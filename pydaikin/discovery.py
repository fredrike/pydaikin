import socket
import udpentity

UDP_DST_IP   = "192.168.10.255"
UDP_SRC_PORT = 30000
UDP_DST_PORT = 30050
RCV_BUFSIZ   = 1024

GRACE_SECONDS = 1

DISCOVERY_MSG="DAIKIN_UDP/common/basic_info"

class Discovery():
    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", UDP_SRC_PORT))
        sock.settimeout(GRACE_SECONDS)

        self.sock = sock
        self.dev  = {}

    def poll(self, stop_if_found = None):
        self.sock.sendto(DISCOVERY_MSG, (UDP_DST_IP, UDP_DST_PORT))

        try:
            while True: # for anyone who ansers
                data, addr = self.sock.recvfrom(RCV_BUFSIZ)

                try:
                    d = udpentity.UdpEntity(addr[0], addr[1], data)

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

