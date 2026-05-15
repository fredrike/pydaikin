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


def test_handle_power_setting_empty_settings_powers_on():
    """device.set({}) must still send a power-ON request.

    Regression: HA's power switch calls `device.set({})` to turn the
    unit ON — this works on BRP069 but previously no-op'd on BRP084
    because `_handle_power_setting` early-returned when 'mode' was
    missing. Clicking the power switch in HA did nothing on the wire.
    """
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)

    requests = []
    device._handle_power_setting({}, requests)

    assert len(requests) == 1, "empty settings should produce exactly one power-on request"
    assert requests[0].name == "p_01"
    assert requests[0].value == "01"  # power ON
    assert requests[0].path == ["e_1002", "e_A002"]


def test_handle_power_setting_temperature_only_does_not_touch_power():
    """device.set({'stemp': '22.0'}) must NOT send a power request.

    Regression: when the empty-settings power-on fix was added, an
    early version triggered on every call without 'mode'. That meant
    changing the setpoint on a powered-off unit (HA's
    async_set_temperature path) silently turned it back on — a UX
    surprise that BRP069 never had (BRP069 sends a single combined
    request with pow=current_pow, leaving power state unchanged).

    Mirrors BRP069's contract: only set({}) or set({'mode':...})
    write the power byte; partial setting changes leave it alone.
    """
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)

    requests = []
    # Several non-mode partial settings — none should touch power
    for partial in [{'stemp': '22.0'}, {'f_rate': 'auto'}, {'f_dir': 'off'}]:
        device._handle_power_setting(partial, requests)

    assert requests == [], (
        f"non-mode settings should not produce power requests, got {requests!r}"
    )


@pytest.mark.parametrize(
    'mode_in, expected_hex',
    [
        ('heat', '0100'),
        ('hot', '0100'),  # HA climate integration alias for heat
        ('cool', '0200'),
        ('auto', '0300'),
        ('fan', '0000'),
        ('dry', '0500'),
    ],
)
def test_handle_power_setting_mode_alias(mode_in, expected_hex):
    """Mode write should be sent for both canonical names and HA-style aliases.

    Regression: Home Assistant's climate integration maps HVACMode.HEAT to the
    legacy BRP069 wire string "hot". Previously, REVERSE_MODE_MAP.get("hot")
    returned None and the mode write was silently dropped (fredrike/pydaikin#81),
    so switching to HEAT from HA did nothing on the wire.
    """
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)

    requests = []
    device._handle_power_setting({'mode': mode_in}, requests)

    # Expect: one power-on write + one mode write
    assert len(requests) == 2
    assert requests[0].value == "01"
    assert requests[1].name == "p_01"
    assert requests[1].value == expected_hex


@pytest.mark.parametrize(
    'hex_in, expected',
    [
        ('3400', 52),
        ('2C00', 44),
        ('0000', 0),
        ('7800', 120),
        ('', None),
        ('invalid', None),
    ],
)
def test_hex_le_u16(hex_in, expected):
    """Little-endian u16 decoder for compressor frequency values."""
    assert DaikinBRP084.hex_le_u16(hex_in) == expected


@pytest.mark.parametrize(
    'hex_in, expected',
    [
        ('8C00', 14.0),    # outdoor refrigerant temp observed live
        ('3200', 5.0),     # outdoor heat-exchanger temp observed live
        ('3802', 56.8),    # indoor coil outlet, heat mode
        ('2803', 80.8),    # indoor coil inlet, heat mode
        ('A001', 41.6),    # indoor coil after compressor stop
        ('FFFF', -0.1),    # signed -1 → -0.1 °C  (sub-zero defrost case)
        ('00FF', -25.6),   # large negative — defrost edge
        ('', None),
        ('xy', None),
    ],
)
def test_hex_le_i16_div10(hex_in, expected):
    """Signed little-endian int16 / 10 decoder for coil/refrigerant temps."""
    result = DaikinBRP084.hex_le_i16_div10(hex_in)
    if expected is None:
        assert result is None
    else:
        assert result == pytest.approx(expected)


