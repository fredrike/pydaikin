import entity

class UdpEntity(entity.Entity):
    def __init__(self, ip, port, basic_info_string):
        entity.Entity.__init__(self)

        self.values['ip']   = ip
        self.values['port'] = port
        self.values.update(self.parse_basic_info(basic_info_string))

    def parse_basic_info(self, basic_info):
        d = self.parse_response(basic_info)

        if 'mac' not in d:
            raise ValueError("no mac found for device")

        return d

    def __getitem__(self, name):
        if name in self.values:
            return self.values[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def keys(self):
        return self.values.keys()

    def __str__(self):
        return str(self.values)
