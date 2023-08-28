"Factory to generate Pydaikin complete objects"

from typing import Optional

from aiohttp import ClientSession

from .daikin_airbase import DaikinAirBase
from .daikin_base import Appliance
from .daikin_brp069 import DaikinBRP069
from .daikin_brp072c import DaikinBRP072C
from .daikin_skyfi import DaikinSkyFi
from .exceptions import DaikinException


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
            self._generated_object = DaikinSkyFi(device_id, session, password=password)
        elif key is not None:
            self._generated_object = DaikinBRP072C(
                device_id,
                session,
                key=key,
                uuid=kwargs.get('uuid'),
            )
        else:  # special case for BRP069 and AirBase
            self._generated_object = DaikinBRP069(device_id, session)
            await self._generated_object.update_status(
                self._generated_object.HTTP_RESOURCES[:1]
            )
            if not self._generated_object.values:
                self._generated_object = DaikinAirBase(device_id, session)

        await self._generated_object.init()

        if not self._generated_object.values.get("mode"):
            raise DaikinException(
                f"Error creating device, {device_id} is not supported."
            )
