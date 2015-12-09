# -*- coding: utf-8 -*-
"""
    entity
    ~~~~~~~~~~~~

    Models the base class for objects representing a Daikin HVAC appliance

    :copyright: (c) 2015 by Yari Adan.
    :license: BSD, see LICENSE for more details.
"""

import urllib

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

