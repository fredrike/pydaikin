"""Pydaikin appliance, represent a Daikin device."""

import logging
import socket

from aiohttp import ClientSession, ServerDisconnectedError

import pydaikin.discovery as discovery
import pydaikin.entity as entity

_LOGGER = logging.getLogger(__name__)

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

AIRBASE_RESOURCES = [
    'common/basic_info',
    'aircon/get_control_info',
    'aircon/get_model_info',
    'aircon/get_zone_setting',
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

TRANSLATIONS_AIRBASE = {
    'mode': {'0': 'fan', '1': 'hot', '2': 'cool', '3': 'auto', '7': 'dry',},
    'f_rate': {'1': 'low', '3': 'mid', '5': 'high',},
    'f_dir': {'0': 'off', '1': 'vertical', '2': 'horizontal', '3': '3d',},
    'en_hol': {'0': 'off', '1': 'on',},
}


def daikin_to_human(dimension, value, airbase=False):
    """Return converted values from Daikin to Human."""
    if airbase:
        translations = TRANSLATIONS_AIRBASE
    else:
        translations = TRANSLATIONS
    return translations.get(dimension, {}).get(value, str(value))


def human_to_daikin(dimension, value, airbase=False):
    """Return converted values from Human to Daikin."""
    if airbase:
        translations = TRANSLATIONS_AIRBASE
    else:
        translations = TRANSLATIONS
    translations_rev = {
        dim: {v: k for k, v in item.items()} for dim, item in translations.items()
    }
    return translations_rev.get(dimension, {}).get(value, value)


def daikin_values(dimension):
    """Return sorted list of translated values."""
    return sorted(list(TRANSLATIONS[dimension].values()))


class Appliance(entity.Entity):
    """Daikin appliance class."""

    def __init__(self, id, session=None):
        """Init the pydaikin appliance, representing one Daikin device."""
        entity.Entity.__init__(self)
        self._airbase = False
        self._fan_rate = TRANSLATIONS['f_rate']
        self.session = session

        if session:
            self.ip = id
            return

        try:
            socket.inet_aton(id)
            ip = id  # id is an IP
        except socket.error:
            ip = None

        if ip is None:
            # id is a common name, try discovery
            e = discovery.get_name(id)
            if e is None:
                # try DNS
                try:
                    ip = socket.gethostbyname(id)
                except socket.gaierror:
                    raise ValueError("no device found for %s" % id)
            else:
                ip = e['ip']

        self.ip = ip

    async def init(self):
        """Init status."""
        await self.update_status(HTTP_RESOURCES[:1])
        if self.values == {}:
            self._airbase = True
            INFO_RESOURCES.append('aircon/get_zone_setting')
            self.values.update({'htemp': '-', 'otemp': '-', 'shum': '--'})
            await self.update_status(AIRBASE_RESOURCES)
            if self.values['frate_steps'] == '2':
                self._fan_rate = {'1': 'low', '5': 'high'}
            else:
                self._fan_rate = TRANSLATIONS_AIRBASE['f_rate']
        else:
            await self.update_status(HTTP_RESOURCES[1:])

    @property
    def fan_rate(self):
        """Return list of supported fan modes."""
        return list(map(str.title, self._fan_rate.values()))

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return not self._airbase and 'en_hol' in self.values

    @property
    def support_fan_rate(self):
        """Return True if the device support setting fan_rate."""
        return self.values.get('f_rate') is not None

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return self.values.get('f_dir') is not None and not self._airbase

    @property
    def support_outside_temperature(self):
        """Return True if the device is not an AirBase unit."""
        return not (self._airbase and not self.outside_temperature)

    async def get_resource(self, resource, retries=3):
        """Update resource."""
        try:
            if self.session and not self.session.closed:
                return await self._get_resource(resource)
            else:
                async with ClientSession() as self.session:
                    return await self._get_resource(resource)
        except ServerDisconnectedError as error:
            _LOGGER.debug("ServerDisconnectedError %d", retries)
            if retries == 0:
                raise error
            return await self.get_resource(resource, retries=retries - 1)

    async def _get_resource(self, resource):
        """Make the http request."""
        if self._airbase:
            resource = 'skyfi/%s' % resource
        async with self.session.get('http://%s/%s' % (self.ip, resource)) as resp:
            if resp.status == 200:
                return self.parse_response(await resp.text())
            return {}

    async def update_status(self, resources=INFO_RESOURCES):
        """Update status from resources."""
        _LOGGER.debug("Updating %s", resources)
        for resource in resources:
            self.values.update(await self.get_resource(resource))

    def show_values(self, only_summary=False):
        """Print values."""
        if only_summary:
            keys = VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, v) = self.represent(key)
                print("%18s: %s" % (k, v))

    def translate_mac(self, value):
        """Return translated MAC address."""
        return ':'.join(value[i : i + 2] for i in range(0, len(value), 2))

    def represent(self, key):
        """Return translated value from key."""
        from urllib.parse import unquote

        # adapt the key
        k = VALUES_TRANSLATION.get(key, key)

        # adapt the value
        v = self.values[key]

        if key == 'mode' and self.values['pow'] == '0':
            v = 'off'
        elif key == 'mac':
            v = self.translate_mac(v)
        elif key in ['zone_name', 'zone_onoff']:
            v = unquote(self.values[key]).split(';')
        else:
            v = daikin_to_human(key, v, self._airbase)

        _LOGGER.debug('Represent: %s, %s, %s', key, k, v)
        return (k, v)

    async def set(self, settings):
        """Set settings on Daikin device."""
        # start with current values
        current_val = await self.get_resource('aircon/get_control_info')

        # Merge current_val with mapped settings
        self.values.update(current_val)
        self.values.update(
            {k: human_to_daikin(k, v, self._airbase) for k, v in settings.items()}
        )

        # we are using an extra mode "off" to power off the unit
        if settings.get('mode', '') == 'off':
            self.values['pow'] = '0'
            # some units are picky with the off mode
            self.values['mode'] = current_val['mode']
        else:
            self.values['pow'] = '1'

        # Use settings for respecitve mode (dh and dt)
        for k, v in {'stemp': 'dt', 'shum': 'dh', 'f_rate': 'dfr'}.items():
            if k not in settings:
                key = v + self.values['mode']
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
        if self.support_swing_mode or self._airbase:
            query_c += '&f_dir=%s' % self.values['f_dir']

        if self._airbase:
            query_c += '&lpw=&f_airside=0'

        _LOGGER.debug("Sending query_c: %s", query_c)
        await self.get_resource(query_c)

    async def set_holiday(self, mode):
        """Set holiday mode."""
        value = human_to_daikin('en_hol', mode, self._airbase)
        if value in ('0', '1'):
            query_h = 'common/set_holiday?en_hol=%s' % value
            self.values['en_hol'] = value
            _LOGGER.debug("Sending query: %s", query_h)
            await self.get_resource(query_h)

    @property
    def zones(self):
        """Return list of zones."""
        if not self.values.get('zone_name'):
            return
        zone_onoff = self.represent('zone_onoff')[1]
        return [
            (name.strip(' +,'), zone_onoff[i])
            for i, name in enumerate(self.represent('zone_name')[1])
        ]

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        from urllib.parse import quote

        current_state = await self.get_resource('aircon/get_zone_setting')
        self.values.update(current_state)
        zone_onoff = self.represent('zone_onoff')[1]
        zone_onoff[zone_id] = status
        self.values['zone_onoff'] = quote(';'.join(zone_onoff)).lower()

        query = 'aircon/set_zone_setting?zone_name={}&zone_onoff={}'.format(
            current_state['zone_name'], self.values['zone_onoff'],
        )

        _LOGGER.debug("Set zone:: %s", query)
        await self.get_resource(query)

    def _temperature(self, dimension):
        """Parse temperature."""
        try:
            return float(self.values.get(dimension))
        except ValueError:
            return

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
