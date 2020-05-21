"""Pydaikin appliance, represent a Daikin AirBase device."""

import logging
from urllib.parse import quote, unquote

from .daikin_brp069 import DaikinBRP069

_LOGGER = logging.getLogger(__name__)


class DaikinAirBase(DaikinBRP069):
    """Daikin class for AirBase (BRP15B61) units."""

    TRANSLATIONS = dict(
        DaikinBRP069.TRANSLATIONS,
        **{
            'mode': {'0': 'fan', '1': 'hot', '2': 'cool', '3': 'auto', '7': 'dry',},
            'f_rate': {'1': 'low', '3': 'mid', '5': 'high',},
        },
    )

    HTTP_RESOURCES = [
        'common/basic_info',
        'aircon/get_control_info',
        'aircon/get_model_info',
        'aircon/get_zone_setting',
    ]

    INFO_RESOURCES = DaikinBRP069.INFO_RESOURCES + ['aircon/get_zone_setting']

    def __init__(self, device_id, session=None):
        """Init the pydaikin appliance, representing one Daikin AirBase (BRP15B61) device."""
        super().__init__(device_id, session)
        self.values.update({'htemp': '-', 'otemp': '-', 'shum': '--'})

    async def init(self):
        """Init status and set defaults."""
        await super().init()
        if not self.values:
            raise Exception("Empty values.")
        if self.values['frate_steps'] == '2':
            self.TRANSLATIONS['f_rate'] = {'1': 'low', '5': 'high'}

    async def _run_get_resource(self, resource):
        """Make the http request."""
        resource = 'skyfi/%s' % resource
        return await super()._run_get_resource(resource)

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return False

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return False

    @property
    def support_outside_temperature(self):
        """Return True if the device is not an AirBase unit."""
        return False

    async def set(self, settings):
        """Set settings on Daikin device."""
        await self._update_settings(settings)

        query_c = 'aircon/set_control_info?pow={pow}&mode={mode}&stemp={stemp}&shum={shum}'.format(
            **self.values
        )
        query_c += '&lpw=&f_airside=0'

        # Apparently some remote controllers doesn't support f_rate and f_dir
        if self.support_fan_rate:
            query_c += f'&f_rate={self.values["f_rate"]}'
        query_c += f'&f_dir={self.values["f_dir"]}'

        _LOGGER.debug("Sending query_c: %s", query_c)
        await self._get_resource(query_c)

    def represent(self, key):
        """Return translated value from key."""
        k, val = super().represent(key)

        if key in ['zone_name', 'zone_onoff']:
            val = unquote(self.values[key]).split(';')

        return (k, val)

    @property
    def zones(self):
        """Return list of zones."""
        if not self.values.get('zone_name'):
            return None
        zone_onoff = self.represent('zone_onoff')[1]
        return [
            (name.strip(' +,'), zone_onoff[i])
            for i, name in enumerate(self.represent('zone_name')[1])
        ]

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        current_state = await self._get_resource('aircon/get_zone_setting')
        self.values.update(current_state)
        zone_onoff = self.represent('zone_onoff')[1]
        zone_onoff[zone_id] = status
        self.values['zone_onoff'] = quote(';'.join(zone_onoff)).lower()

        query = 'aircon/set_zone_setting?zone_name={}&zone_onoff={}'.format(
            current_state['zone_name'], self.values['zone_onoff'],
        )

        _LOGGER.debug("Set zone:: %s", query)
        await self._get_resource(query)
