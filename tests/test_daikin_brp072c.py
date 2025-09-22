from unittest.mock import MagicMock

import pytest

from pydaikin.daikin_brp072c import DaikinBRP072C


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
    """Test the humidity property for DaikinBRP072C."""
    mock_session = MagicMock()
    device = DaikinBRP072C('127.0.0.1', session=mock_session, key='dummy_key')
    device.values.update(values)
    assert device.humidity == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'hhum': '50'}, True),
        ({'hhum': '25.5'}, True),
        ({'hhum': '-'}, False),
        ({'hhum': '--'}, False),
        ({}, False),
        ({'hhum': None}, False),
        ({'hhum': 'invalid'}, False),
    ],
)
def test_support_humidity(values, expected):
    """Test the support_humidity property for DaikinBRP072C."""
    mock_session = MagicMock()
    device = DaikinBRP072C('127.0.0.1', session=mock_session, key='dummy_key')
    device.values.update(values)
    assert device.support_humidity is expected
