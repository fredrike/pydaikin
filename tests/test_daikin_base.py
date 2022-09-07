import pytest

from pydaikin.daikin_base import Appliance


@pytest.mark.parametrize(
    'body,values',
    [
        (
            'ret=KO,type=aircon,reg=eu,dst=1',
            dict(),
        ),
        (
            'ret=OK,type=aircon,reg=eu,dst=1,ver=1_14_68,rev=C3FF8A6,pow=1',
            dict(
                ret='OK',
                type='aircon',
                reg='eu',
                dst='1',
                ver='1_14_68',
                rev='C3FF8A6',
                pow='1',
            ),
        ),
        (
            'ret=OK,ssid1=Loading 2,4G...,radio1=-33,ssid=DaikinAP47108,grp_name=,en_grp=0',
            dict(
                ret='OK',
                ssid1='Loading 2,4G...',
                radio1='-33',
                ssid='DaikinAP47108',
                grp_name='',
                en_grp='0',
            ),
        ),
        (
            'ret=OK,ssid1=Loadi=ng 2,4G...,radio1=-33,ssid=DaikinAP47108,grp_name=,en_grp=0',
            dict(
                ret='OK',
                Loadi='ng 2,4G...',
                radio1='-33',
                ssid='DaikinAP47108',
                grp_name='',
                en_grp='0',
            ),
        ),
    ],
)
def test_parse_response(body: str, values: dict):
    assert Appliance.parse_response(body) == values
