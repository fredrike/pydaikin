import socket

import pydaikin.discovery as discovery
import pydaikin.entity as entity

import aiohttp
import logging

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
}

TRANSLATIONS_AIRBASE = {
    'mode': {
        '0': 'fan',
        '1': 'hot',
        '2': 'cool',
        '7': 'dry',
    },
    'f_rate': {
        'A': 'auto',
        'B': 'silence',
        '1': '1',
        '2': '2',
        '3': '3',
        '4': '4',
        '5': '5',
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
}


def daikin_to_human(dimension, value, airbase=False):
    if airbase:
        translations = TRANSLATIONS_AIRBASE
    else:
        translations = TRANSLATIONS
    return translations.get(dimension, {}).get(value, str(value))


def human_to_daikin(dimension, value, airbase=False):
    if airbase:
        translations = TRANSLATIONS_AIRBASE
    else:
        translations = TRANSLATIONS
    translations_rev = {
        dim: {v: k
              for k, v in item.items()}
        for dim, item in translations.items()
    }
    return translations_rev.get(dimension, {}).get(value, value)


def daikin_values(dimension):
    return sorted(list(TRANSLATIONS[dimension].values()))


class Appliance(entity.Entity):
    def __init__(self, id, session=None):

        entity.Entity.__init__(self)
        self._airbase = False
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
            self.values.update({'htemp': '-', 'otemp': '-', 'shum': '--'})
            await self.update_status(AIRBASE_RESOURCES)
        else:
            await self.update_status(HTTP_RESOURCES[1:])

    @property
    def support_fan_mode(self):
        return self.values.get('f_rate') is not None

    @property
    def support_swing_mode(self):
        return self.values.get('f_dir') is not None and not self._airbase

    async def get_resource(self, resource):
        if self.session and not self.session.closed:
            return await self._get_resource(resource)
        else:
            async with aiohttp.ClientSession() as self.session:
                return await self._get_resource(resource)

    async def _get_resource(self, resource):
        if self._airbase:
            resource = 'skyfi/%s' % resource
        async with self.session.get(
                'http://%s/%s' % (self.ip, resource)) as resp:
            if resp.status == 200:
                return self.parse_response(await resp.text())
            return {}

    async def update_status(self, resources=INFO_RESOURCES):
        _LOGGER.debug("Updating %s", resources)
        for resource in resources:
            self.values.update(await self.get_resource(resource))

    def show_values(self, only_summary=False):
        if only_summary:
            keys = VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, v) = self.represent(key)
                print("%18s: %s" % (k, v))

    def translate_mac(self, value):
        return ':'.join(value[i:i + 2] for i in range(0, len(value), 2))

    def represent(self, key):
        # adapt the key
        k = VALUES_TRANSLATION.get(key, key)

        # adapt the value
        v = self.values[key]

        if key == 'mode' and self.values['pow'] == '0':
                v = 'off'
        elif key == 'mac':
            v = self.translate_mac(v)
        else:
            v = daikin_to_human(key, v, self._airbase)

        _LOGGER.debug('Represent: %s, %s, %s', key, k, v)
        return (k, v)

    async def set(self, settings):
        # start with current values
        current_val = await self.get_resource('aircon/get_control_info')

        # Merge current_val with mapped settings
        self.values.update(current_val)
        self.values.update({
            k: human_to_daikin(k, v, self._airbase)
            for k, v in settings.items()
        })

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

        query_c = \
            'aircon/set_control_info?pow=%s&mode=%s&stemp=%s&shum=%s' % \
            (
                self.values['pow'],
                self.values['mode'],
                self.values['stemp'],
                self.values['shum'],
            )

        # Apparently some remote controllers doesn't support f_rate and f_dir
        if self.support_fan_mode:
            if self._airbase and self.values['f_rate'] != 5:
                    self.values['f_rate'] = 1
            query_c += '&f_rate=%s' % self.values['f_rate']
        if self.support_swing_mode or self._airbase:
            query_c += '&f_dir=%s' % self.values['f_dir']

        if self._airbase:
            query_c += '&lpw=&f_airside=0'

        query_h = ('common/set_holiday?en_hol=%s' % self.values.get('en_hol'))

        _LOGGER.debug("Sending query_c: %s", query_c)
        if self.values.get('en_hol', '') == "1":
            await self.get_resource(query_h)
        else:
            await self.get_resource(query_c)
