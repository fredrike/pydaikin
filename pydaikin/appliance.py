import pydaikin.entity as entity
import pydaikin.discovery as discovery

import socket
import requests

HTTP_RESOURCES = ['common/basic_info'
                  , 'common/get_remote_method'
                  , 'aircon/get_sensor_info'
                  , 'aircon/get_model_info'
                  , 'aircon/get_control_info'
                  , 'aircon/get_target'
                  , 'aircon/get_price'
                  , 'common/get_holiday'
                  , 'common/get_notify'
                  , 'aircon/get_week_power'
                  , 'aircon/get_year_power'
              ]

VALUES_SUMMARY = ['name', 'ip', 'mac', 'mode', 'f_rate', 'f_dir'
                  , 'htemp', 'otemp', 'stemp'
                  , 'cmpfreq', 'en_hol', 'err']

VALUES_TRANSLATION = {
    'otemp'    : 'outside temp'
    , 'htemp'  : 'inside temp'
    , 'stemp'  : 'target temp'
    , 'ver'    : 'firmware adapter'
    , 'pow'    : 'power'
    , 'cmpfreq': 'compressor demand'
    , 'f_rate' : 'fan rate'
    , 'f_dir'  : 'fan direction'
    , 'err'    : 'error code'
    , 'en_hol' : 'away_mode'
}

TRANSLATIONS = {
    'mode' : {
        '2': 'dry',
        '3': 'cool',
        '4': 'hot',
        '6': 'fan',
        '0': 'auto',
        '1': 'auto-1',
        '7': 'auto-7',
        '10': 'off'
    },
    'f_rate' : {
        'A': 'auto',
        'B': 'silence',
        '3': '1',
        '4': '2',
        '5': '3',
        '6': '4',
        '7': '5'
    },
    'f_dir' : {
        '0': 'off',
        '1': 'vertical',
        '2': 'horizontal',
        '3': '3d'
    },
    'en_hol' : {
        '0': 'off',
        '1': 'on'
    }
}

def daikin_to_human(dimension, value):
    if value in TRANSLATIONS[dimension].keys():
        return TRANSLATIONS[dimension][value]
    else:
        return "UNKNOWN (%s)" % value

def human_to_daikin(dimension, value):
    ivd = {v: k for k, v in TRANSLATIONS[dimension].items()}
    return ivd[value]

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

        if None == ip:
            # id is a common name, try discovery
            e = discovery.get_name(id)
            if None == e:
                raise ValueError("no device found for %s" % id)

            ip = e['ip']

        self.ip = ip

        self.values['ip'] = ip

        with requests.Session() as self.session:
            for resource in HTTP_RESOURCES:
                self.values.update(self.get_resource(resource))

    def get_resource(self, resource):
        r = self.session.get('http://%s/%s' % (self.ip, resource))

        return self.parse_response(r.text)

    def show_values(self, only_summary = False):
        if only_summary:
            keys = VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, v) = self.represent(key)
                print ("%18s: %s" % (k, v))

    def translate_mac(self, value):
        r = ""
        for b in range(0, len(value)):
            r += value[b]
            if 1 == (b % 2) and b < len(value) - 1:
                r += ":"

        return r

    def represent(self, key):
        # adapt the key
        if key in VALUES_TRANSLATION:
            k = VALUES_TRANSLATION[key]
        else:
            k = key

        # adapt the value
        v = self.values[key]

        if (key == 'mode'):
            if self.values['pow'] == '0':
                v = 'off'
            else:
                v = daikin_to_human(key, v)

        elif (key in TRANSLATIONS.keys()):
            v = daikin_to_human(key, v)
        elif key == 'mac':
            v = self.translate_mac(v)

        return (k, v)

    def set(self, settings):
        # start with current values
        current_val = self.get_resource('aircon/get_control_info')

        pow   = current_val['pow']
        mode  = current_val['mode']
        temp  = current_val['stemp']
        hum   = current_val['shum']
        # Apparently some models don't have f_rate
        if "f_rate" in current_val:
            fan   = current_val['f_rate']
        dir   = current_val['f_dir']
        hol   = self.values['en_hol']

        # update them with the ones requested
        if 'pow' in settings:
            pow = settings["pow"]

        if 'mode' in settings:
            # we are using an extra mode "off" to power off the unit
            if settings['mode'] == 'off':
                pow = '0'
            else:
                if hol != "0":
                    raise ValueError("device is in holiday mode")

                pow = '1'
                mode = human_to_daikin('mode', settings['mode'])

        if 'stemp' in settings:
            temp = settings['stemp']

        if 'shum' in settings:
            hum = settings['shum']

        if 'f_rate' in settings:
            fan = human_to_daikin('f_rate', settings['f_rate'])

        if 'f_dir' in settings:
            dir = human_to_daikin('f_dir', settings['f_dir'])

        if 'en_hol' in settings:
            hol = human_to_daikin('en_hol', settings['en_hol'])

        self.values['pow'] = pow
        self.values['mode'] = mode
        self.values['stemp'] = temp
        self.values['shum'] = hum
        self.values['en_hol'] = hol

        # Apparently some models don't have f_rate and f_dir
        if "fan" in locals():
            self.values['f_rate'] = fan
            self.values['f_dir'] = dir
            query_c = 'aircon/set_control_info?'
            query_c += ('pow=%s&mode=%s&stemp=%s&shum=%s&f_rate=%s&f_dir=%s' %
                    (pow, mode, temp, hum, fan, dir))

        query_c = 'aircon/set_control_info?'
        query_c += ('pow=%s&mode=%s&stemp=%s&shum=%s' %
               (pow, mode, temp, hum))

        query_h = 'common/set_holiday?'
        query_h += ('en_hol=%s' % hol)

        with requests.Session() as self.session:
            self.get_resource(query_h)
            if (hol == "0"):
                self.get_resource(query_c)

