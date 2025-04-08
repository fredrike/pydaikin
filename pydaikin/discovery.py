"""Discovery module to autodiscover Daikin devices on local network."""

import logging
import socket

import netifaces

from .response import parse_response

_LOGGER = logging.getLogger(__name__)

UDP_SRC_PORT = 30000
UDP_DST_PORT = 30050
RCV_BUFSIZ = 1024

GRACE_SECONDS = 1

DISCOVERY_MSG = "DAIKIN_UDP/common/basic_info"


class Discovery:  # pylint: disable=too-few-public-methods
    """Discovery class."""

    def __init__(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", UDP_SRC_PORT))
        sock.settimeout(GRACE_SECONDS)

        self.sock = sock
        self.dev = {}

    def poll(self, stop_if_found=None, ip=None):  # pylint: disable=invalid-name
        """Poll for available devices."""
        if ip:
            broadcast_ips = [ip]
        else:
            # get all IPv4 definitions in the system
            net_groups = [
                netifaces.ifaddresses(i)[netifaces.AF_INET]
                for i in netifaces.interfaces()
                if netifaces.AF_INET in netifaces.ifaddresses(i)
            ]

            # flatten the previous list
            net_ips = [item for sublist in net_groups for item in sublist]

            # from those, get the broadcast IPs, if available
            broadcast_ips = [i['broadcast'] for i in net_ips if 'broadcast' in i.keys()]

        # send a daikin broadcast to each one of the ips
        for ip_address in broadcast_ips:
            self.sock.sendto(bytes(DISCOVERY_MSG, 'UTF-8'), (ip_address, UDP_DST_PORT))

        try:
            while True:  # for anyone who ansers
                data, addr = self.sock.recvfrom(RCV_BUFSIZ)
                _LOGGER.debug("Discovered %s, %s", addr, data.decode('UTF-8'))

                try:
                    data = parse_response(data.decode('UTF-8'))

                    if 'mac' not in data:
                        raise ValueError("no mac found for device")

                    data.update(
                        {
                            "ip": addr[0],
                            "port": addr[1],
                        }
                    )

                    new_mac = data['mac']
                    self.dev[new_mac] = data

                    if (
                        stop_if_found is not None
                        and data['name'].lower() == stop_if_found.lower()
                    ):
                        return self.dev.values()

                except ValueError:  # invalid message received
                    continue

        except socket.timeout:  # nobody else is answering
            pass

        return self.dev.values()


def get_devices():
    """Returns discovered devices."""
    discovery = Discovery()

    return discovery.poll()


def get_name(name):
    """Returns the name of discovered devices."""
    discovery = Discovery()

    devices = discovery.poll(name)

    ret = None

    for device in devices:
        if device['name'].lower() == name.lower():
            ret = device

    return ret
