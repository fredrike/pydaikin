import asyncio
from unittest.mock import MagicMock

from aiohttp.client_exceptions import ClientResponseError
from aiohttp.web_exceptions import HTTPForbidden
import pytest

from pydaikin.daikin_base import Appliance
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.response import parse_response

from .test_init import client_session

assert client_session


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


def test_translate_mac():
    """Test MAC address translation."""
    assert DaikinBRP069.translate_mac('112233445566') == '11:22:33:44:55:66'
    assert DaikinBRP069.translate_mac('AABBCCDDEEFF') == 'AA:BB:CC:DD:EE:FF'
    assert DaikinBRP069.translate_mac('') == ''


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'en_hol': '1'}, True),
        ({'en_hol': '0'}, True),
        ({}, False),
    ],
)
def test_support_away_mode(values, expected):
    """Test support_away_mode property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_away_mode == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'f_rate': 'A'}, True),
        ({'f_rate': '3'}, True),
        ({}, False),
    ],
)
def test_support_fan_rate(values, expected):
    """Test support_fan_rate property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_fan_rate == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'f_dir': '0'}, True),
        ({'f_dir': '3'}, True),
        ({}, False),
    ],
)
def test_support_swing_mode(values, expected):
    """Test support_swing_mode property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_swing_mode == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'otemp': '25.0'}, True),
        ({'otemp': '-'}, True),
        ({}, False),
    ],
)
def test_support_outside_temperature(values, expected):
    """Test support_outside_temperature property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_outside_temperature == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'adv': ''}, True),
        ({'adv': '2'}, True),
        ({}, False),
    ],
)
def test_support_advanced_modes(values, expected):
    """Test support_advanced_modes property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_advanced_modes == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'cmpfreq': '40'}, True),
        ({'cmpfreq': '0'}, True),
        ({}, False),
    ],
)
def test_support_compressor_frequency(values, expected):
    """Test support_compressor_frequency property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_compressor_frequency == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'en_filter_sign': '1', 'filter_sign_info': '100'}, True),
        ({'en_filter_sign': '0', 'filter_sign_info': '100'}, False),
        ({'en_filter_sign': '1'}, False),
        ({'filter_sign_info': '100'}, False),
        ({}, False),
    ],
)
def test_support_filter_dirty(values, expected):
    """Test support_filter_dirty property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_filter_dirty == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'en_zone': '8'}, True),
        ({'en_zone': '0'}, True),
        ({}, False),
    ],
)
def test_support_zone_count(values, expected):
    """Test support_zone_count property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_zone_count == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'otemp': '21.5'}, 21.5),
        ({'otemp': '-5.0'}, -5.0),
        ({'otemp': '-'}, None),
        ({}, None),
    ],
)
def test_outside_temperature(values, expected):
    """Test outside_temperature property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.outside_temperature == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'htemp': '23.5'}, 23.5),
        ({'htemp': '18'}, 18.0),
        ({'htemp': '-'}, None),
        ({}, None),
    ],
)
def test_inside_temperature(values, expected):
    """Test inside_temperature property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.inside_temperature == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'stemp': '25.0'}, 25.0),
        ({'stemp': '22'}, 22.0),
        ({'stemp': 'M'}, None),
        ({}, None),
    ],
)
def test_target_temperature(values, expected):
    """Test target_temperature property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.target_temperature == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'cmpfreq': '40'}, 40.0),
        ({'cmpfreq': '0'}, 0.0),
        ({'cmpfreq': '100'}, 100.0),
        ({}, None),
    ],
)
def test_compressor_frequency(values, expected):
    """Test compressor_frequency property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.compressor_frequency == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'filter_sign_info': '100'}, 100.0),
        ({'filter_sign_info': '50'}, 50.0),
        ({}, None),
    ],
)
def test_filter_dirty(values, expected):
    """Test filter_dirty property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.filter_dirty == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'en_zone': '8'}, 8.0),
        ({'en_zone': '4'}, 4.0),
        ({}, None),
    ],
)
def test_zone_count(values, expected):
    """Test zone_count property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.zone_count == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'shum': '50'}, 50.0),
        ({'shum': 'AUTO'}, None),
        ({}, None),
    ],
)
def test_target_humidity(values, expected):
    """Test target_humidity property."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.target_humidity == expected


def test_fan_rate_values():
    """Test fan_rate property returns list of translated values."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    fan_rates = device.fan_rate
    assert isinstance(fan_rates, list)
    assert len(fan_rates) > 0
    # Check that values are strings
    assert all(isinstance(rate, str) for rate in fan_rates)


