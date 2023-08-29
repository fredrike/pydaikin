import unittest

from pydaikin.models.base import DaikinResponse


class TestReponseParser(unittest.TestCase):
    fixtures = [
        (
            "Base CSV",
            'ret=OK,type=aircon,reg=eu,dst=1',
            dict(
                ret="OK",
                type="aircon",
                reg="eu",
                dst="1",
            ),
        ),
        (
            "Good CSV",
            'ret=OK,type=aircon,ssid=NormalWifiName,reg=eu,dst=1',
            dict(ret="OK", type="aircon", reg="eu", dst="1", ssid="NormalWifiName"),
        ),
        (
            "Bad CSV",
            'ret=OK,type=aircon,ssid=Wifi,WithComma,reg=eu,dst=1',
            dict(ret="OK", type="aircon", reg="eu", dst="1", ssid="Wifi,WithComma"),
        ),
    ]

    def test_parse_response(self):
        for msg, body, values in self.fixtures:
            with self.subTest(msg, body=body, values=values):
                self.assertEqual(
                    DaikinResponse.responseparser({"_response": body}), values
                )
