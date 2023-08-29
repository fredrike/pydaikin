import pytest

from pydaikin.models.base import DaikinResponse


@pytest.mark.parametrize(
    'body,values',
    [
        (
            'ret=OK,type=aircon,reg=eu,dst=1',
            dict(
                ret="OK",
                type="aircon",
                reg="eu",
                dst="1",
            ),
        ),
        (
            'ret=OK,type=aircon,ssid=NormalWifiName,reg=eu,dst=1',
            dict(ret="OK", type="aircon", reg="eu", dst="1", ssid="NormalWifiName"),
        ),
        (
            'ret=OK,type=aircon,ssid=Wifi,WithComma,reg=eu,dst=1',
            dict(ret="OK", type="aircon", reg="eu", dst="1", ssid="Wifi,WithComma"),
        ),
    ],
)
def test_parse_response(body: str, values: dict):
    assert DaikinResponse.responseparser({"_response": body}) == values