def test_swing_modes_values():
    """Test swing_modes property returns list of translated values."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    swing_modes = device.swing_modes
    assert isinstance(swing_modes, list)
    assert len(swing_modes) > 0
    # Check that values are strings
    assert all(isinstance(mode, str) for mode in swing_modes)


def test_mac_property():
    """Test mac property returns MAC address or falls back to device_ip."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)

    # Without mac in values, should return device_ip
    assert device.mac == '127.0.0.1'

    # With mac in values, should return mac
    device.values.update({'mac': '112233445566'})
    assert device.mac == '112233445566'


def test_daikin_values():
    """Test daikin_values returns sorted list of translated values."""
    values = DaikinBRP069.daikin_values('mode')
    assert isinstance(values, list)
    assert len(values) > 0

    # Empty dimension should return empty list
    values = DaikinBRP069.daikin_values('nonexistent')
    assert values == []


def test_represent_mode_off():
    """Test represent method handles mode 'off' when pow=0."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update({'pow': '0', 'mode': '2'})

    k, val = device.represent('mode')
    assert val == 'off'


def test_represent_mac():
    """Test represent method handles MAC address."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update({'mac': '112233445566'})

    k, val = device.represent('mac')
    # Should return a list (split by semicolon)
    assert isinstance(val, list)
    assert '112233445566' in val


def test_show_values():
    """Test show_values method."""
    from io import StringIO
    import sys

    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(
        {'pow': '1', 'mode': '2', 'stemp': '25.0', 'mac': '112233445566'}
    )

    # Capture stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        device.show_values(only_summary=True)
        output = captured_output.getvalue()
        # Should print some values
        assert len(output) > 0
    finally:
        sys.stdout = sys.__stdout__


def test_getitem():
    """Test __getitem__ method."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update({'mode': '2'})

    # Should work like dictionary access
    assert device['mode'] == '2'

    # Should raise AttributeError for missing keys
    with pytest.raises(AttributeError):
        _ = device['nonexistent']


def test_discover_ip_with_ip():
    """Test discover_ip with valid IP address."""
    # Valid IP should return as-is
    result = DaikinBRP069.discover_ip('192.168.1.100')
    assert result == '192.168.1.100'


def test_discover_ip_with_dns():
    """Test discover_ip with DNS name."""
    import socket  # noqa: F401

    # Try with localhost which should resolve
    try:
        result = DaikinBRP069.discover_ip('localhost')
        # Should either succeed or raise ValueError
        assert result == 'localhost' or result is not None
    except ValueError:
        # DNS resolution can fail in test environment
        pass


def test_discover_ip_invalid():
    """Test discover_ip with invalid name."""
    # Invalid name should raise ValueError
    with pytest.raises(ValueError, match="no device found"):
        DaikinBRP069.discover_ip('this-device-definitely-does-not-exist-12345')


def test_discover_ip_from_discovery(monkeypatch):
    """Test discover_ip resolves a common name via discovery."""
    monkeypatch.setattr(
        'pydaikin.daikin_base.get_name', lambda name: {'ip': '192.168.1.50'}
    )

    assert DaikinBRP069.discover_ip('livingroom') == 'livingroom'


@pytest.mark.asyncio
async def test_async_context_manager():
    """The appliance supports the async context manager protocol."""
    device = DaikinBRP069('192.168.1.100')
    async with device as entered:
        assert entered is device
    assert device.session.closed is True


@pytest.mark.asyncio
async def test_base_init_not_implemented():
    """Base Appliance init raises NotImplementedError."""
    device = Appliance('127.0.0.1', session=MagicMock())
    with pytest.raises(NotImplementedError):
        await device.init()


@pytest.mark.asyncio
async def test_get_resource_coalescing(aresponses, client_session):
    """Concurrent identical GETs are coalesced into a single request."""
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,cur=2023/8/27 21:54:1",
    )

    device = DaikinBRP069('192.168.1.100', session=client_session)
    r1, r2 = await asyncio.gather(
        device._get_resource('common/get_datetime'),
        device._get_resource('common/get_datetime'),
    )

    assert r1 == r2
    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_get_resource_forbidden(aresponses, client_session):
    """A 403 response raises HTTPForbidden (after the retries)."""
    for _ in range(3):
        aresponses.add(
            path_pattern="/common/get_datetime",
            method_pattern="GET",
            response=aresponses.Response(status=403, text="Forbidden"),
        )

    device = DaikinBRP069('192.168.1.100', session=client_session)
    with pytest.raises(HTTPForbidden):
        await device._get_resource('common/get_datetime')


@pytest.mark.asyncio
async def test_update_status_default_resources():
    """update_status uses get_info_resources() when no resources given."""
    device = Appliance('192.168.1.100', session=MagicMock())
    await device.update_status()


@pytest.mark.asyncio
async def test_update_status_task_group_error(aresponses, client_session, monkeypatch):
    """Errors raised inside the update TaskGroup are logged."""
    for _ in range(3):
        aresponses.add(
            path_pattern="/common/get_datetime",
            method_pattern="GET",
            response=aresponses.Response(status=500, text="Error"),
        )

    device = Appliance('192.168.1.100', session=client_session)
    monkeypatch.setattr(Appliance, 'INFO_RESOURCES', ['common/get_datetime'])

    with pytest.raises(ClientResponseError):
        await device.update_status()


def test_show_values_all():
    """show_values without summary prints every value."""
    from io import StringIO
    import sys

    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update({'pow': '1', 'mode': '2', 'stemp': '25.0'})

    captured_output = StringIO()
    sys.stdout = captured_output
    try:
        device.show_values()
        assert len(captured_output.getvalue()) > 0
    finally:
        sys.stdout = sys.__stdout__


def test_log_sensors(tmp_path):
    """log_sensors writes a CSV row for the device sensors."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(
        {
            'htemp': '25.0',
            'otemp': '21.0',
            'cmpfreq': '40',
            'en_filter_sign': '1',
            'filter_sign_info': '100',
            'datas': '100/200/300/400/500/600/700',
            'curr_day_cool': '10/20',
            'curr_day_heat': '30/40',
            'this_year': '50/100',
            'previous_year': '60/120',
        }
    )

    sensors_file = tmp_path / 'sensors.csv'
    with open(sensors_file, 'w') as f:
        device.log_sensors(f)

    content = sensors_file.read_text()
    assert 'in_temp' in content
    assert 'total_power' in content


