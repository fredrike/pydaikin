"Factory to generate Pydaikin complete objects"

import logging
import re
from typing import Optional

from aiohttp import ClientSession
from aiohttp.web_exceptions import HTTPNotFound

from .daikin_airbase import DaikinAirBase
from .daikin_base import Appliance
from .daikin_brp069 import DaikinBRP069
from .daikin_brp072c import DaikinBRP072C
from .daikin_brp_280 import DaikinBRP280
from .daikin_skyfi import DaikinSkyFi
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

        if password is not None:
            self._generated_object = DaikinSkyFi(device_id, session, password)
        elif key is not None:
            self._generated_object = DaikinBRP072C(
                device_id,
                session,
                key=key,
                uuid=kwargs.get('uuid'),
                ssl_context=kwargs.get('ssl_context'),
            )
        else:  # special case for BRP069, AirBase, and BRP firmware 2.8.0
            # First try to check if it's firmware 2.8.0
            try:
                _LOGGER.debug("Trying connection to firmware 2.8.0")
                self._generated_object = DaikinBRP280(device_id, session)
                try:
                    await self._generated_object.update_status()
                    # If we get here, it's likely a 2.8.0 device
                    _LOGGER.info("Successfully connected to firmware 2.8.0 device")
                    # Initialize mode to "off" if we couldn't read it
                    if not self._generated_object.values.get("mode", invalidate=False):
                        self._generated_object.values["mode"] = "off"
                        self._generated_object.values["pow"] = "0"
                    return
                except Exception as e:
                    _LOGGER.debug("Failed to communicate with firmware 2.8.0 endpoint: %s", e)
                    raise DaikinException(f"Not a firmware 2.8.0 device: {e}")
            except (HTTPNotFound, DaikinException) as err:
                _LOGGER.debug("Not a firmware 2.8.0 device: %s", err)
                
            # Try BRP069
            try:
                _LOGGER.debug("Trying connection to BRP069")
                self._generated_object = DaikinBRP069(device_id, session)
                await self._generated_object.update_status(
                    self._generated_object.HTTP_RESOURCES[:1]
                )
                if not self._generated_object.values:
                    raise DaikinException("Empty Values.")
            except (HTTPNotFound, DaikinException) as err:
                _LOGGER.debug("Falling back to AirBase: %s", err)
                self._generated_object = DaikinAirBase(device_id, session)

        await self._generated_object.init()

        if not self._generated_object.values.get("mode"):
            raise DaikinException(
                f"Error creating device, {device_id} is not supported."
            )

        _LOGGER.debug("Daikin generated object: %s", self._generated_object)