"""Pydaikin appliance, represent a Daikin device."""

import logging
import socket
from urllib.parse import quote, unquote

from aiohttp import ClientSession, ServerDisconnectedError

import pydaikin.discovery as discovery

_LOGGER = logging.getLogger(__name__)


class Appliance:
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
        return sorted(list(cls.TRANSLATIONS[dimension].values()))

    @staticmethod
    async def factory(device_id, session=None, **kwargs):
        """Factory to init the corresponding Daikin class."""
        from .daikin_skyfi import DaikinSkyFi

        if 'password' in kwargs and kwargs['password'] is not None:
            _class = DaikinSkyFi(device_id, session, password=kwargs['password'])
        else:
            _class = await DaikinBRP069(device_id, session).init()
        return _class

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

    def __init__(self, device_id, session=None):
        """Init the pydaikin appliance, representing one Daikin device."""
        self.values = {}
        self.session = session
        if session:
            self._device_ip = device_id
            return

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

        self._device_ip = device_ip

    def __getitem__(self, name):
        """Return values from self.value."""
        if name in self.values:
            return self.values[name]
        raise AttributeError("No such attribute: " + name)

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
            return {}

    async def update_status(self, resources=None):
        """Update status from resources."""
        if resources is None:
            resources = self.INFO_RESOURCES
        _LOGGER.debug("Updating %s", resources)
        for resource in resources:
            self.values.update(await self._get_resource(resource))

    def show_values(self, only_summary=False):
        """Print values."""
        if only_summary:
            keys = self.VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, val) = self._represent(key)
                print("%18s: %s" % (k, val))

    def _represent(self, key):
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

        _LOGGER.debug('Represent: %s, %s, %s', key, k, val)
        return (k, val)

    def _temperature(self, dimension):
        """Parse temperature."""
        try:
            return float(self.values.get(dimension))
        except ValueError:
            return False

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

    @property
    def fan_rate(self):
        """Return list of supported fan modes."""
        return list(map(str.title, self.TRANSLATIONS.get('f_rate', {}).values()))

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
        'f_dir': {'0': 'off', '1': 'vertical', '2': 'horizontal', '3': '3d',},
        'en_hol': {'0': 'off', '1': 'on',},
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
        'aircon/get_week_power',
        'aircon/get_year_power',
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
    ]

    VALUES_TRANSLATION = {
        'otemp': 'outside temp',
        'htemp': 'inside temp',
        'stemp': 'target temp',
        'ver': 'firmware adapter',
        'pow': 'power',
        'cmpfreq': 'compressor demand',
        'f_rate': 'fan rate',
        'f_dir': 'fan direction',
        'err': 'error code',
        'en_hol': 'away_mode',
    }

    async def init(self):
        """Init status."""
        await self.update_status(self.HTTP_RESOURCES[:1])
        if self.values == {}:
            # The device is most likely an AirBase unit.
            return await DaikinAirBase(self._device_ip, self.session).init()
        await self.update_status(self.HTTP_RESOURCES[1:])
        return self

    async def set(self, settings):
        """Set settings on Daikin device."""
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

    async def set_zone(self, zone_id, status):
        """Set zone status."""


class DaikinAirBase(DaikinBRP069):
    """Daikin class for AirBase (BRP15B61) units."""

    TRANSLATIONS = dict(
        DaikinBRP069.TRANSLATIONS,
        **{
            'mode': {'0': 'fan', '1': 'hot', '2': 'cool', '3': 'auto', '7': 'dry',},
            'f_rate': {'1': 'low', '3': 'mid', '5': 'high',},
        },
    )

    RESOURCES = [
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
        await self.update_status(self.RESOURCES)
        if self.values['frate_steps'] == '2':
            self.TRANSLATIONS['f_rate'] = {'1': 'low', '5': 'high'}
        return self

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

        query_c = 'aircon/set_control_info?pow={pow}&mode={mode}&stemp={stemp}&shum={shum}'.format(
            **self.values
        )

        # Apparently some remote controllers doesn't support f_rate and f_dir
        if self.support_fan_rate:
            query_c += f'&f_rate={self.values["f_rate"]}'
        query_c += f'&f_dir={self.values["f_dir"]}'

        query_c += '&lpw=&f_airside=0'

        _LOGGER.debug("Sending query_c: %s", query_c)
        await self._get_resource(query_c)

    def _represent(self, key):
        """Return translated value from key."""
        k, val = super()._represent(key)

        if key in ['zone_name', 'zone_onoff']:
            val = unquote(self.values[key]).split(';')

        return (k, val)

    @property
    def zones(self):
        """Return list of zones."""
        if not self.values.get('zone_name'):
            return None
        zone_onoff = self._represent('zone_onoff')[1]
        return [
            (name.strip(' +,'), zone_onoff[i])
            for i, name in enumerate(self._represent('zone_name')[1])
        ]

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        current_state = await self._get_resource('aircon/get_zone_setting')
        self.values.update(current_state)
        zone_onoff = self._represent('zone_onoff')[1]
        zone_onoff[zone_id] = status
        self.values['zone_onoff'] = quote(';'.join(zone_onoff)).lower()

        query = 'aircon/set_zone_setting?zone_name={}&zone_onoff={}'.format(
            current_state['zone_name'], self.values['zone_onoff'],
        )

        _LOGGER.debug("Set zone:: %s", query)
        await self._get_resource(query)