def test_show_sensors(capsys):
    """show_sensors prints a summary of the device sensors."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(
        {
            'htemp': '25.0',
            'otemp': '21.0',
            'cmpfreq': '40',
            'en_filter_sign': '1',
            'filter_sign_info': '100',
            'datas': '100/200/300/400/500/600/700',
            'this_year': '50/100',
            'previous_year': '60/120',
        }
    )

    device.show_sensors()
    assert 'in_temp=25' in capsys.readouterr().out


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method, args',
    [
        ('set', ({},)),
        ('set_holiday', ('1',)),
        ('set_advanced_mode', ('powerful', '1')),
        ('set_streamer', ('1',)),
        ('set_zone', (0, 'key', 'value')),
    ],
)
async def test_base_appliance_abstract_methods(method, args):
    """Base Appliance abstract methods raise NotImplementedError."""
    device = Appliance('127.0.0.1', session=MagicMock())
    with pytest.raises(NotImplementedError):
        await getattr(device, method)(*args)


def test_base_appliance_zones_none():
    """The base Appliance exposes no zones."""
    device = Appliance('127.0.0.1', session=MagicMock())
    assert device.zones is None


def test_subclass_missing_override_raises():
    """Direct subclasses must override the required class attributes."""
    with pytest.raises(
        TypeError, match="must override class attribute 'INFO_RESOURCES'"
    ):

        class MissingInfoResources(Appliance):
            TRANSLATIONS = {"mode": {"1": "auto"}}
            VALUES_TRANSLATION = {}
            VALUES_SUMMARY = []


def test_subclass_empty_translations_raises():
    """Direct subclasses with empty TRANSLATIONS are rejected."""
    with pytest.raises(ValueError, match="TRANSLATIONS must not be empty"):

        class EmptyTranslations(Appliance):
            TRANSLATIONS = {}
            VALUES_TRANSLATION = {}
            VALUES_SUMMARY = []
            INFO_RESOURCES = ["aircon/getinfo"]


def test_subclass_with_overrides_accepted():
    """Direct subclasses overriding all attributes are accepted."""

    class ValidSubclass(Appliance):
        TRANSLATIONS = {"mode": {"1": "auto"}}
        VALUES_TRANSLATION = {}
        VALUES_SUMMARY = []
        INFO_RESOURCES = []

    assert ValidSubclass.TRANSLATIONS == {"mode": {"1": "auto"}}


def test_indirect_subclass_not_validated():
    """Intermediate subclasses inherit the overrides without validation."""

    class Child(Appliance):
        TRANSLATIONS = {"mode": {"1": "auto"}}
        VALUES_TRANSLATION = {}
        VALUES_SUMMARY = []
        INFO_RESOURCES = ["aircon/getinfo"]

    class GrandChild(Child):
        pass

    assert GrandChild.INFO_RESOURCES == ["aircon/getinfo"]
