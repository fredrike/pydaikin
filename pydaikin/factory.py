"""Factory to init the corresponding Daikin class."""

from .daikin_airbase import DaikinAirBase
from .daikin_brp069 import DaikinBRP069
from .daikin_brp072c import DaikinBRP072C
from .daikin_skyfi import DaikinSkyFi


async def factory(device_id, session=None, **kwargs):
    """Factory to init the corresponding Daikin class."""

    if 'password' in kwargs and kwargs['password'] is not None:
        appl = DaikinSkyFi(device_id, session, password=kwargs['password'])
    elif 'key' in kwargs and kwargs['key'] is not None:
        appl = DaikinBRP072C(
            device_id,
            session,
            key=kwargs['key'],
            uuid=kwargs.get('uuid'),
        )
    else:  # special case for BRP069 and AirBase
        appl = DaikinBRP069(device_id, session)
        await appl.update_status(appl.HTTP_RESOURCES[:1])
        if not appl.values:
            appl = DaikinAirBase(device_id, session)
    await appl.init()
    return appl
