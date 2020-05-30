"""Pydaikin base appliance, represent a Daikin device."""

from collections import defaultdict, namedtuple
from datetime import datetime, timedelta
import logging
import socket
from urllib.parse import unquote

from aiohttp import ClientSession, ServerDisconnectedError
from aiohttp.web_exceptions import HTTPForbidden

import pydaikin.discovery as discovery

_LOGGER = logging.getLogger(__name__)

ENERGY_CONSUMPTION_MAX_HISTORY = timedelta(hours=3)

ATTR_TOTAL = 'total'
ATTR_COOL = 'cool'
ATTR_HEAT = 'heat'

TIME_TODAY = 'today'
TIME_YESTERDAY = 'yesterday'
TIME_THIS_YEAR = 'this_year'
TIME_LAST_YEAR = 'last_year'

EnergyConsumptionParser = namedtuple(
    'EnergyConsumptionParser', ['dimension', 'reducer', 'divider']
)

EnergyConsumptionState = namedtuple(
    'EnergyConsumptionState', ['datetime', 'today', 'yesterday']
)


class Appliance:  # pylint: disable=too-many-public-methods
    """Daikin main appliance class."""

    TRANSLATIONS = {}

    VALUES_TRANSLATION = {}

    VALUES_SUMMARY = []

    INFO_RESOURCES = []

    ENERGY_CONSUMPTION_PARSERS = {
        f'{ATTR_TOTAL}_{TIME_TODAY}': EnergyConsumptionParser(
            dimension='datas', reducer=lambda values: values[-1], divider=1000
        ),
        f'{ATTR_COOL}_{TIME_TODAY}': EnergyConsumptionParser(
            dimension='curr_day_cool', reducer=sum, divider=10
        ),
        f'{ATTR_HEAT}_{TIME_TODAY}': EnergyConsumptionParser(
            dimension='curr_day_heat', reducer=sum, divider=10
        ),
        f'{ATTR_TOTAL}_{TIME_YESTERDAY}': EnergyConsumptionParser(
            dimension='datas', reducer=lambda values: values[-2], divider=1000
        ),
        f'{ATTR_COOL}_{TIME_YESTERDAY}': EnergyConsumptionParser(
            dimension='prev_1day_cool', reducer=sum, divider=10
        ),
        f'{ATTR_HEAT}_{TIME_YESTERDAY}': EnergyConsumptionParser(
            dimension='prev_1day_heat', reducer=sum, divider=10
        ),
        f'{ATTR_TOTAL}_{TIME_THIS_YEAR}': EnergyConsumptionParser(
            dimension='this_year', reducer=sum, divider=1
        ),
        f'{ATTR_TOTAL}_{TIME_LAST_YEAR}': EnergyConsumptionParser(
            dimension='previous_year', reducer=sum, divider=1
        ),
    }

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
        return sorted(list(cls.TRANSLATIONS[dimension].values()))

    @staticmethod
    async def factory(device_id, session=None, **kwargs):
        """Factory to init the corresponding Daikin class."""
        from .daikin_airbase import (  # pylint: disable=import-outside-toplevel
            DaikinAirBase,
        )
        from .daikin_brp069 import (  # pylint: disable=import-outside-toplevel
            DaikinBRP069,
        )
        from .daikin_skyfi import DaikinSkyFi  # pylint: disable=import-outside-toplevel
        from .daikin_brp072c import (  # pylint: disable=import-outside-toplevel
            DaikinBRP072C,
        )

        if 'password' in kwargs and kwargs['password'] is not None:
            appl = DaikinSkyFi(device_id, session, password=kwargs['password'])
        elif 'key' in kwargs and kwargs['key'] is not None:
            appl = DaikinBRP072C(
                device_id, session, key=kwargs['key'], uuid=kwargs.get('uuid'),
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
                except socket.gaierror:
                    raise ValueError("no device found for %s" % device_id)
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
            if resp.status == 200:
                return self.parse_response(await resp.text())
            elif resp.status == 403:
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

    def _register_energy_consumption_history(self):
        if not self.support_energy_consumption:
            return

        for mode in (ATTR_TOTAL, ATTR_COOL, ATTR_HEAT):
            new_state = EnergyConsumptionState(
                datetime=datetime.utcnow(),
                today=self.energy_consumption(mode=mode, time=TIME_TODAY),
                yesterday=self.energy_consumption(mode=mode, time=TIME_YESTERDAY),
            )
            if new_state.today is None:
                continue

            if self._energy_consumption_history[mode]:
                old_state = self._energy_consumption_history[mode][0]

                if new_state.today == old_state.today:
                    if new_state.yesterday == old_state.yesterday:
                        # State has not changed, nothing to register
                        continue

            self._energy_consumption_history[mode].insert(0, new_state)

            # We can remove very old states (except the latest one)
            idx = (
                min(
                    (
                        i
                        for i, (dt, _, _) in enumerate(
                            self._energy_consumption_history[mode]
                        )
                        if dt < datetime.utcnow() - ENERGY_CONSUMPTION_MAX_HISTORY
                    ),
                    default=len(self._energy_consumption_history[mode]),
                )
                + 1
            )

            self._energy_consumption_history[mode] = self._energy_consumption_history[
                mode
            ][:idx]

    def show_values(self, only_summary=False):
        """Print values."""
        if only_summary:
            keys = self.VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, val) = self.represent(key)
                print("%18s: %s" % (k, val))

    def show_sensors(self):
        """Print sensors."""
        data = [
            datetime.utcnow().strftime('%m/%d/%Y %H:%M:%S'),
            f'in_temp={int(self.inside_temperature)}°C',
        ]
        if self.support_outside_temperature:
            data.append(f'out_temp={int(self.outside_temperature)}°C')
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
            data.append(f'total_power={self.current_total_power_consumption:.01f}kW')
            data.append(f'cool_power={self.last_hour_cool_energy_consumption:.01f}kW')
            data.append(f'heat_power={self.last_hour_heat_energy_consumption:.01f}kW')
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

    def _temperature(self, dimension):
        """Parse temperature."""
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
    def support_energy_consumption(self):
        """Return True if the device supports energy consumption monitoring."""
        return (self.energy_consumption(mode=ATTR_TOTAL, time=TIME_THIS_YEAR) or 0) + (
            self.energy_consumption(mode=ATTR_TOTAL, time=TIME_LAST_YEAR) or 0
        ) > 0

    @property
    def outside_temperature(self):
        """Return current outside temperature."""
        return self._temperature('otemp')

    @property
    def inside_temperature(self):
        """Return current inside temperature."""
        return self._temperature('htemp')

    @property
    def target_temperature(self):
        """Return current target temperature."""
        return self._temperature('stemp')

    def energy_consumption(self, mode=ATTR_TOTAL, time=TIME_TODAY):
        """Return today energy consumption in kWh."""
        parser = self.ENERGY_CONSUMPTION_PARSERS.get(f'{mode}_{time}')
        if parser is None:
            raise ValueError(f'Unsupported mode {mode} on {time}.')

        try:
            values = [int(x) for x in self.values.get(parser.dimension).split('/')]
            value = parser.reducer(values)
            value /= parser.divider
            return value
        except (TypeError, IndexError, AttributeError, ValueError):
            return None

    def delta_energy_consumption(
        self, time_window, mode=ATTR_TOTAL, lag_window=None, early_break=False
    ):
        """Return the delta energy consumption of a given mode and over the given time_window."""
        if not self._energy_consumption_history:
            # The sensor has not been properly initialized
            return None

        if lag_window is None:
            lag_window = timedelta(seconds=0)

        energy = 0
        history = self._energy_consumption_history[mode]
        for curr, prev in zip(history, history[1:]):
            # We iterate over the history backward and pairwise
            if curr.datetime > datetime.utcnow() - lag_window:
                continue
            if curr.datetime <= datetime.utcnow() - (time_window + lag_window):
                break
            if curr.today > prev.today:
                # Normal behavior, today state is growing
                energy += curr.today - prev.today
            elif curr.yesterday is None:
                _LOGGER.error(
                    f'Decreasing today state and missing yesterday state caused an impossible energy consumption measure of {mode}'
                )
                return None
            elif curr.yesterday >= prev.today:
                # If today state is not growing (or even declines), we probably have shifted 1 day
                # Thus we should have yesterday state greater or equal to previous today state
                # (in most cases it will be equal)
                energy += curr.yesterday - prev.today
                energy += curr.today
            else:
                _LOGGER.error(f'Impossible energy consumption measure of {mode}')
                return None
            if early_break:
                break

        return energy

    @property
    def current_total_power_consumption(self):
        """Return the current total power consumption in kW."""
        time_window = timedelta(minutes=30)
        return self.delta_energy_consumption(time_window, mode='total') * (
            timedelta(hours=1) / time_window
        )

    @property
    def last_hour_cool_energy_consumption(self):
        """Return the last hour cool power consumption of a given mode in kWh."""
        # We tolerate a 5 minutes delay in consumption measure
        time_window = timedelta(minutes=60)
        lag_window = timedelta(minutes=5)
        return self.delta_energy_consumption(
            time_window, mode=ATTR_COOL, lag_window=lag_window, early_break=True
        )

    @property
    def last_hour_heat_energy_consumption(self):
        """Return the last hour heat power consumption of a given mode in kWh."""
        # We tolerate a 5 minutes margin in consumption measure
        time_window = timedelta(minutes=60)
        lag_window = timedelta(minutes=5)
        return self.delta_energy_consumption(
            time_window, mode=ATTR_HEAT, lag_window=lag_window, early_break=True
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

    @property
    def zones(self):
        """Return list of zones."""
        return

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        raise NotImplementedError
