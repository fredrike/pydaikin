"Factory to generate Pydaikin complete objects"

import logging
import re
from typing import Optional, Tuple

from aiohttp import ClientSession
from aiohttp.web_exceptions import HTTPNotFound

from .daikin_airbase import DaikinAirBase
from .daikin_base import Appliance
from .daikin_brp069 import DaikinBRP069
from .daikin_brp072c import DaikinBRP072C
from .daikin_brp084 import DaikinBRP084
from .daikin_skyfi import DaikinSkyFi
from .discovery import get_name
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

    async def __init__(
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

        if password:
            obj = DaikinSkyFi(device_ip, session, password)
        elif key:
            obj = DaikinBRP072C(
                device_ip,
                session,
                key=key,
                uuid=kwargs.get('uuid'),
                ssl_context=kwargs.get('ssl_context'),
            )
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

        await obj.init()
        if not obj.values.get("mode"):
            raise DaikinException(
                f"Error creating device, {device_id} is not supported."
            )
        _LOGGER.debug("Daikin generated object: %s", type(obj))
        self._generated_object = obj

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
