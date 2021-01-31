"""Pydaikin base appliance, represent a Daikin device."""

from collections import defaultdict
from datetime import datetime, timedelta
import logging
import socket
from urllib.parse import unquote

from aiohttp import ClientSession, ServerDisconnectedError
from aiohttp.web_exceptions import HTTPForbidden

import pydaikin.discovery as discovery
from pydaikin.power import (
    ATTR_COOL,
    ATTR_HEAT,
    ATTR_TOTAL,
    TIME_TODAY,
    DaikinPowerMixin,
)

_LOGGER = logging.getLogger(__name__)


class Appliance(DaikinPowerMixin):  # pylint: disable=too-many-public-methods
    """Daikin main appliance class."""

    TRANSLATIONS = {}

    VALUES_TRANSLATION = {}

    VALUES_SUMMARY = []

    INFO_RESOURCES = []

    @classmethod
    def daikin_to_human(cls, dimension, value):
        """Return converted values from Daikin to Human."""
        return cls.TRANSLATIONS.get(dimension, {}).get(value, str(value))

    @classmethod
    def human_to_daikin(cls, dimension, value):
        """Return converted values from Human to Daikin."""
        translations_rev = {
            dim: {v: k for k, v in item.items()}
            for dim, item in cls.TRANSLATIONS.items()
        }
        return translations_rev.get(dimension, {}).get(value, value)

    @classmethod
    def daikin_values(cls, dimension):
        """Return sorted list of translated values."""
        return sorted(list(cls.TRANSLATIONS.get(dimension, {}).values()))

    @staticmethod
    async def factory(device_id, session=None, **kwargs):
        """Factory to init the corresponding Daikin class."""
        from .daikin_airbase import (  # pylint: disable=import-outside-toplevel
            DaikinAirBase,
        )
        from .daikin_brp069 import (  # pylint: disable=import-outside-toplevel
            DaikinBRP069,
        )
        from .daikin_brp072c import (  # pylint: disable=import-outside-toplevel
            DaikinBRP072C,
        )
        from .daikin_skyfi import DaikinSkyFi  # pylint: disable=import-outside-toplevel

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
            if appl.values == {}:
                appl = DaikinAirBase(device_id, session)
        await appl.init()
        return appl

    @staticmethod
    def parse_response(response_body):
        """Parse respose from Daikin."""
        response = dict([e.split('=') for e in response_body.split(',')])
        if 'ret' not in response:
            raise ValueError("missing 'ret' field in response")
        if response['ret'] != 'OK':
            return {}
        if 'name' in response:
            response['name'] = unquote(response['name'])
        return response

    @staticmethod
    def translate_mac(value):
        """Return translated MAC address."""
        return ':'.join(value[i : i + 2] for i in range(0, len(value), 2))

    @staticmethod
    def discover_ip(device_id):
        """Return translated name to ip address."""
        try:
            socket.inet_aton(device_id)
            device_ip = device_id  # id is an IP
        except socket.error:
            device_ip = None

        if device_ip is None:
            # id is a common name, try discovery
            device_name = discovery.get_name(device_id)
            if device_name is None:
                # try DNS
                try:
                    device_ip = socket.gethostbyname(device_id)
                except socket.gaierror as exc:
                    raise ValueError("no device found for %s" % device_id) from exc
            else:
                device_ip = device_name['ip']
        return device_id

    def __init__(self, device_id, session=None):
        """Init the pydaikin appliance, representing one Daikin device."""
        self.values = {}
        self.session = session
        self._energy_consumption_history = defaultdict(list)
        if session:
            self._device_ip = device_id
        else:
            self._device_ip = self.discover_ip(device_id)

    def __getitem__(self, name):
        """Return values from self.value."""
        if name in self.values:
            return self.values[name]
        raise AttributeError("No such attribute: " + name)

    async def init(self):
        """Init status."""
        # Re-defined in all sub-classes
        raise NotImplementedError

    async def _get_resource(self, resource, retries=3):
        """Update resource."""
        try:
            if self.session and not self.session.closed:
                return await self._run_get_resource(resource)
            async with ClientSession() as self.session:
                return await self._run_get_resource(resource)
        except ServerDisconnectedError as error:
            _LOGGER.debug("ServerDisconnectedError %d", retries)
            if retries == 0:
                raise error
            return await self._get_resource(resource, retries=retries - 1)

    async def _run_get_resource(self, resource):
        """Make the http request."""
        async with self.session.get(f'http://{self._device_ip}/{resource}') as resp:
            return await self._handle_response(resp)

    async def _handle_response(self, resp):
        """Handle the http response."""
        if resp.status == 200:
            return self.parse_response(await resp.text())
        if resp.status == 403:
            raise HTTPForbidden
        return {}

    async def update_status(self, resources=None):
        """Update status from resources."""
        if resources is None:
            resources = self.INFO_RESOURCES
        _LOGGER.debug("Updating %s", resources)
        for resource in resources:
            self.values.update(await self._get_resource(resource))

        self._register_energy_consumption_history()

    def show_values(self, only_summary=False):
        """Print values."""
        if only_summary:
            keys = self.VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, val) = self.represent(key)
                print("%20s: %s" % (k, val))

    def log_sensors(self, file):
        """Log sensors to a file."""
        data = [
            ('datetime', datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')),
            ('in_temp', self.inside_temperature),
        ]
        if self.support_outside_temperature:
            data.append(('out_temp', self.outside_temperature))
        if self.support_compressor_frequency:
            data.append(('cmp_freq', self.compressor_frequency))
        if self.support_energy_consumption:
            data.append(
                ('total_today', self.energy_consumption(ATTR_TOTAL, TIME_TODAY))
            )
            data.append(('cool_today', self.energy_consumption(ATTR_COOL, TIME_TODAY)))
            data.append(('heat_today', self.energy_consumption(ATTR_HEAT, TIME_TODAY)))
            data.append(('total_power', self.current_total_power_consumption))
            data.append(('cool_power', self.last_hour_cool_power_consumption))
            data.append(('heat_power', self.last_hour_heat_power_consumption))
        if file.tell() == 0:
            file.write(','.join(k for k, _ in data))
            file.write('\n')
        file.write(','.join(str(v) for _, v in data))
        file.write('\n')
        file.flush()

    def show_sensors(self):
        """Print sensors."""
        data = [
            datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            f'in_temp={int(self.inside_temperature)}°C',
        ]
        if self.support_outside_temperature:
            data.append(f'out_temp={int(self.outside_temperature)}°C')
        if self.support_compressor_frequency:
            data.append(f'cmp_freq={int(self.compressor_frequency)}Hz')
        if self.support_energy_consumption:
            data.append(
                f'total_today={self.energy_consumption(ATTR_TOTAL, TIME_TODAY):.01f}kWh'
            )
            data.append(
                f'cool_today={self.energy_consumption(ATTR_COOL, TIME_TODAY):.01f}kWh'
            )
            data.append(
                f'heat_today={self.energy_consumption(ATTR_HEAT, TIME_TODAY):.01f}kWh'
            )
            data.append(f'total_power={self.current_total_power_consumption:.02f}kW')
            data.append(f'cool_power={self.last_hour_cool_power_consumption:.01f}kW')
            data.append(f'heat_power={self.last_hour_heat_power_consumption:.01f}kW')
        print('  '.join(data))

    def represent(self, key):
        """Return translated value from key."""
        k = self.VALUES_TRANSLATION.get(key, key)

        # adapt the value
        val = self.values[key]

        if key == 'mode' and self.values['pow'] == '0':
            val = 'off'
        elif key == 'mac':
            val = self.translate_mac(val)
            val = unquote(self.values[key]).split(';')
        else:
            val = self.daikin_to_human(key, val)

        _LOGGER.log(logging.NOTSET, 'Represent: %s, %s, %s', key, k, val)
        return (k, val)

    def _parse_number(self, dimension):
        """Parse float number."""
        try:
            return float(self.values.get(dimension))
        except (TypeError, ValueError):
            return None

    @property
    def device_ip(self):
        """Return device's IP address."""
        return self._device_ip

    @property
    def mac(self):
        """Return device's MAC address."""
        return self.values.get('mac', self._device_ip)

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return 'en_hol' in self.values

    @property
    def support_fan_rate(self):
        """Return True if the device support setting fan_rate."""
        return 'f_rate' in self.values

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return 'f_dir' in self.values

    @property
    def support_outside_temperature(self):
        """Return True if the device is not an AirBase unit."""
        return self.outside_temperature is not None

    @property
    def support_humidity(self):
        """Return True if the device has humidity sensor."""
        return False

    @property
    def support_advanced_modes(self):
        """Return True if the device supports advanced modes."""
        return 'adv' in self.values

    @property
    def support_compressor_frequency(self):
        """Return True if the device supports compressor frequency."""
        return 'cmpfreq' in self.values

    @property
    def support_energy_consumption(self):
        """Return True if the device supports energy consumption monitoring."""
        return super().support_energy_consumption

    @property
    def outside_temperature(self):
        """Return current outside temperature."""
        return self._parse_number('otemp')

    @property
    def inside_temperature(self):
        """Return current inside temperature."""
        return self._parse_number('htemp')

    @property
    def target_temperature(self):
        """Return current target temperature."""
        return self._parse_number('stemp')

    @property
    def compressor_frequency(self):
        """Return current compressor frequency."""
        return self._parse_number('cmpfreq')

    @property
    def humidity(self):
        """Return current humidity."""
        return self._parse_number('hhum')

    @property
    def target_humidity(self):
        """Return target humidity."""
        return self._parse_number('shum')

    @property
    def current_total_power_consumption(self):
        """Return the current total power consumption in kW."""
        # We tolerate a 50% delay in consumption measure
        return self.current_power_consumption(
            mode=ATTR_TOTAL, exp_diff_time_margin_factor=0.5
        )

    @property
    def last_hour_cool_power_consumption(self):
        """Return the last hour cool power consumption of a given mode in kW."""
        # We tolerate a 5 minutes delay in consumption measure
        return self.current_power_consumption(
            mode=ATTR_COOL,
            exp_diff_time_value=timedelta(minutes=60),
            exp_diff_time_margin_factor=timedelta(minutes=5),
        )

    @property
    def last_hour_heat_power_consumption(self):
        """Return the last hour heat power consumption of a given mode in kW."""
        # We tolerate a 5 minutes margin in consumption measure
        return self.current_power_consumption(
            mode=ATTR_HEAT,
            exp_diff_time_value=timedelta(minutes=60),
            exp_diff_time_margin_factor=timedelta(minutes=5),
        )

    @property
    def fan_rate(self):
        """Return list of supported fan rates."""
        return list(map(str.title, self.TRANSLATIONS.get('f_rate', {}).values()))

    @property
    def swing_modes(self):
        """Return list of supported swing modes."""
        return list(map(str.title, self.TRANSLATIONS.get('f_dir', {}).values()))

    async def set(self, settings):
        """Set settings on Daikin device."""
        raise NotImplementedError

    async def set_holiday(self, mode):
        """Set holiday mode."""
        raise NotImplementedError

    async def set_advanced_mode(self, mode, value):
        """Enable or disable advanced modes."""
        raise NotImplementedError

    async def set_streamer(self, mode):
        """Enable or disable the streamer."""
        raise NotImplementedError

    @property
    def zones(self):
        """Return list of zones."""
        return

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        raise NotImplementedError
