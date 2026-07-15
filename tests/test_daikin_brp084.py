"""Verify that init() calls the expected set of endpoints for firmware 2.8.0 devices."""

import json
from unittest.mock import MagicMock

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
                                        {"pn": "p_01", "pv": "22"}
                                    ],  # Outside temp (17°C)
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
                                        {"pn": "p_01", "pv": "22"}
                                    ],  # Outside temp (17°C)
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


def _energy_response(
    en_ipw_sep="0",
    datas=None,
    datas2=None,
    this_year=None,
    previous_year=None,
):
    """Build a minimal multireq response exercising only the energy paths."""
    week_pch = [{"pn": "today_runtime", "pv": "120"}]
    if datas is not None:
        week_pch.append({"pn": "datas", "pv": datas})
    if datas2 is not None:
        week_pch.append({"pn": "datas2", "pv": datas2})

    year_pch = []
    if this_year is not None:
        year_pch.append({"pn": "this_year", "pv": this_year})
    if previous_year is not None:
        year_pch.append({"pn": "previous_year", "pv": previous_year})

    adp_pch = [{"pn": "mac", "pv": "112233445566"}]
    if en_ipw_sep is not None:
        adp_pch.append({"pn": "func", "pch": [{"pn": "en_ipw_sep", "pv": en_ipw_sep}]})

    return {
        "responses": [
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {"pn": "week_power", "pch": week_pch},
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.year_power",
                "pc": {"pn": "year_power", "pch": year_pch},
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {"pn": "adp_i", "pch": adp_pch},
                "rsc": 2000,
            },
        ]
    }


def _make_device():
    return DaikinBRP084('127.0.0.1', session=MagicMock())


def test_extract_energy_full_breakdown():
    """Combined-metering device derives cool/heat split and yearly series."""
    device = _make_device()
    response = _energy_response(
        en_ipw_sep="0",
        datas=[0, 0, 0, 0, 0, 500, 1000],  # weekly totals (Wh)
        datas2=[0, 0, 0, 0, 0, 200, 300],  # weekly cooling (Wh)
        this_year=[10, 20, 30],
        previous_year=[5, 6, 7],
    )

    device._extract_energy(response)

    assert device.values['today_runtime'] == "120"
    assert device.values['en_ipw_sep'] == "0"
    assert device.values['datas'] == "0/0/0/0/0/500/1000"
    assert device.values['datas2'] == "0/0/0/0/0/200/300"
    # today: total 1000Wh -> 10, cool 300Wh -> 3, heat 10-3 = 7 (0.1 kWh units)
    assert device.values['curr_day_cool'] == "3"
    assert device.values['curr_day_heat'] == "7"
    # yesterday: total 500 -> 5, cool 200 -> 2, heat 3
    assert device.values['prev_1day_cool'] == "2"
    assert device.values['prev_1day_heat'] == "3"
    assert device.values['this_year'] == "10/20/30"
    assert device.values['previous_year'] == "5/6/7"


def test_extract_energy_separate_metering_skips_split():
    """en_ipw_sep=1 means datas2 is not a comparable total, so no derivation."""
    device = _make_device()
    response = _energy_response(
        en_ipw_sep="1",
        datas=[0, 0, 0, 0, 0, 500, 1000],
        datas2=[0, 0, 0, 0, 0, 200, 300],
        this_year=[1, 2, 3],
    )

    device._extract_energy(response)

    assert device.values['en_ipw_sep'] == "1"
    assert device.values['datas'] == "0/0/0/0/0/500/1000"
    # Heat/cool split guarded off for separate-metering adapters.
    assert 'datas2' not in device.values
    assert 'curr_day_cool' not in device.values
    assert 'curr_day_heat' not in device.values
    # Yearly data is independent of the split and still extracted.
    assert device.values['this_year'] == "1/2/3"


def test_extract_energy_absent_en_ipw_sep_defaults_to_combined():
    """A device that omits en_ipw_sep is treated as combined metering."""
    device = _make_device()
    response = _energy_response(
        en_ipw_sep=None,
        datas=[100, 1000],
        datas2=[40, 300],
    )

    device._extract_energy(response)

    assert 'en_ipw_sep' not in device.values
    assert device.values['curr_day_cool'] == "3"  # 300 // 100
    assert device.values['curr_day_heat'] == "7"  # 1000//100 - 3


def test_extract_energy_without_cooling_series():
    """No datas2 -> weekly totals kept, but no heat/cool split is synthesised."""
    device = _make_device()
    response = _energy_response(datas=[100, 1000], datas2=None)

    device._extract_energy(response)

    assert device.values['datas'] == "100/1000"
    assert 'datas2' not in device.values
    assert 'curr_day_cool' not in device.values


def test_extract_energy_missing_everything_is_guarded():
    """A response with no power series leaves energy values unset, no raise."""
    device = _make_device()
    device._extract_energy({'responses': []})

    for key in ('today_runtime', 'datas', 'datas2', 'this_year', 'previous_year'):
        assert key not in device.values
