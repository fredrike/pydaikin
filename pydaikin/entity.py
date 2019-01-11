# -*- coding: utf-8 -*-
"""
    entity
    ~~~~~~~~~~~~

    Models the base class for objects representing a Daikin HVAC appliance

    :copyright: (c) 2015 by Yari Adan.
    :license: BSD, see LICENSE for more details.
"""

import urllib
import urllib.parse

class Entity:
    def __init__(self):
        self.values = {}

    def __getitem__(self, name):
        if name in self.values:
            return self.values[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def parse_response(self, body):
        d = dict([e.split('=') for e in body.split(',')])

        if 'ret' not in d:
            raise ValueError("missing 'ret' field in response")

        if d['ret'] != 'OK':
            return {}

        if 'name' in d:
            d['name'] = urllib.parse.unquote(d['name'])

        return d
