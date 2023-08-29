import unittest
from unittest.mock import MagicMock, patch

from pydaikin.discovery import DiscoveredObject, Discovery, get_name


class MockSocket(MagicMock):
    def recvfrom(self, size: int):  # pylint: disable=unused-argument
        self.call_count += 1
        if self.call_count == 1:
            return (b"ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0", "192.168.1.1")
        elif self.call_count == 2:
            return (b"ret=OK,type=aircon,reg=th,adp_kind=4,ver=1_19_0,rev=17330723,pv=3.40,cpv=3,cpv_minor=40,pow=0,err=0,location=0,name=%44%61%69%6b%69%6e%41%50%39%36%31%36%32,icon=0,instform=0,method=home only,port=0,id=,pw=,lpw_flag=0,led=1,dst=1,en_setzone=1,mac=9C50D1BD7812,ssid=DaikinAP96162,adp_mode=ap_run,grp_name=,en_grp=0,en_hol=0,edid=0000000003708558,sw_id=1900292A", "192.168.1.2")
        else:
            raise TimeoutError


class TestDiscovery(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.mocksock = MockSocket()
        self.mocksock.setsockopt.return_value = None
        self.mocksock.bind.return_value = None
        self.mocksock.settimeout.return_value = None
        self.mocksock.sendto.return_value = None

    @patch("pydaikin.discovery.socket")
    def test_discovery(self, mock_socket):
        mock_socket.socket.return_value = self.mocksock

        d = Discovery()
        found_devices = d.poll()

        self.assertEqual(len(found_devices), 2)

    @patch("pydaikin.discovery.socket")
    def test_find_device(self, mock_socket):
        mock_socket.socket.return_value = self.mocksock

        found_devices = get_name("Notte")
        self.assertIsInstance(found_devices, DiscoveredObject)
