import unittest
from unittest.mock import MagicMock, patch

from pydaikin.discovery import Discovery


class MockSocket(MagicMock):
    def recvfrom(self, size: int):  # pylint: disable=unused-argument
        if self.call_count == 0:
            self.call_count += 1
            return (b"ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0", "192.168.1.1")
        else:
            raise TimeoutError


class TestDiscovery(unittest.IsolatedAsyncioTestCase):

    @patch("pydaikin.discovery.socket")
    def test_discovery(self, mock_socket):
        mocksock = MockSocket()
        mocksock.setsockopt.return_value = None
        mocksock.bind.return_value = None
        mocksock.settimeout.return_value = None
        mocksock.sendto.return_value = None

        mock_socket.socket.return_value = mocksock

        d = Discovery()
        found_devices = d.poll()

        self.assertEqual(len(found_devices), 1)
