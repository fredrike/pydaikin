import pydaikin.entity as entity
import pydaikin.discovery as discovery

import socket
import requests

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

# Reversed list of translations
TRANSLATIONS_REV = {
    dim: {v: k
          for k, v in item.items()}
    for dim, item in TRANSLATIONS.items()
}


def daikin_to_human(dimension, value):
    return TRANSLATIONS.get(dimension, {}).get(value, value)


def human_to_daikin(dimension, value):
    return TRANSLATIONS_REV.get(dimension, {}).get(value, value)


def daikin_values(dimension):
    return sorted(list(TRANSLATIONS[dimension].values()))


class Appliance(entity.Entity):
    def __init__(self, id):

        entity.Entity.__init__(self)

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

        self.update_status(HTTP_RESOURCES)

    @property
    def support_fan_mode(self):
        return self.values.get('f_rate') is not None

    @property
    def support_swing_mode(self):
        return self.values.get('f_dir') is not None

    def get_resource(self, resource):
        r = self.session.get('http://%s/%s' % (self.ip, resource))
        if r.status_code == 200:
            return self.parse_response(r.text)
        return {}

    def update_status(self, resources=INFO_RESOURCES):
        for resource in resources:
            with requests.Session() as self.session:
                self.values.update(self.get_resource(resource))

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

        if key == 'mode':
            if self.values['pow'] == '0':
                v = 'off'
            else:
                v = daikin_to_human(key, v)

        elif key in TRANSLATIONS:
            v = daikin_to_human(key, v)
        elif key == 'mac':
            v = self.translate_mac(v)

        return (k, v)

    def set(self, settings):
        # start with current values
        current_val = self.get_resource('aircon/get_control_info')

        # Merge current_val with mapped settings
        self.values.update(current_val)
        self.values.update(
            {k: human_to_daikin(k, v)
             for k, v in settings.items()})

        # we are using an extra mode "off" to power off the unit
        if settings.get('mode', '') == 'off':
            self.values['pow'] = '0'
            self.values['mode'] = current_val['mode']  # some units are picky with the off mode
        else:
            self.values['pow'] = '1'

        # Use settings for respecitve mode (dh and dt)
        for k, v in {'stemp': 'dt', 'shum': 'dh'}.items():
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
            query_c += '&f_rate=%s' % self.values['f_rate']
        if self.support_swing_mode:
            query_c += '&f_dir=%s' % self.values['f_dir']

        query_h = ('common/set_holiday?en_hol=%s' % self.values.get('en_hol'))

        with requests.Session() as self.session:
            if self.values.get('en_hol', '') == "1":
                self.get_resource(query_h)
            else:
                self.get_resource(query_c)
