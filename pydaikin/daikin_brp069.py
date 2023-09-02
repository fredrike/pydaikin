"""Pydaikin appliance, represent a Daikin BRP069 device."""

import logging
from typing import Literal

from aiohttp import ClientSession

from .daikin_base import Appliance
from .models import base, brp069

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

    async def __init__(self, device_id, session: ClientSession | None = None):
        await super().__init__(device_id, session)

        self.http_resources.update({
            'common/basic_info': base.CommonBasicInfo,
            'common/get_remote_method': brp069.CommonGetRemoteMethod,
            'aircon/get_sensor_info': brp069.AirconGetSensorInfo,
            'aircon/get_model_info': brp069.AirconGetModelInfo,
            'aircon/get_control_info': brp069.AirconGetControlInfo,
            'aircon/get_target': brp069.AirconGetTarget,
            'aircon/get_price': brp069.AirconGetPrice,
            'common/get_holiday': brp069.CommonGetHoliday,
            'common/get_notify': brp069.CommonGetNotify,
            'aircon/get_day_power_ex': brp069.AirconGetDayPowerEx,
            'aircon/get_week_power': brp069.AirconGetWeekPower,
            'aircon/get_year_power': brp069.AirconGetYearPower,
            'common/get_datetime': brp069.CommonGetdatetime,
        })

    async def refresh_data(self):
        """Init status."""
        await super().refresh_data()
        await self.auto_set_clock()

    async def _update_settings(self, settings):
        """Update settings to set on Daikin device."""
        # start with current values
        resource = 'aircon/get_control_info'
        current_val = await self._get_resource(resource)

        # Merge current_val with mapped settings
        self.values.update_by_resource(resource, current_val)
        self.values.update_by_resource(
            resource, {k: self.human_to_daikin(k, v) for k, v in settings.items()}
        )

        # we are using an extra mode "off" to power off the unit
        if settings.get('mode', '') == 'off':
            self.values['pow'] = '0'
            # some units are picky with the off mode
            self.values['mode'] = current_val['mode']

        # if changing the mode to something other than off assume the unit should be
        # powered on OR if the request is empty power on
        elif 'mode' in settings or not settings:
            self.values['pow'] = '1'

        # Use settings for respecitve mode (dh and dt)
        for k, val in {'stemp': 'dt', 'shum': 'dh', 'f_rate': 'dfr'}.items():
            if k not in settings:
                key = val + self.values['mode']
                if key in current_val:
                    self.values[k] = current_val[key]

        return current_val

    async def set(self, settings):
        """Set settings on Daikin device."""
        await self._update_settings(settings)

        path = 'aircon/set_control_info'
        params = {
            "mode": self.values["mode"],
            "pow": self.values["pow"],
            "shum": self.values["shum"],
            "stemp": self.values["stemp"],
        }

        # Apparently some remote controllers doesn't support f_rate and f_dir
        if self.support_fan_rate:
            params.update({"f_rate": self.values['f_rate']})
        if self.support_swing_mode:
            params.update({"f_dir": self.values['f_dir']})

        _LOGGER.debug("Sending request to %s with params: %s", path, params)
        await self._get_resource(path, params)

    async def set_holiday(self, mode: Literal["on", "off"]):
        """Set holiday mode."""

        mapping = {
            "on": "1",
            "off": "0"
        }

        try:
            daikinparam = mapping[mode]
        except KeyError as exc:
            raise ValueError('mode must be "on" or "off"') from exc

        path = 'common/set_holiday'
        params = {"en_hol": daikinparam}

        _LOGGER.debug("Sending request to %s with params: %s", path, params)
        await self.get(path, params)

    async def set_advanced_mode(self, mode, value):
        """Enable or disable advanced modes."""
        mode = self.human_to_daikin('spmode_kind', mode)
        value = self.human_to_daikin('spmode', value)
        if value in ('0', '1'):
            path = 'aircon/set_special_mode'
            params = {
                "spmode_kind": mode,
                "set_spmode": value,
            }

            _LOGGER.debug("Sending request to %s with params: %s", path, params)
            # Update the adv value from the response
            self.values.update(await self._get_resource(path, params))

    async def set_streamer(self, mode):
        """Enable or disable the streamer."""
        value = self.human_to_daikin('en_streamer', mode)
        if value in ('0', '1'):
            path = 'aircon/set_special_mode'
            params = {
                "streamer": mode,
                "set_spmode": value,
            }

            _LOGGER.debug("Sending request to %s with params: %s", path, params)
            # Update the adv value from the response
            self.values.update(await self._get_resource(path, params))

    async def set_zone(self, zone_id, key, value):
        """Set zone status."""

    async def auto_set_clock(self):
        """Tells the AC to auto-set its internal clock."""
        try:
            await self.get('common/get_datetime', {"cur": ""})
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Raised "%s" while trying to auto-set internal clock', exc)

    @property
    def support_humidity(self):
        """Return True if the device has humidity sensor."""
        return self.humidity is not None
