# -*- coding: utf-8 -*-
"""
    entity
    ~~~~~~~~~~~~

    Models the base class for objects representing a Daikin HVAC appliance

    :copyright: (c) 2015 by Yari Adan.
    :license: BSD, see LICENSE for more details.
"""

import urllib

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

class Entity:
    def __init__(self):
        self.values = {}

    def __getitem__(self, name):
        if name in self.values:
            return self.values[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def parse_response(self, body):
        d = dict([ e.split('=') for e in body.split(',') ])

        if not 'ret' in d or d['ret'] != 'OK':
            raise ValueError("non-OK return on response")

        if 'name' in d:
            d['name'] = urllib.unquote(d['name'])

        return d

    def show_values(self, only_summary = False):
        if only_summary:
            keys = VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, v) = self.represent(key)
                print "%18s: %s" % (k, v)

    def translate_mode(self, value):
        if value == '2':
            r = 'DEHUMIDIFICATOR'
        elif value == '3':
            r = 'COLD'
        elif value == '4':
            r = 'HOT'
        elif value == '6':
            r = 'FAN'
        elif value == '0':
            r = 'AUTO'
        elif value == '1':
            r = 'AUTO'
        elif value == '7':
            r = 'AUTO'
        else:
            r = 'UNKNOWN'

        return r + " (%s)" % value

    def translate_power(self, value):
        if value == '0':
            r = "OFF"
        elif value == '1':
            r = "ON"
        else:
            r = "UNKNOWN"

        return r + " (%s)" % value

    def translate_fan_direction(self, value):
        if value == '0':
            r = "STOPPED"
        elif value == '1':
            r = "VERTICAL"
        elif value == '2':
            r = "HORIZONTAL"
        elif value == '3':
            r = "VERTICAL AND HORIZONTAL"
        else:
            r = "UNKNOWN"

        return r + " (%s)" % value

    def translate_fan_rate(self, value):
        if value == 'A':
            r = "AUTO"
        elif value == 'B':
            r = "SILENCE"
        elif value == '3':
            r = "1/5"
        elif value == '4':
            r = "2/5"
        elif value == '5':
            r = "3/5"
        elif value == '6':
            r = "4/5"
        elif value == '7':
            r = "5/5"
        else:
            r = "UNKNOWN"

        return r + " (%s)" % value

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
            v = self.translate_mode(v)
        elif key == 'pow':
            v = self.translate_power(v)
        elif key == 'f_rate':
            v = self.translate_fan_rate(v)
        elif key == 'f_dir':
            v = self.translate_fan_direction(v)
        elif key == 'mac':
            v = self.translate_mac(v)

        return (k, v)

