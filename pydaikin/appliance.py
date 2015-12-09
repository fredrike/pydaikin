import pydaikin.entity as entity
import pydaikin.discovery as discovery

import socket
import requests

HTTP_RESOURCES = ['common/basic_info'
                  , 'common/get_remote_method'
                  , 'aircon/get_sensor_info'
                  , 'aircon/get_model_info'
                  , 'aircon/get_control_info'
                  , 'aircon/get_timer'
                  , 'aircon/get_target'
                  , 'aircon/get_price'
                  , 'aircon/get_program'
                  , 'common/get_notify'
                  , 'aircon/get_week_power'
                  , 'aircon/get_year_power'
                  , 'aircon/get_scdltimer'
              ]

VALUES_SUMMARY = ['name', 'ip', 'mac', 'pow', 'mode', 'f_rate', 'f_dir'
                  , 'htemp', 'otemp', 'stemp'
                  , 'cmpfreq', 'err']

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
}

TRANSLATIONS = {
    'mode' : {
        '2': 'dehumidificator',
        '3': 'cold',
        '4': 'hot',
        '6': 'fan',
        '0': 'auto',
        '1': 'auto-1',
        '7': 'auto-7'
    },
    'power' : {
        '0': 'off',
        '1': 'on'
    },
    'fan' : {
        'A': 'auto',
        'B': 'silence',
        '3': '1',
        '4': '2',
        '5': '3',
        '6': '4',
        '7': '5'
    },
    'direction' : {
        '0': "stopped",
        '1': "vertical",
        '2': "horizontal",
        '3': "all"
    }
}

def daikin_to_human(dimension, value):
    if value in TRANSLATIONS[dimension].keys():
        return TRANSLATIONS[dimension][value].upper()
    else:
        return "UNKNOWN (%s)" % value

def human_to_daikin(dimension, value):
    ivd = {v: k for k, v in TRANSLATIONS[dimension].items()}
    return ivd[value]

def daikin_values(dimension):
    return TRANSLATIONS[dimension].values()

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

        self.session = requests.Session()

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
                print("%18s: %s" % (k, v))


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

        if key == 'mode':
            v = daikin_to_human('mode', v)
        elif key == 'pow':
            v = daikin_to_human('power', v)
        elif key == 'f_rate':
            v = daikin_to_human('fan', v)
        elif key == 'f_dir':
            v = daikin_to_human('direction', v)
        elif key == 'mac':
            v = self.translate_mac(v)

        return (k, v)

    def set(self, settings):
        # start with current values
        pow   = self.values['pow']
        mode  = self.values['mode']
        temp  = self.values['stemp']
        hum   = self.values['shum']
        fan   = self.values['f_rate']
        dir   = self.values['f_dir']

        # update them with the ones requested
        if 'power' in settings:
            pow = human_to_daikin('power', settings['power'])

        if 'mode' in settings:
            mode = human_to_daikin('mode', settings['mode'])

        if 'temp' in settings:
            temp = settings['temp']

        if 'humidity' in settings:
            hum = settings['humidity']

        if 'fan' in settings:
            fan = human_to_daikin('fan', settings['fan'])

        if 'direction' in settings:
            dir = human_to_daikin('direction', settings['direction'])

        self.get_resource('aircon/set_control_info?pow=%s&mode=%s&stemp=%s&shum=%s&f_rate=%s&f_dir=%s' %
                          (pow, mode, temp, hum, fan, dir))

