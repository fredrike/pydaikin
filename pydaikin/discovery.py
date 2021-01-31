"""Pydaikin discovery, used for auto discovery of devices."""

import logging
import socket

from netifaces import (  # pylint: disable=no-name-in-module
    AF_INET,
    ifaddresses,
    interfaces,
)

_LOGGER = logging.getLogger(__name__)

UDP_SRC_PORT = 30000
UDP_DST_PORT = 30050
RCV_BUFSIZ = 1024

GRACE_SECONDS = 1

DISCOVERY_MSG = "DAIKIN_UDP/common/basic_info"


class DiscoveredObject:
    """Represents a discovered device."""

    def __init__(self, ip, port, basic_info_string):
        self.values = {}

        self.values['ip'] = ip
        self.values['port'] = port
        self.values.update(self.parse_basic_info(basic_info_string))

    @staticmethod
    def parse_basic_info(basic_info):
        """Parse basic info."""
        from pydaikin.daikin_base import (  # pylint: disable=import-outside-toplevel
            Appliance,
        )

        data = Appliance.parse_response(basic_info)

        if 'mac' not in data:
            raise ValueError("no mac found for device")

        return data

    def __getitem__(self, name):
        """Override getitem."""
        if name in self.values:
            return self.values[name]
        raise AttributeError("No such attribute: " + name)

    def keys(self):
        """Return keys."""
        return self.values.keys()

    def __str__(self):
        """Override str."""
        return str(self.values)


class Discovery:  # pylint: disable=too-few-public-methods
    """Main discovery class."""

    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", UDP_SRC_PORT))
        sock.settimeout(GRACE_SECONDS)

        self.sock = sock
        self.dev = {}

    def poll(self, stop_if_found=None, ip_address=None):
        """Poll discivered devices."""
        if ip_address:
            broadcast_ips = [ip_address]
        else:
            # get all IPv4 definitions in the system
            net_groups = [
                ifaddresses(i)[AF_INET]
                for i in interfaces()
                if AF_INET in ifaddresses(i)
            ]

            # flatten the previous list
            net_ips = [item for sublist in net_groups for item in sublist]

            # from those, get the broadcast IPs, if available
            broadcast_ips = [i['broadcast'] for i in net_ips if 'broadcast' in i.keys()]

        # send a daikin broadcast to each one of the ips
        for address in broadcast_ips:
            self.sock.sendto(bytes(DISCOVERY_MSG, 'UTF-8'), (address, UDP_DST_PORT))

        try:
            while True:  # for anyone who ansers
                data, addr = self.sock.recvfrom(RCV_BUFSIZ)
                _LOGGER.debug("Discovered %s, %s", addr, data.decode('UTF-8'))

                try:
                    data = DiscoveredObject(addr[0], addr[1], data.decode('UTF-8'))

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
    """Get information of discovered devices."""
    return Discovery().poll()


def get_name(name):
    """Get names of discovered devices."""
    devices = Discovery().poll(name)

    for device in devices:
        if device['name'].lower() == name.lower():
            return device
    return None
