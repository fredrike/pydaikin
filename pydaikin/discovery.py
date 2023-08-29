"""Discovery module to autodiscover Daikin devices on local network."""

import logging
import socket
from typing import List

import netifaces

from .models.base import CommonBasicInfo

_LOGGER = logging.getLogger(__name__)

UDP_SRC_PORT = 30000
UDP_DST_PORT = 30050
RCV_BUFSIZ = 1024

GRACE_SECONDS = 1

DISCOVERY_MSG = "DAIKIN_UDP/common/basic_info"


class DiscoveredObject(CommonBasicInfo):
    "Proto-Appliance with just basic data"
    ip_addr: str
    port: str


class Discovery:  # pylint: disable=too-few-public-methods
    """Discovery class."""

    def __init__(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", UDP_SRC_PORT))
        sock.settimeout(GRACE_SECONDS)

        self.sock = sock

    def poll(
        self, stop_if_found=None, ip_addr=None
    ) -> List[DiscoveredObject]:  # pylint: disable=invalid-name
        """Poll for available devices."""

        self.find_with_broadcast_probe(ip_addr)

        found_devices = []

        try:
            while True:  # for anyone who ansers
                data, addr = self.sock.recvfrom(RCV_BUFSIZ)
                _LOGGER.debug("Discovered %s, %s", addr, data.decode('UTF-8'))

                try:
                    data = DiscoveredObject(
                        _response=data.decode('UTF-8'), ip_addr=addr[0], port=addr[1]
                    )

                    if (
                        stop_if_found is not None
                        and data.name.lower() == stop_if_found.lower()
                    ):
                        return [
                            data,
                        ]

                    found_devices.append(data)

                except ValueError:  # invalid message received
                    continue

        except TimeoutError:  # nobody else is answering
            pass

        return found_devices

    def find_with_broadcast_probe(self, ip_addr):
        "Send an UDP broadcast probe on all local interfaces for Daikin controllers"
        if ip_addr:
            broadcast_ips = [ip_addr]
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


def get_name(name: str) -> DiscoveredObject:
    """Returns the name of discovered devices."""
    discovery = Discovery()

    devices = discovery.poll(name)

    ret = None

    for device in devices:
        if device.name.lower() == name.lower():
            ret = device

    return ret
