"""Pydaikin appliance, represent a Daikin device."""

import logging
from urllib.parse import unquote

from .appliance import Appliance

_LOGGER = logging.getLogger(__name__)


class DaikinSkyFi(Appliance):
    """Daikin class for SkyFi units."""

    HTTP_RESOURCES = ['ac.cgi?', 'zones.cgi?']

    INFO_RESOURCES = HTTP_RESOURCES

    SKYFI_TO_DAIKIN = {
        'outsidetemp': 'otemp',
        'roomtemp': 'htemp',
        'settemp': 'stemp',
        'opmode': 'pow',
        'fanspeed': 'f_rate',
        'fanflags': 'f_dir',
        'acmode': 'mode',
    }

    TRANSLATIONS = {
        'mode': {
            '0': 'Off',
            '1': 'auto',
            '2': 'hot',
            '3': 'auto-3',
            '4': 'dry',
            '8': 'cool',
            '9': 'auto-9',
            '16': 'dry',
        },
        'f_rate': {'1': 'low', '2': 'mid', '3': 'high'},
        'f_mode': {'1': 'manual', '3': 'auto'},
    }

    @classmethod
    def daikin_to_skyfi(cls, dimension):
        """Return converted values from Daikin to SkyFi."""
        return {val: key for key, val in cls.SKYFI_TO_DAIKIN.items()}.get(
            dimension, dimension
        )

    def __init__(self, device_id, session=None, password=None):
        """Init the pydaikin appliance, representing one Daikin SkyFi device."""
        super().__init__(device_id, session)
        self._device_ip = f'{self._device_ip}:2000'
        self._password = password

    def __getitem__(self, name):
        """Return named value."""
        name = self.SKYFI_TO_DAIKIN.get(name, name)
        return super().__getitem__(name)

    async def init(self):
        """Init status."""
        await self.update_status(self.HTTP_RESOURCES)

    def set_holiday(self, mode):
        """Set holiday mode."""

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return False

    @property
    def support_fan_rate(self):
        """Return True if the device support setting fan_rate."""
        return True

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return False

    @property
    def mac(self):
        """Return ip as mac not is available on SkyFi units."""
        return self._device_ip

    @staticmethod
    def parse_response(response_body):
        """Parse response from Daikin and map it to general Daikin format."""
        response = dict([e.split('=') for e in response_body.split(',')])
        return response

    async def _run_get_resource(self, resource):
        """Make the http request."""
        resource = "{}pass={}".format(resource, self._password)
        return await super()._run_get_resource(resource)

    def _represent(self, key):
        """Return translated value from key."""
        k, val = super()._represent(key)
        if key in [f'zone{i}' for i in range(1, 9)]:
            val = unquote(self[key])
        if key == 'zone':
            # zone is a binary representation of zone status
            val = list(str(bin(int(self[key])) + 256))[3:]
        return (k, val)

    async def set(self, settings):
        """Set settings on Daikin device."""
        # start with current values
        current_val = await self._get_resource('ac.cgi?')

        # Merge current_val with mapped settings
        self.values.update(current_val)
        self.values.update(
            {
                self.daikin_to_skyfi(k): self.human_to_daikin(k, v)
                for k, v in settings.items()
            }
        )

        # we are using an extra mode "off" to power off the unit
        if settings.get('mode', '') == 'off':
            self.values['pow'] = '0'
        else:
            self.values['pow'] = '1'

        query_c = 'set.cgi?p={pow}&t={stemp}&f={f_rate}&m={mode}&'.format(**self.values)

        _LOGGER.debug("Sending query_c: %s", query_c)
        await self._get_resource(query_c)

    @property
    def zones(self):
        """Return list of zones."""
        if 'nz' not in self.values:
            return False
        zone_onoff = self._represent('zone')
        return [
            (name.strip(' +,'), zone_onoff)
            for i, name in enumerate(
                [self._represent(f'zone{i}') for i in range(1, int(self['nz']) + 1)]
            )
        ]

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        query = '/setzone.cgi?z={zone_id}&s={status}&'
        _LOGGER.debug("Set zone: %s", query)
        current_state = await self._get_resource(query)
        self.values.update(current_state)
