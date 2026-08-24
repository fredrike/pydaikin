"Factory to generate Pydaikin complete objects"

import logging
import re
from typing import Optional, Tuple

import aiohttp
from aiohttp import ClientSession
from aiohttp.web_exceptions import HTTPNotFound

from .daikin_airbase import DaikinAirBase
from .daikin_base import Appliance
from .daikin_brp069 import DaikinBRP069
from .daikin_brp072c import DaikinBRP072C
from .daikin_brp084 import DaikinBRP084
from .daikin_skyfi import DaikinSkyFi
from .discovery import get_device_by_ip, get_name
from .exceptions import DaikinException

_LOGGER = logging.getLogger(__name__)


class DaikinFactory:  # pylint: disable=too-few-public-methods
    "Factory object generating instantiated instances of Appliance"

    _generated_object: Appliance

    async def __new__(cls, *a, **kw):  # pylint: disable=invalid-overridden-method
        "Return not itself, but the Appliance instanced by __init__"
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance._generated_object

    async def __init__(  # pylint: disable=too-many-branches,too-many-statements,broad-exception-caught
        self,
        device_id: str,
        session: Optional[ClientSession] = None,
        password: str = None,
        key: str = None,
        **kwargs,
    ) -> None:
        """Factory to init the corresponding Daikin class."""

        # Check if this is a device with optional port from discovery
        device_ip, device_port = self._extract_ip_port(device_id)
        obj = None
        already_initialized = False

        # Create a single session for all detection trials if the caller did not
        # provide one, so that failed trials do not leak their own sessions.
        if session is None:
            session = ClientSession()
            own_session = True
        else:
            own_session = False

        if password:
            obj = DaikinSkyFi(device_ip, session, password)
        elif key:
            obj = await self._try_brp072c(device_ip, session, key, kwargs)
            if obj is not None:
                already_initialized = True
        # Try BRP084, firmware 2.8.0
        if not obj:
            try:
                _LOGGER.debug("Trying connection to BRP084 firmware 2.8.0")
                obj = DaikinBRP084(device_ip, session)
                await obj.update_status()
                # Initialize mode to "off" if we couldn't read it
                if not obj.values.get("mode", invalidate=False):
                    obj.values["mode"] = "off"
                    obj.values["pow"] = "0"
            except (HTTPNotFound, DaikinException) as err:
                _LOGGER.debug("Not a BRP084 firmware 2.8.0 device: %s", err)
                obj = None
        # Try BRP069
        if not obj:
            try:
                _LOGGER.debug("Trying connection to BRP069")
                obj = DaikinBRP069(device_ip, session)

                # If we have a specific port from discovery, set it in the base_url
                if device_port and device_port != 80:
                    _LOGGER.debug("Using custom port %s for BRP069", device_port)
                    obj.base_url = f"http://{device_ip}:{device_port}"
                await obj.update_status(obj.HTTP_RESOURCES[:1])
                if not obj.values:
                    raise DaikinException("Empty Values.")
            except (HTTPNotFound, DaikinException) as err:
                _LOGGER.debug("Not a BRP069 device: %s", err)
                obj = None
        # Try AirBase
        if not obj:
            _LOGGER.debug("Trying connection to AirBase")
            obj = DaikinAirBase(device_ip, session)

            # If we have a specific port from discovery, set it in the base_url
            if device_port and device_port != 80:
                _LOGGER.debug("Using custom port %s for AirBase", device_port)
                obj.base_url = f"http://{device_ip}:{device_port}"

        if own_session:
            setattr(obj, "_own_session", True)
        try:
            if not already_initialized:
                try:
                    await obj.init()
                except DaikinException as err:
                    # The last-resort driver could not read any values at all.
                    # If discovery identifies a known unsupported fingerprint,
                    # report it instead of the bare exception.
                    if not isinstance(obj, DaikinAirBase):
                        raise
                    discovery_info = self._get_discovery_info(device_ip)
                    if discovery_info is None:
                        raise
                    raise DaikinException(
                        self._unsupported_device_message(obj, device_id, discovery_info)
                    ) from err
            if not obj.values.get("mode"):
                raise DaikinException(
                    self._unsupported_device_message(
                        obj, device_id, self._get_discovery_info(device_ip)
                    )
                )
        except Exception:
            if own_session:
                await obj.aclose()
            raise
        _LOGGER.debug("Daikin generated object: %s", type(obj))
        self._generated_object = obj

    @staticmethod
    async def _try_brp072c(
        device_ip: str,
        session: Optional[ClientSession],
        key: str,
        kwargs: dict,
    ) -> Optional[DaikinBRP072C]:
        """Try to connect as BRP072C; return None if it fails."""
        obj = DaikinBRP072C(
            device_ip,
            session,
            key=key,
            uuid=kwargs.get("uuid"),
            ssl_context=kwargs.get("ssl_context"),
        )
        try:
            # Some BRP069 units also use keys to auth.
            # If treated as a BRP072 we won't be able to connect,
            # since this will force https on a unit that expects
            # connection to port 80. We do a preliminary attempt at
            # initialization to catch connection errors and then
            # fallback to the following cases.
            await obj.init()
            return obj
        except (DaikinException, aiohttp.ClientError, TimeoutError, OSError) as err:
            _LOGGER.debug(err)
            return None

    @staticmethod
    def _unsupported_device_message(
        obj: Appliance,
        device_id: str,
        discovery_info: Optional[dict] = None,
    ) -> str:
        """Build a clear error message for a detected but unsupported device.

        Some adapters answer /common/basic_info (so type, subtype and firmware
        are known) but expose no control API. A known example is the BRP069C8x
        running firmware 2.3.x, which returns 404 for every /aircon endpoint.
        Other adapters answer UDP discovery only, with every HTTP endpoint
        returning 404 - for those ``discovery_info`` carries the fingerprint.
        """
        values = obj.values
        device_type = values.get("type", invalidate=False)
        subtype = values.get("subtype", invalidate=False)
        firmware = values.get("ver", invalidate=False)

        if (
            device_type == "aircon"
            and subtype == "qa"
            and firmware
            and firmware.startswith("2_3_")
        ):
            return (
                f"Error creating device, {device_id} is not supported: "
                f"BRP069C8x with firmware {firmware.replace('_', '.')} is not "
                "supported by pydaikin."
            )

        # Adapters speaking the DGC protocol (Onecta generation) with firmware
        # before 2.8.0 respond to UDP discovery but expose no local control
        # API at all - every HTTP endpoint returns 404. Known examples are the
        # built-in WiFi adapters of newer Stylish units (issue #153) and
        # BRP069C4x/C8x gateways (issues #83, #116).
        if discovery_info:
            protocol = discovery_info.get("protocol")
            disc_firmware = discovery_info.get("ver")
            if protocol == "DGC" and DaikinFactory._is_pre_multireq_firmware(
                disc_firmware
            ):
                disc_type = discovery_info.get("type", "unknown")
                return (
                    f"Error creating device, {device_id} is not supported: "
                    f"detected {disc_type}/{protocol} adapter with firmware "
                    f"{disc_firmware.replace('_', '.')}, but its local "
                    "control API requires adapter firmware 2.8.0 or later. "
                    "Update the adapter via the Onecta app, or control the "
                    "device through the Daikin cloud."
                )

        details = []
        if device_type:
            details.append(f"type={device_type}")
        if subtype:
            details.append(f"subtype={subtype}")
        if firmware:
            details.append(f"firmware {firmware.replace('_', '.')}")
        if adp_kind := values.get("adp_kind", invalidate=False):
            details.append(f"adp_kind={adp_kind}")

        if details:
            return (
                f"Error creating device, {device_id} is not supported: "
                f"detected {', '.join(details)}, but its control API is not "
                "available. This device/firmware combination is not supported "
                "by pydaikin."
            )
        return f"Error creating device, {device_id} is not supported."

    @staticmethod
    def _is_pre_multireq_firmware(ver: Optional[str]) -> bool:
        """Return True for DGC adapter firmware lacking /dsiot/multireq.

        Adapter firmware 2.8.0 introduced the local JSON API; earlier 2.x
        releases (e.g. 2_6_1) provide no local control endpoints at all.
        Malformed versions are treated as not matching this fingerprint.
        """
        try:
            major, minor = (int(part) for part in ver.split("_")[:2])
        except (AttributeError, ValueError):
            return False
        return (major, minor) < (2, 8)

    @staticmethod
    def _get_discovery_info(device_ip: str) -> Optional[dict]:
        """Best-effort lookup of UDP discovery attributes for the device IP."""
        try:
            return get_device_by_ip(device_ip)
        except Exception as err:  # pylint: disable=broad-exception-caught
            _LOGGER.debug("Error looking up device via discovery: %s", err)
            return None

    @staticmethod
    def _extract_ip_port(device_id: str) -> Tuple[str, Optional[int]]:
        """Extract IP and optional port from device_id string or lookup via discovery."""
        # Check if there's a port specified in the device_id
        port_match = re.match(r'^(.+):(\d+)$', device_id)
        if port_match:
            return port_match.group(1), int(port_match.group(2))

        # Try to look up device in discovery
        try:
            device_name = get_name(device_id)
            if device_name and 'port' in device_name:
                return device_name['ip'], int(device_name['port'])
        except (KeyError, ValueError, TypeError) as e:
            _LOGGER.debug("Error looking up device in discovery: %s", e)

        # Default: just return the IP with no port
        return device_id, None
