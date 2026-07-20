"""Verify that init() calls the expected set of endpoints for firmware 2.8.0 devices."""

import json
from unittest.mock import AsyncMock, MagicMock

from aiohttp import ClientSession
import pytest
import pytest_asyncio

from pydaikin.daikin_brp084 import DaikinBRP084


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.asyncio
async def test_daikin_brp084(aresponses, client_session):
    """Test the DaikinBRP084 class for firmware 2.8.0 devices."""
    # Mock response for initial status update
    mock_response = {
        "responses": [
            {
                "fr": "/dsiot/edge/adr_0100.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1002",
                            "pch": [
                                {"pn": "e_A002", "pch": [{"pn": "p_01", "pv": "01"}]},
                                {
                                    "pn": "e_3001",
                                    "pch": [
                                        {"pn": "p_01", "pv": "0200"},  # Mode (COOL)
                                        {"pn": "p_02", "pv": "32"},  # Cool temp (25°C)
                                        {
                                            "pn": "p_09",
                                            "pv": "0A00",
                                        },  # Cool fan speed (AUTO)
                                        {
                                            "pn": "p_05",
                                            "pv": "000000",
                                        },  # Vertical swing OFF
                                        {
                                            "pn": "p_06",
                                            "pv": "000000",
                                        },  # Horizontal swing OFF
                                    ],
                                },
                                {
                                    "pn": "e_A00B",
                                    "pch": [
                                        {"pn": "p_01", "pv": "18"},  # Room temp (24°C)
                                        {"pn": "p_02", "pv": "3c"},  # Humidity (60%)
                                    ],
                                },
                                {
                                    "pn": "e_3003",
                                    "pch": [
                                        {"pn": "p_1D", "pv": "00"},  # Comfort OFF
                                        {"pn": "p_24", "pv": "00"},  # Econo OFF
                                    ],
                                },
                                {
                                    "pn": "e_A001",
                                    # Model "AMVA17MXTF" (hex ASCII, space-padded)
                                    "pch": [
                                        {
                                            "pn": "p_01",
                                            "pv": "2020202020414D564131374D585446",
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0200.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1003",
                            "pch": [
                                {
                                    "pn": "e_A00D",
                                    "pch": [
                                        {"pn": "p_01", "pv": "2200"}
                                    ],  # Outside temp, LE 2-byte (17°C)
                                },
                                {
                                    "pn": "e_A005",
                                    "pch": [
                                        {
                                            "pn": "p_01",
                                            "pv": "8C0000",
                                        },  # Compressor 70°C
                                        {"pn": "p_02", "pv": "410000"},
                                    ],
                                },
                                {
                                    "pn": "e_A001",
                                    "pch": [
                                        {
                                            "pn": "p_01",
                                            "pv": "2020202020414D564131374D5852",
                                        },  # Model "AMVA17MXR"
                                    ],
                                },
                                {
                                    "pn": "e_3002",
                                    "pch": [
                                        {"pn": "p_3D", "pv": "00"},  # Quiet OFF
                                        {"pn": "p_44", "pv": "00"},  # Powerful OFF
                                    ],
                                },
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {
                    "pn": "week_power",
                    "pch": [
                        {"pn": "today_runtime", "pv": "120"},
                        {"pn": "datas", "pv": [100, 200, 300, 400, 500, 600, 700]},
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {
                    "pn": "adp_i",
                    "pch": [
                        {"pn": "mac", "pv": "112233445566"},
                        {"pn": "ver", "pv": "3_12_3"},
                        {"pn": "api_ver", "pv": "2_2"},
                        {
                            "pn": "func",
                            "pch": [{"pn": "en_ipw_sep", "pv": 0}],
                        },
                    ],
                },
                "rsc": 2000,
            },
        ]
    }

    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(mock_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    # Mock response for setting temperature
    temp_update_response = {
        "responses": [{"fr": "/dsiot/edge/adr_0100.dgc_status", "rsc": 2004}]
    }

    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(temp_update_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    # Add another mock for the status update after setting
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(mock_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    device = DaikinBRP084('ip', session=client_session)
    await device.init()

    # Check basic properties
    assert device.values.get('mode') == 'cool'
    assert device.values.get('pow') == '1'
    assert device.values.get('stemp') == '25.0'
    assert device.values.get('f_rate') == 'auto'
    assert device.values.get('htemp') == '24.0'
    assert device.values.get('otemp') == '17.0'
    assert device.values.get('f_dir') == 'off'
    assert device.values.get('mac') == '112233445566'

    # New reads: comfort airflow, capabilities, outdoor sensors, models
    assert device.values.get('comfort') == 'off'
    assert device.support_comfort_mode is True
    assert device.comfort_mode == 'off'
    assert device.values.get('ver') == '3_12_3'
    assert device.firmware_version == '3_12_3'
    assert device.values.get('api_ver') == '2_2'
    assert device.outside_temperature == 17.0  # LE 2-byte decode
    assert device.compressor_temperature == 70.0
    assert device.support_compressor_temperature is True
    assert device.model == 'AMVA17MXTF'
    assert device.outdoor_model == 'AMVA17MXR'

    # New feature toggles: comfort/econo/outdoor_quiet/powerful
    assert device.comfort_mode == 'off' and device.support_comfort_mode
    assert device.econo_mode == 'off' and device.support_econo_mode
    assert device.outdoor_quiet_mode == 'off' and device.support_outdoor_quiet_mode
    assert device.powerful_mode == 'off' and device.support_powerful_mode

    # Test setting temperature
    await device.set({'stemp': '26.0'})

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_add_request_method(aresponses, client_session):
    """Test the add_request helper method."""
    # Mock response for initial status update - include all required fields
    mock_response = {
        "responses": [
            {
                "fr": "/dsiot/edge/adr_0100.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1002",
                            "pch": [
                                {"pn": "e_A002", "pch": [{"pn": "p_01", "pv": "01"}]},
                                {
                                    "pn": "e_3001",
                                    "pch": [
                                        {"pn": "p_01", "pv": "0200"},  # Mode (COOL)
                                        {"pn": "p_02", "pv": "32"},  # Cool temp (25°C)
                                        {
                                            "pn": "p_09",
                                            "pv": "0A00",
                                        },  # Cool fan speed (AUTO)
                                        {
                                            "pn": "p_05",
                                            "pv": "000000",
                                        },  # Vertical swing OFF
                                        {
                                            "pn": "p_06",
                                            "pv": "000000",
                                        },  # Horizontal swing OFF
                                    ],
                                },
                                {
                                    "pn": "e_A00B",
                                    "pch": [
                                        {"pn": "p_01", "pv": "18"},  # Room temp (24°C)
                                        {"pn": "p_02", "pv": "3c"},  # Humidity (60%)
                                    ],
                                },
                                {
                                    "pn": "e_3003",
                                    "pch": [
                                        {"pn": "p_1D", "pv": "00"},  # Comfort OFF
                                        {"pn": "p_24", "pv": "00"},  # Econo OFF
                                    ],
                                },
                                {
                                    "pn": "e_A001",
                                    # Model "AMVA17MXTF" (hex ASCII, space-padded)
                                    "pch": [
                                        {
                                            "pn": "p_01",
                                            "pv": "2020202020414D564131374D585446",
                                        },
                                    ],
                                },
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0200.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1003",
                            "pch": [
                                {
                                    "pn": "e_A00D",
                                    "pch": [
                                        {"pn": "p_01", "pv": "2200"}
                                    ],  # Outside temp, LE 2-byte (17°C)
                                },
                                {
                                    "pn": "e_A005",
                                    "pch": [
                                        {
                                            "pn": "p_01",
                                            "pv": "8C0000",
                                        },  # Compressor 70°C
                                        {"pn": "p_02", "pv": "410000"},
                                    ],
                                },
                                {
                                    "pn": "e_A001",
                                    "pch": [
                                        {
                                            "pn": "p_01",
                                            "pv": "2020202020414D564131374D5852",
                                        },  # Model "AMVA17MXR"
                                    ],
                                },
                                {
                                    "pn": "e_3002",
                                    "pch": [
                                        {"pn": "p_3D", "pv": "00"},  # Quiet OFF
                                        {"pn": "p_44", "pv": "00"},  # Powerful OFF
                                    ],
                                },
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {
                    "pn": "week_power",
                    "pch": [
                        {"pn": "today_runtime", "pv": "120"},
                        {"pn": "datas", "pv": [100, 200, 300, 400, 500, 600, 700]},
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {
                    "pn": "adp_i",
                    "pch": [
                        {"pn": "mac", "pv": "112233445566"},
                        {"pn": "ver", "pv": "3_12_3"},
                        {"pn": "api_ver", "pv": "2_2"},
                        {
                            "pn": "func",
                            "pch": [{"pn": "en_ipw_sep", "pv": 0}],
                        },
                    ],
                },
                "rsc": 2000,
            },
        ]
    }

    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(mock_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    # Mock response for setting operations
    set_response = {
        "responses": [{"fr": "/dsiot/edge/adr_0100.dgc_status", "rsc": 2004}]
    }

    # Add mock for the set operation
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(set_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    # Add mock for the status update after setting
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(mock_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    device = DaikinBRP084('ip', session=client_session)
    await device.init()

    # Test power setting
    requests = []
    device.requests = requests
    device._handle_power_setting({'mode': 'off'}, requests)
    assert len(requests) == 1
    assert requests[0].name == "p_01"
    assert requests[0].value == "00"

    # Test power on and mode setting
    requests = []
    device._handle_power_setting({'mode': 'cool'}, requests)
    assert len(requests) == 2
    assert requests[0].name == "p_01"
    assert requests[0].value == "01"  # Power on
    assert requests[1].name == "p_01"
    assert requests[1].value == "0200"  # Cool mode

    # Test temperature setting
    requests = []
    device._handle_temperature_setting({'stemp': '25.0'}, requests)
    assert len(requests) == 1
    assert requests[0].name == "p_02"  # Cool mode temp parameter
    assert requests[0].value == "32"  # 25°C in hex

    # Test fan setting
    requests = []
    device._handle_fan_setting({'f_rate': 'auto'}, requests)
    assert len(requests) == 1
    assert requests[0].name == "p_09"  # Cool mode fan parameter
    assert requests[0].value == "0A00"  # Auto fan speed

    # Test swing setting
    requests = []
    device._handle_swing_setting({'f_dir': 'both'}, requests)
    assert len(requests) == 2
    assert requests[0].name == "p_05"  # Vertical swing parameter for cool mode
    assert requests[0].value == device.TURN_ON_SWING_AXIS
    assert requests[1].name == "p_06"  # Horizontal swing parameter for cool mode
    assert requests[1].value == device.TURN_ON_SWING_AXIS

    # Test the full set method with multiple settings
    await device.set(
        {'mode': 'cool', 'stemp': '26.0', 'f_rate': 'auto', 'f_dir': 'both'}
    )

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_add_request_direct(client_session):
    """Test the add_request method directly."""
    device = DaikinBRP084('ip', session=client_session)

    # Initialize requests list
    requests = []

    # Test adding a power request
    power_path = device.get_path("power")
    device.add_request(requests, power_path, "01")  # Power on

    assert len(requests) == 1
    assert requests[0].name == "p_01"
    assert requests[0].value == "01"
    assert requests[0].path == ["e_1002", "e_A002"]
    assert requests[0].to == "/dsiot/edge/adr_0100.dgc_status"

    # Test adding a mode request
    mode_path = device.get_path("mode")
    device.add_request(requests, mode_path, "0200")  # Cool mode

    assert len(requests) == 2
    assert requests[1].name == "p_01"
    assert requests[1].value == "0200"
    assert requests[1].path == ["e_1002", "e_3001"]
    assert requests[1].to == "/dsiot/edge/adr_0100.dgc_status"

    # Test adding a temperature request
    temp_path = device.get_path("temp_settings", "cool")
    device.add_request(requests, temp_path, "32")  # 25°C

    assert len(requests) == 3
    assert requests[2].name == "p_02"
    assert requests[2].value == "32"
    assert requests[2].path == ["e_1002", "e_3001"]
    assert requests[2].to == "/dsiot/edge/adr_0100.dgc_status"


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'hhum': '60'}, 60.0),
        ({'hhum': '25.5'}, 25.5),
        ({'hhum': '-'}, None),
        ({'hhum': '--'}, None),
        ({}, None),
        ({'hhum': None}, None),
        ({'hhum': 'invalid'}, None),
    ],
)
def test_humidity(values, expected):
    """Test the humidity property for DaikinBRP084."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.humidity == expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'hhum': '60'}, True),
        ({'hhum': '25.5'}, True),
        ({'hhum': '-'}, False),
        ({'hhum': '--'}, False),
        ({}, False),
        ({'hhum': None}, False),
        ({'hhum': 'invalid'}, False),
    ],
)
def test_support_humidity(values, expected):
    """Test the support_humidity property for DaikinBRP084."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_humidity is expected


@pytest.mark.parametrize(
    'value, expected',
    [
        ('0D00', 6.5),  # 0x000D = 13, /2
        ('2200', 17.0),  # 0x0022 = 34, /2
        ('F6FF', -5.0),  # 0xFFF6 = -10 (signed), /2
        ('00FF', -128.0),  # 0xFF00 = -256 (signed), /2
    ],
)
def test_hex_le_to_temp(value, expected):
    """Little-endian signed temperature decoding (handles sub-zero)."""
    assert DaikinBRP084.hex_le_to_temp(value) == expected


@pytest.mark.parametrize(
    'value, expected',
    [
        ('2020202020414D564131374D585446', 'AMVA17MXTF'),
        ('202020202020202031313230303045', '112000E'),
        ('notvalidhex', 'notvalidhex'),  # falls back to input
    ],
)
def test_hex_to_ascii(value, expected):
    """Hex-ASCII model/serial decoding with padding trimmed."""
    assert DaikinBRP084.hex_to_ascii(value) == expected


def test_handle_feature_toggles():
    """Feature toggles accept human and raw values, rejecting garbage."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)

    requests = []
    device._handle_feature_toggles({'comfort': 'on'}, requests)
    assert len(requests) == 1
    assert requests[0].name == 'p_1D'
    assert requests[0].value == '01'
    assert requests[0].path == ['e_1002', 'e_3003']

    # Econo (indoor e_3003/p_24)
    requests = []
    device._handle_feature_toggles({'econo': 'on'}, requests)
    assert requests[0].name == 'p_24'
    assert requests[0].value == '01'
    assert requests[0].path == ['e_1002', 'e_3003']

    # Outdoor quiet + powerful live on the outdoor unit (adr_0200 / e_3002)
    requests = []
    device._handle_feature_toggles({'outdoor_quiet': '01'}, requests)
    assert requests[0].name == 'p_3D'
    assert requests[0].path == ['e_1003', 'e_3002']
    assert requests[0].to == '/dsiot/edge/adr_0200.dgc_status'

    requests = []
    device._handle_feature_toggles({'powerful': 'on'}, requests)
    assert requests[0].name == 'p_44'
    assert requests[0].path == ['e_1003', 'e_3002']
    assert requests[0].to == '/dsiot/edge/adr_0200.dgc_status'

    # Garbage / empty -> no-op
    requests = []
    device._handle_feature_toggles({'comfort': 'bogus'}, requests)
    assert len(requests) == 0
    device._handle_feature_toggles({}, requests)
    assert len(requests) == 0


def test_powerful_mutual_exclusion():
    """Enabling Powerful clears active comfort/econo/quiet, and vice-versa."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)

    # Powerful on while comfort+econo are active -> both get cleared to 00.
    device.values.update({'comfort': 'on', 'econo': 'on', 'outdoor_quiet': 'off'})
    requests = []
    device._handle_feature_toggles({'powerful': 'on'}, requests)
    by_name = {r.name: r.value for r in requests}
    assert by_name['p_44'] == '01'  # powerful on
    assert by_name['p_1D'] == '00'  # comfort cleared
    assert by_name['p_24'] == '00'  # econo cleared
    assert 'p_3D' not in by_name  # quiet was already off, not touched

    # Turning comfort on while powerful is active -> powerful cleared.
    device.values.update({'powerful': 'on', 'comfort': 'off'})
    requests = []
    device._handle_feature_toggles({'comfort': 'on'}, requests)
    by_name = {r.name: r.value for r in requests}
    assert by_name['p_1D'] == '01'  # comfort on
    assert by_name['p_44'] == '00'  # powerful cleared


def test_handle_vane_setting():
    """Discrete vertical vane writes the mode-specific property."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.values.update({'mode': 'cool'})

    requests = []
    device._handle_vane_setting({'vane_vertical': 'down'}, requests)
    assert len(requests) == 1
    assert requests[0].name == 'p_05'  # cool vertical
    assert requests[0].value == '17000000'

    requests = []
    device._handle_vane_setting({'vane_vertical': 'swing'}, requests)
    assert requests[0].value == '0F000000'

    requests = []
    device._handle_vane_setting({'vane_vertical': 'off'}, requests)
    assert requests[0].value == '00000000'

    # 'up' no longer exists (byte-1 is inert) and unknown positions -> no-op
    for bad in ('up', 'sideways'):
        requests = []
        device._handle_vane_setting({'vane_vertical': bad}, requests)
        assert len(requests) == 0

    # In a mode without swing settings (off) -> no-op
    device.values.update({'mode': 'off'})
    requests = []
    device._handle_vane_setting({'vane_vertical': 'down'}, requests)
    assert len(requests) == 0


def test_vane_overrides_swing_vertical():
    """When both f_dir and vane_vertical are set, vane wins the vertical axis."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.values.update({'mode': 'cool'})

    requests = []
    settings = {'f_dir': 'both', 'vane_vertical': 'down'}
    device._handle_swing_setting(settings, requests)
    device._handle_vane_setting(settings, requests)

    verticals = [r for r in requests if r.name == 'p_05']
    assert len(verticals) == 1  # no duplicate vertical write
    assert verticals[0].value == '17000000'  # the vane value, not swing
    # horizontal swing still applied
    assert any(r.name == 'p_06' for r in requests)


@pytest.mark.asyncio
async def test_null_outdoor_temp(aresponses, client_session):
    """Test that a null outdoor temperature is handled gracefully."""
    mock_response = {
        "responses": [
            {
                "fr": "/dsiot/edge/adr_0100.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1002",
                            "pch": [
                                {"pn": "e_A002", "pch": [{"pn": "p_01", "pv": "01"}]},
                                {
                                    "pn": "e_3001",
                                    "pch": [
                                        {"pn": "p_01", "pv": "0200"},
                                        {"pn": "p_02", "pv": "32"},
                                        {"pn": "p_09", "pv": "0A00"},
                                        {"pn": "p_05", "pv": "000000"},
                                        {"pn": "p_06", "pv": "000000"},
                                    ],
                                },
                                {
                                    "pn": "e_A00B",
                                    "pch": [
                                        {"pn": "p_01", "pv": "18"},
                                        {"pn": "p_02", "pv": "3c"},
                                    ],
                                },
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0200.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1003",
                            "pch": [
                                {
                                    "pn": "e_A00D",
                                    "pch": [{"pn": "p_01", "pv": None}],
                                }
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {
                    "pn": "week_power",
                    "pch": [
                        {"pn": "today_runtime", "pv": "0"},
                        {"pn": "datas", "pv": [0, 0, 0, 0, 0, 0, 0]},
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {"pn": "adp_i", "pch": [{"pn": "mac", "pv": "112233445566"}]},
                "rsc": 2000,
            },
        ]
    }

    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(mock_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    device = DaikinBRP084('ip', session=client_session)
    await device.init()

    assert device.values.get('otemp') == '--'
    assert device.values.get('mode') == 'cool'
    assert device.values.get('htemp') == '24.0'


@pytest.mark.asyncio
async def test_firmware_version_extraction(aresponses, client_session):
    """Test that firmware version is extracted from adapter info."""
    mock_response = {
        "responses": [
            {
                "fr": "/dsiot/edge/adr_0100.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1002",
                            "pch": [
                                {"pn": "e_A002", "pch": [{"pn": "p_01", "pv": "01"}]},
                                {
                                    "pn": "e_3001",
                                    "pch": [
                                        {"pn": "p_01", "pv": "0200"},
                                        {"pn": "p_02", "pv": "32"},
                                        {"pn": "p_09", "pv": "0A00"},
                                        {"pn": "p_05", "pv": "000000"},
                                        {"pn": "p_06", "pv": "000000"},
                                    ],
                                },
                                {
                                    "pn": "e_A00B",
                                    "pch": [
                                        {"pn": "p_01", "pv": "18"},
                                        {"pn": "p_02", "pv": "3c"},
                                    ],
                                },
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0200.dgc_status",
                "pc": {
                    "pn": "dgc_status",
                    "pch": [
                        {
                            "pn": "e_1003",
                            "pch": [
                                {
                                    "pn": "e_A00D",
                                    "pch": [{"pn": "p_01", "pv": "22"}],
                                }
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {
                    "pn": "week_power",
                    "pch": [
                        {"pn": "today_runtime", "pv": "120"},
                        {"pn": "datas", "pv": [100, 200, 300, 400, 500, 600, 700]},
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {
                    "pn": "adp_i",
                    "pch": [
                        {"pn": "mac", "pv": "112233445566"},
                        {"pn": "ver", "pv": "3_12_3"},
                    ],
                },
                "rsc": 2000,
            },
        ]
    }

    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(mock_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    device = DaikinBRP084('ip', session=client_session)
    await device.init()

    assert device.values.get('ver') == '3_12_3'
    assert device.values.get('mac') == '112233445566'


def test_empty_settings_sends_power_on(client_session):
    """set({}) sends a power-ON request (HA toggle-switch path)."""
    device = DaikinBRP084('ip', session=client_session)
    requests = []
    device._handle_power_setting({}, requests)

    assert len(requests) == 1
    assert requests[0].name == "p_01"
    assert requests[0].value == "01"


def test_stemp_only_no_power_write(client_session):
    """set({'stemp': X}) does not touch power."""
    device = DaikinBRP084('ip', session=client_session)
    device.values['mode'] = 'cool'

    requests = []
    device._handle_power_setting({'stemp': '25.0'}, requests)

    assert len(requests) == 0


def test_f_rate_only_no_power_write(client_session):
    """set({'f_rate': X}) does not touch power."""
    device = DaikinBRP084('ip', session=client_session)
    device.values['mode'] = 'cool'

    requests = []
    device._handle_power_setting({'f_rate': 'auto'}, requests)

    assert len(requests) == 0


def test_mode_off_sends_power_off(client_session):
    """set({'mode': 'off'}) sends power OFF and no mode write."""
    device = DaikinBRP084('ip', session=client_session)
    requests = []
    device._handle_power_setting({'mode': 'off'}, requests)

    assert len(requests) == 1
    assert requests[0].name == "p_01"
    assert requests[0].value == "00"


def test_valid_mode_sends_power_on_and_mode(client_session):
    """set({'mode': 'cool'}) sends power ON followed by mode hex."""
    device = DaikinBRP084('ip', session=client_session)
    requests = []
    device._handle_power_setting({'mode': 'cool'}, requests)

    assert len(requests) == 2
    assert requests[0].value == "01"  # power on
    assert requests[1].value == "0200"  # cool hex


def test_hot_mode_sends_correct_hex(client_session):
    """set({'mode': 'hot'}) maps to hex 0100."""
    device = DaikinBRP084('ip', session=client_session)
    requests = []
    device._handle_power_setting({'mode': 'hot'}, requests)

    assert len(requests) == 2
    assert requests[0].value == "01"  # power on
    assert requests[1].value == "0100"  # hot hex


def test_unrecognized_mode_logs_warning(client_session, caplog):
    """Unrecognized mode sends power ON but no mode write, and logs a warning."""
    import logging

    device = DaikinBRP084('ip', session=client_session)
    requests = []

    with caplog.at_level(logging.WARNING):
        device._handle_power_setting({'mode': 'bogus'}, requests)

    assert len(requests) == 1  # power ON only
    assert requests[0].value == "01"
    assert "Unrecognized mode" in caplog.text
    assert "bogus" in caplog.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    'method, arg, expected',
    [
        ('set_comfort_mode', 'on', {'comfort': 'on'}),
        ('set_econo_mode', 'off', {'econo': 'off'}),
        ('set_outdoor_quiet_mode', 'on', {'outdoor_quiet': 'on'}),
        ('set_powerful_mode', 'on', {'powerful': 'on'}),
        ('set_vertical_vane', 'down', {'vane_vertical': 'down'}),
    ],
)
async def test_feature_convenience_setters(method, arg, expected):
    """Each convenience setter delegates to set() with the right payload."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.set = AsyncMock()

    await getattr(device, method)(arg)

    device.set.assert_awaited_once_with(expected)


@pytest.mark.parametrize(
    'values, support, current',
    [
        ({'comfort': 'on'}, ('support_comfort_mode', 'comfort_mode'), 'on'),
        ({'econo': 'off'}, ('support_econo_mode', 'econo_mode'), 'off'),
        (
            {'outdoor_quiet': 'on'},
            ('support_outdoor_quiet_mode', 'outdoor_quiet_mode'),
            'on',
        ),
        ({'powerful': 'on'}, ('support_powerful_mode', 'powerful_mode'), 'on'),
    ],
)
def test_feature_support_and_current(values, support, current):
    """support_* is True once the value is present; the getter returns it."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)

    support_prop, current_prop = support
    assert getattr(device, support_prop) is False
    assert getattr(device, current_prop) is None

    device.values.update(values)
    assert getattr(device, support_prop) is True
    assert getattr(device, current_prop) == current


def test_vertical_vane_property():
    """vertical_vane reflects the decoded vane position, None when unknown."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)

    assert device.vertical_vane is None

    device.values.update({'vane_vertical': 'swing'})
    assert device.vertical_vane == 'swing'


def test_extract_optional_readings_guards_missing_containers():
    """A response missing every optional container leaves values unset, no raise."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.values['mode'] = 'cool'  # in swing_settings, so the vane path is tried

    # No 'responses' matching any optional path -> every guarded read hits
    # DaikinException and is swallowed.
    device._extract_optional_readings({'responses': []})

    for key in ('comfort', 'econo', 'outdoor_quiet', 'powerful', 'vane_vertical'):
        assert key not in device.values
