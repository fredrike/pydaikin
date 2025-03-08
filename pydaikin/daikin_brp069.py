"""Pydaikin appliance, represent a Daikin BRP069 device."""

from datetime import datetime, timezone
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
        'filter_sign_info': 'filter dirty',
    }

    MAX_CONCURRENT_REQUESTS = 1

    @staticmethod
    def parse_response(response_body):
        """Parse response from Daikin

        Translate swing mode from 2 parameters to 1 (Special case for certain models e.g Alira X)
        """
        _LOGGER.debug("Parsing %s", response_body)
        response = super(DaikinBRP069, DaikinBRP069).parse_response(response_body)

        if response.get("f_dir_ud") == "0" and response.get("f_dir_lr") == "0":
            response["f_dir"] = '0'
        elif response.get("f_dir_ud") == "S" and response.get("f_dir_lr") == "0":
            response["f_dir"] = '1'
        elif response.get("f_dir_ud") == "0" and response.get("f_dir_lr") == "S":
            response["f_dir"] = '2'
        elif response.get("f_dir_ud") == "S" and response.get("f_dir_lr") == "S":
            response["f_dir"] = '3'

        return response

    async def init(self):
        """Init status."""
        await self.auto_set_clock()
        if self.values:
            await self.update_status(self.HTTP_RESOURCES[1:])
        else:
            await self.update_status(self.HTTP_RESOURCES)

    def get_info_resources(self):
        """Returns info_resources"""
        if self.support_energy_consumption:
            return self.INFO_RESOURCES + [
                'aircon/get_day_power_ex',
                'aircon/get_week_power',
            ]

        return self.INFO_RESOURCES

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
            if 'f_dir_lr' in self.values and 'f_dir_ud' in self.values:
                # Australian Alira X uses 2 separate parameters instead of the combined f_dir
                f_dir_ud = 'S' if self.values['f_dir'] in ('1', '3') else '0'
                f_dir_lr = 'S' if self.values['f_dir'] in ('2', '3') else '0'
                params.update({"f_dir_ud": f_dir_ud, "f_dir_lr": f_dir_lr})
            else:
                params.update({"f_dir": self.values['f_dir']})

        _LOGGER.debug("Sending request to %s with params: %s", path, params)
        await self._get_resource(path, params)

    async def set_holiday(self, mode):
        """Set holiday mode."""
        value = self.human_to_daikin('en_hol', mode)
        if value in ('0', '1'):
            self.values["en_hol"] = value

            path = 'common/set_holiday'
            params = {"en_hol": value}

            _LOGGER.debug("Sending request to %s with params: %s", path, params)
            await self._get_resource(path, params)

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
                "en_streamer": value,
            }

            _LOGGER.debug("Sending request to %s with params: %s", path, params)
            # Update the adv value from the response
            self.values.update(await self._get_resource(path, params))

    async def set_zone(self, zone_id, key, value):
        """Set zone status."""

    async def set_clock(self):
        """Sets the clock on the AC to the current time"""
        now = datetime.now(timezone.utc)
        try:
            await self._get_resource(
                'common/notify_date_time',
                {
                    "date=": now.strftime('%Y/%m/%d'),
                    "zone": "GMT",
                    "time": now.strftime('%H:%M:%S'),
                },
            )
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Raised "%s" while setting internal clock', exc)

    async def auto_set_clock(self):
        """Tells the AC to auto-set its internal clock."""
        try:
            await self._get_resource('common/get_datetime', {"cur": ""})
        except Exception as exc:  # pylint: disable=broad-except
            _LOGGER.error('Raised "%s" while trying to auto-set internal clock', exc)

    @property
    def support_humidity(self):
        """Return True if the device has humidity sensor."""
        return self.humidity is not None
