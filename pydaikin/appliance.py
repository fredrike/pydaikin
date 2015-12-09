import entity
import discovery

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

    def power(self, state):
        if state:
            power = "1"
        else:
            power = "0"

        self.get_resource('aircon/set_control_info?pow=%s&mode=%s&stemp=%s&shum=%s&f_rate=%s&f_dir=%s' %
                          (power
                           , self.values['mode']
                           , self.values['stemp']
                           , self.values['shum']
                           , self.values['f_rate']
                           , self.values['f_dir']))

    def get_resource(self, resource):
        r = self.session.get('http://%s/%s' % (self.ip, resource))

        return self.parse_response(r.text)

