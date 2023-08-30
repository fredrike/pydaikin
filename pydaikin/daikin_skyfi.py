"""Pydaikin appliance, represent a Daikin device."""

import logging
from urllib.parse import unquote

from .daikin_base import Appliance

_LOGGER = logging.getLogger(__name__)


class DaikinSkyFi(Appliance):
    """Daikin class for SkyFi units."""

    HTTP_RESOURCES = ['ac.cgi?pass={}', 'zones.cgi?pass={}']

    INFO_RESOURCES = HTTP_RESOURCES

    SKYFI_TO_DAIKIN = {
        'outsidetemp': 'otemp',
        'roomtemp': 'htemp',
        'settemp': 'stemp',
        'opmode': 'pow',
        'fanspeed': 'f_rate',
        'acmode': 'mode',
    }

    DAIKIN_TO_SKYFI = {val: k for k, val in SKYFI_TO_DAIKIN.items()}

    TRANSLATIONS = {
        'mode': {
            '0': 'off',
            '1': 'auto',
            '2': 'hot',
            '3': 'auto-3',
            '4': 'dry',
            '8': 'cool',
            '9': 'auto-9',
            '16': 'fan',
        },
        'f_rate': {
            '1': 'low',
            '2': 'medium',
            '3': 'high',
            '5': 'low/auto',
            '6': 'medium/auto',
            '7': 'high/auto',
        },
    }

    def __init__(self, device_id, session=None, password=None):
        """Init the pydaikin appliance, representing one Daikin SkyFi device."""
        super().__init__(device_id, session)
        self.device_ip = f'{self.device_ip}:2000'
        self.base_url = f"http://{self.device_ip}"
        self._password = password

    def __getitem__(self, name):
        """Return named value."""
        name = self.SKYFI_TO_DAIKIN.get(name, name)
        return super().__getitem__(name)

    async def refresh_data(self):
        """Init status."""
        await self.refresh_data(self.HTTP_RESOURCES)

    async def set_holiday(self, mode):
        """Set holiday mode."""

    async def set_advanced_mode(self, mode, value):
        """Set advanced mode."""

    async def set_streamer(self, mode):
        """Set streamer mode."""

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

    @staticmethod
    def parse_response(response_body):
        """Parse response from Daikin and map it to general Daikin format."""
        _LOGGER.debug("Parsing %s", response_body)
        response = dict([e.split('=') for e in response_body.split('&')])
        if response.get('fanflags') == '3':
            response['fanspeed'] = str(int(response['fanspeed']) + 4)
        response.update(
            {
                DaikinSkyFi.SKYFI_TO_DAIKIN.get(key, key): val
                for key, val in response.items()
            }
        )
        return response

    def represent(self, key):
        """Return translated value from key."""
        k, val = super().represent(self.SKYFI_TO_DAIKIN.get(key, key))
        if key in [f'zone{i}' for i in range(1, 9)]:
            val = unquote(self[key])
        if key == 'zone':
            # zone is a binary representation of zone status
            val = str(bin(int(self[key]) + 256))[3 : int(self['nz']) + 3]
        return (k, val)

    async def set(self, settings):
        """Set settings on Daikin device."""
        _LOGGER.debug("Updating settings: %s", settings)
        await self.refresh_data(['ac.cgi?pass={}'])

        # Merge current_val with mapped settings
        self.values.update(
            {
                self.DAIKIN_TO_SKYFI[k]: self.human_to_daikin(k, v)
                for k, v in settings.items()
            }
        )
        _LOGGER.debug("Updated values: %s", self.values)

        # we are using an extra mode "off" to power off the unit
        path = "set.cgi"
        params = {
            'pass': self._password,
            "opmode": self.values['opmode'],
            "settemp": self.values['settemp'],
            "fanspeed": self.values['fanspeed'],
            "acmode": self.values['acmode'],
        }

        if settings.get('mode', '') == 'off':
            params['opmode'] = '0'
        else:
            if 'mode' in settings:
                params['opmode'] = '1'

        current_state = await self._get_resource(path, params)
        self.values.update(current_state)

    @property
    def zones(self):
        """Return list of zones."""
        if 'nz' not in self.values:
            return False
        return [
            v
            for i, v in enumerate(
                [
                    (self.represent(f'zone{i+1}')[1].strip(' +,'), onoff)
                    for i, onoff in enumerate(self.represent('zone')[1])
                ]
            )
            if v != f'Zone {i+1}'
        ]

    async def set_zone(self, zone_id, key, value):
        """Set zone status."""
        if key != 'zone_onoff':
            return
        zone_id += 1

        path = "setzone.cgi"
        params = {"pass": "HIDDEN", "z": zone_id, "s": value}
        _LOGGER.debug("Sending request to %s with params: %s", path, params)

        params["pass"] = self._password

        current_state = await self._get_resource(path, params)
        self.values.update(current_state)
