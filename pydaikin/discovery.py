import pydaikin.entity as entity

import socket
import netifaces

UDP_SRC_PORT = 30000
UDP_DST_PORT = 30050
RCV_BUFSIZ   = 1024

GRACE_SECONDS = 1

DISCOVERY_MSG="DAIKIN_UDP/common/basic_info"

class DiscoveredObject(entity.Entity):
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

class Discovery():
    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", UDP_SRC_PORT))
        sock.settimeout(GRACE_SECONDS)

        self.sock = sock
        self.dev  = {}

    def poll(self, stop_if_found = None):
        # get all IPv4 definitions in the system
        net_groups = [ netifaces.ifaddresses(i)[netifaces.AF_INET] for
                       i in netifaces.interfaces() if
                       netifaces.AF_INET in netifaces.ifaddresses(i) ]

        # flatten the previous list
        net_ips = [ item for sublist in net_groups for item in sublist ]

        # from those, get the broadcast IPs, if available
        broadcast_ips = [ i['broadcast'] for i in net_ips if
                          'broadcast' in i.keys() ]

        # send a daikin broadcast to each one of the ips
        for ip in broadcast_ips:
            self.sock.sendto(DISCOVERY_MSG.encode(), (ip, UDP_DST_PORT))

        try:
            while True: # for anyone who ansers
                data, addr = self.sock.recvfrom(RCV_BUFSIZ)

                try:
                    d = DiscoveredObject(addr[0], addr[1], data.decode())

                    new_mac = d['mac']
                    self.dev[new_mac] = d

                    if (None != stop_if_found and
                        d['name'].lower() == stop_if_found.lower()):
                        return self.dev.values()

                except ValueError: # invalid message received
                    continue

        except socket.timeout: # nobody else is answering
            pass

        return self.dev.values()


def get_devices():
    d = Discovery()

    return d.poll()

def get_name(name):
    d = Discovery()

    devs = d.poll(name)

    ret = None

    for dev in devs:

        if dev['name'].lower() == name.lower():
            ret = dev

    return ret

