"""Pydaikin appliance, represent a Daikin BRP069 device."""

import logging

from .daikin_base import Appliance

_LOGGER = logging.getLogger(__name__)


class DaikinBRP069(Appliance):
    """Daikin class for BRP069[A-B]xx units."""

    TRANSLATIONS = {
        'mode': {
            '2': 'dry',
            '3': 'cool',
            '4': 'hot',
            '6': 'fan',
            '0': 'auto',
            '1': 'auto-1',
            '7': 'auto-7',
            '10': 'off',
        },
        'f_rate': {
            'A': 'auto',
            'B': 'silence',
            '3': '1',
            '4': '2',
            '5': '3',
            '6': '4',
            '7': '5',
        },
        'f_dir': {
            '0': 'off',
            '1': 'vertical',
            '2': 'horizontal',
            '3': '3d',
        },
        'en_hol': {
            '0': 'off',
            '1': 'on',
        },
        'en_streamer': {
            '0': 'off',
            '1': 'on',
        },
        'adv': {
            '': 'off',
            '2': 'powerful',
            '2/13': 'powerful streamer',
            '12': 'econo',
            '12/13': 'econo streamer',
            '13': 'streamer',
        },
        'spmode_kind': {
            '0': 'streamer',
            '1': 'powerful',
            '2': 'econo',
        },
        'spmode': {
            '0': 'off',
            '1': 'on',
        },
    }

    HTTP_RESOURCES = [
        'common/basic_info',
        'common/get_remote_method',
        'aircon/get_sensor_info',
        'aircon/get_model_info',
        'aircon/get_control_info',
        'aircon/get_target',
        'aircon/get_price',
        'common/get_holiday',
        'common/get_notify',
        'aircon/get_day_power_ex',
        'aircon/get_week_power',
        'aircon/get_year_power',
        'common/get_datetime',
    ]

    INFO_RESOURCES = [
        'aircon/get_sensor_info',
        'aircon/get_control_info',
    ]

    VALUES_SUMMARY = [
        'name',
        'ip',
        'mac',
        'mode',
        'f_rate',
        'f_dir',
        'htemp',
        'otemp',
        'stemp',
        'cmpfreq',
        'en_hol',
        'err',
        'cur',
        'adv',
    ]

    VALUES_TRANSLATION = {
        'otemp': 'outside temp',
        'htemp': 'inside temp',
        'stemp': 'target temp',
        'ver': 'firmware adapter',
        'pow': 'power',
        'cmpfreq': 'compressor frequency',
        'f_rate': 'fan rate',
        'f_dir': 'fan direction',
        'err': 'error code',
        'en_hol': 'away_mode',
        'cur': 'internal clock',
        'adv': 'advanced mode',
    }

    async def init(self):
        """Init status."""
        await self.auto_set_clock()
        if self.values:
            await self.update_status(self.HTTP_RESOURCES[1:])
        else:
            await self.update_status(self.HTTP_RESOURCES)

        if self.support_energy_consumption:
            self.INFO_RESOURCES += [  # pylint: disable=invalid-name
                'aircon/get_day_power_ex',
                'aircon/get_week_power',
            ]

    async def _update_settings(self, settings):
        """Update settings to set on Daikin device."""
        # start with current values
        current_val = await self._get_resource('aircon/get_control_info')

        # Merge current_val with mapped settings
        self.values.update(current_val)
        self.values.update({k: self.human_to_daikin(k, v) for k, v in settings.items()})

        # we are using an extra mode "off" to power off the unit
        if settings.get('mode', '') == 'off':
            self.values['pow'] = '0'
            # some units are picky with the off mode
            self.values['mode'] = current_val['mode']
        else:
            self.values['pow'] = '1'

        # Use settings for respecitve mode (dh and dt)
        for k, val in {'stemp': 'dt', 'shum': 'dh', 'f_rate': 'dfr'}.items():
            if k not in settings:
                key = val + self.values['mode']
                if key in current_val:
                    self.values[k] = current_val[key]

    async def set(self, settings):
        """Set settings on Daikin device."""
        await self._update_settings(settings)

        query_c = 'aircon/set_control_info?pow=%s&mode=%s&stemp=%s&shum=%s' % (
            self.values['pow'],
            self.values['mode'],
            self.values['stemp'],
            self.values['shum'],
        )

        # Apparently some remote controllers doesn't support f_rate and f_dir
        if self.support_fan_rate:
            query_c += '&f_rate=%s' % self.values['f_rate']
        if self.support_swing_mode:
            query_c += '&f_dir=%s' % self.values['f_dir']

        _LOGGER.debug("Sending query_c: %s", query_c)
        await self._get_resource(query_c)

    async def set_holiday(self, mode):
        """Set holiday mode."""
        value = self.human_to_daikin('en_hol', mode)
        if value in ('0', '1'):
            query_h = 'common/set_holiday?en_hol=%s' % value
            self.values['en_hol'] = value
            _LOGGER.debug("Sending query: %s", query_h)
            await self._get_resource(query_h)

    async def set_advanced_mode(self, mode, value):
        """Enable or disable advanced modes."""
        mode = self.human_to_daikin('spmode_kind', mode)
        value = self.human_to_daikin('spmode', value)
        if value in ('0', '1'):
            query_h = 'aircon/set_special_mode?spmode_kind=%s&set_spmode=%s' % (
                mode,
                value,
            )
            _LOGGER.debug("Sending query: %s", query_h)
            # Update the adv value from the response
            self.values.update(await self._get_resource(query_h))

    async def set_streamer(self, mode):
        """Enable or disable the streamer."""
        value = self.human_to_daikin('en_streamer', mode)
        if value in ('0', '1'):
            query_h = 'aircon/set_special_mode?en_streamer=%s' % value
            _LOGGER.debug("Sending query: %s", query_h)
            # Update the adv value from the response
            self.values.update(await self._get_resource(query_h))

    async def set_zone(self, zone_id, status):
        """Set zone status."""

    async def auto_set_clock(self):
        """Tells the AC to auto-set its internal clock."""
        try:
            await self._get_resource('common/get_datetime?cur=')
        except Exception as exc:
            _LOGGER.error('Raised "%s" while trying to auto-set internal clock', exc)

    @property
    def support_humidity(self):
        """Return True if the device has humidity sensor."""
        return self.humidity is not None