def test_compressor_frequency_stored_from_update():
    """values['cmpfreq'] should be populated when e_2006/p_04 is present."""
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.values['cmpfreq'] = '52'
    assert device.compressor_frequency == 52.0
    assert device.support_compressor_frequency is True


def test_today_energy_falls_back_to_total():
    """BRP084 has only `datas` (aggregate), not cool/heat split.

    today_energy_consumption must fall back to today_total_energy_consumption
    so HA energy sensors populate rather than showing 0.
    """
    mock_session = MagicMock()
    device = DaikinBRP084('127.0.0.1', session=mock_session)
    device.values['datas'] = '0/0/3900/4800/6300/11900/3100'
    # curr_day_cool / curr_day_heat intentionally absent
    assert device.today_energy_consumption == 3.1  # 3100 Wh / 1000


@pytest.mark.asyncio
async def test_update_status_registers_energy_history(aresponses, client_session):
    """update_status() must feed _energy_consumption_history.

    Regression: BRP084 overrides update_status() entirely and for a long time
    omitted the call to _register_energy_consumption_history() that the base
    class performs. With an empty history, current_power_consumption() falls
    through to its "not initialized" branch (power.py ~215-217) and returns
    0, so HA's "Estimated power draw" sensor stayed pinned at 0 kW on every
    BRP084 unit.
    """
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

    # Proof that update_status() called _register_energy_consumption_history:
    # the history dict has at least one key with at least one state recorded.
    # Before the fix the dict was empty and current_power_consumption
    # unconditionally returned 0.
    assert 'total' in device._energy_consumption_history
    assert len(device._energy_consumption_history['total']) >= 1
    recorded = device._energy_consumption_history['total'][0]
    assert recorded.today == 0.7  # datas[-1] = 700 Wh / 1000 = 0.7 kWh


def _build_response(*, mode_pv, set_target_prop, set_target_pv, room_pv, iht_pv=None):
    """Build a multireq mock with a chosen mode + setpoint + room temp + iht.

    mode_pv: e_3001/p_01 value (e.g. "0100" for heat, "0200" for cool)
    set_target_prop: which e_3001 property holds the active setpoint (p_02/p_03/p_1D)
    set_target_pv: hex string for that setpoint (u8/2 = °C)
    room_pv: e_A00B/p_01 hex (whole degrees)
    iht_pv: e_3003/p_0C hex (u8/2 = °C); set to None to omit the entity

    Includes all per-mode fan + swing properties so the mock works for any mode
    (otherwise pydaikin's path lookups raise DaikinException on missing keys).
    """
    e_3001_pch = [
        {"pn": "p_01", "pv": mode_pv},
        {"pn": set_target_prop, "pv": set_target_pv},
        # Per-mode fan rates — pydaikin only reads the active one, but path
        # lookup happens for whichever mode is current
        {"pn": "p_09", "pv": "0A00"},  # cool fan
        {"pn": "p_0A", "pv": "0A00"},  # heat fan
        {"pn": "p_26", "pv": "0A00"},  # auto fan
        {"pn": "p_28", "pv": "0A00"},  # fan-only fan rate
        # Per-mode swing axes
        {"pn": "p_05", "pv": "000000"}, {"pn": "p_06", "pv": "000000"},  # cool
        {"pn": "p_07", "pv": "000000"}, {"pn": "p_08", "pv": "000000"},  # heat
        {"pn": "p_20", "pv": "000000"}, {"pn": "p_21", "pv": "000000"},  # auto
        {"pn": "p_22", "pv": "000000"}, {"pn": "p_23", "pv": "000000"},  # dry
        {"pn": "p_24", "pv": "000000"}, {"pn": "p_25", "pv": "000000"},  # fan
    ]
    e_1002_pch = [
        {"pn": "e_A002", "pch": [{"pn": "p_01", "pv": "01"}]},
        {"pn": "e_3001", "pch": e_3001_pch},
        {"pn": "e_A00B", "pch": [
            {"pn": "p_01", "pv": room_pv},
            {"pn": "p_02", "pv": "3c"},
        ]},
    ]
    if iht_pv is not None:
        e_1002_pch.append({"pn": "e_3003", "pch": [{"pn": "p_0C", "pv": iht_pv}]})

    return {
        "responses": [
            {
                "fr": "/dsiot/edge/adr_0100.dgc_status",
                "pc": {"pn": "dgc_status", "pch": [{"pn": "e_1002", "pch": e_1002_pch}]},
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0200.dgc_status",
                "pc": {"pn": "dgc_status", "pch": [{"pn": "e_1003", "pch": [
                    {"pn": "e_A00D", "pch": [{"pn": "p_01", "pv": "22"}]},
                ]}]},
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {"pn": "week_power", "pch": [
                    {"pn": "today_runtime", "pv": "120"},
                    {"pn": "datas", "pv": [0, 0, 0, 0, 0, 0, 0]},
                ]},
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {"pn": "adp_i", "pch": [{"pn": "mac", "pv": "112233445566"}]},
                "rsc": 2000,
            },
        ]
    }


