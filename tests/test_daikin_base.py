from unittest.mock import MagicMock

import pytest

from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.response import parse_response


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
    assert parse_response(body) == values


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'hhum': '50'}, 50.0),
        ({'hhum': '25.5'}, 25.5),
        ({'hhum': '-'}, None),
        ({'hhum': '--'}, None),
        ({}, None),
        ({'hhum': None}, None),
        ({'hhum': 'invalid'}, None),
    ],
)
def test_humidity(values, expected):
    """Test the humidity property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.humidity == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'hhum': '50'}, True),  # humidity is supported
        ({'hhum': '25.5'}, True),  # humidity is supported (float value)
        ({'hhum': '-'}, False),  # humidity is not supported (non-numeric)
        ({'hhum': '--'}, False),  # humidity is not supported (non-numeric)
        ({}, False),  # 'hhum' key not present
        ({'hhum': None}, False),  # value is None
        ({'hhum': 'invalid'}, False),  # ValueError on float conversion
    ],
)
def test_support_humidity(values, expected):
    """Test the support_humidity property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_humidity is expected