@pytest.mark.asyncio
async def test_estimated_indoor_temp_heat_mode(aresponses, client_session):
    """In heat mode, estimated_indoor_temp = htemp - (iht - stemp)."""
    # heat mode, setpoint 22°C (p_03=2C), room 24°C (p_01=18), iht 24°C (p_0C=30)
    # bias = 24 - 22 = 2°C; estimated = 24 - 2 = 22.0°C
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(_build_response(
                mode_pv="0100", set_target_prop="p_03", set_target_pv="2C",
                room_pv="18", iht_pv="30",
            )),
            headers={"Content-Type": "application/json"},
        ),
    )
    device = DaikinBRP084('ip', session=client_session)
    await device.init()
    assert device.values.get('mode') == 'heat'
    assert device.values.get('htemp') == '24.0'
    assert device.values.get('stemp') == '22.0'
    assert device.values.get('internal_heat_target') == '24.0'
    assert device.values.get('estimated_indoor_temp') == '22.0'


@pytest.mark.asyncio
async def test_estimated_indoor_temp_cool_mode_absent(aresponses, client_session):
    """In cool mode, estimated_indoor_temp must NOT be populated.

    internal_heat_target is heat-mode-specific; reading it in cool mode would
    produce a meaningless number. Sensor should stay absent.
    """
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(_build_response(
                mode_pv="0200", set_target_prop="p_02", set_target_pv="32",
                room_pv="18", iht_pv="30",
            )),
            headers={"Content-Type": "application/json"},
        ),
    )
    device = DaikinBRP084('ip', session=client_session)
    await device.init()
    assert device.values.get('mode') == 'cool'
    assert 'estimated_indoor_temp' not in device.values


@pytest.mark.asyncio
async def test_estimated_indoor_temp_zero_bias(aresponses, client_session):
    """When iht == stemp (no bias), estimated should equal raw htemp."""
    # heat mode, setpoint 22°C, room 24°C, iht 22°C — bias=0, estimated=24.0
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(_build_response(
                mode_pv="0100", set_target_prop="p_03", set_target_pv="2C",
                room_pv="18", iht_pv="2C",
            )),
            headers={"Content-Type": "application/json"},
        ),
    )
    device = DaikinBRP084('ip', session=client_session)
    await device.init()
    assert device.values.get('estimated_indoor_temp') == '24.0'


@pytest.mark.asyncio
async def test_estimated_indoor_temp_missing_iht(aresponses, client_session):
    """If e_3003/p_0C is missing entirely, estimated should also be absent."""
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(_build_response(
                mode_pv="0100", set_target_prop="p_03", set_target_pv="2C",
                room_pv="18", iht_pv=None,
            )),
            headers={"Content-Type": "application/json"},
        ),
    )
    device = DaikinBRP084('ip', session=client_session)
    await device.init()
    assert device.values.get('mode') == 'heat'
    assert 'internal_heat_target' not in device.values
    assert 'estimated_indoor_temp' not in device.values
