"""Verify that init() calls the expected set of endpoints for firmware 2.8.0 devices."""

import json

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
                                        {"pn": "p_09", "pv": "0A00"},  # Cool fan speed (AUTO)
                                        {"pn": "p_05", "pv": "000000"},  # Vertical swing OFF
                                        {"pn": "p_06", "pv": "000000"},  # Horizontal swing OFF
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
    device.requests = requests
    device._handle_power_setting({'mode': 'cool'}, requests)
    assert len(requests) == 2
    assert requests[0].name == "p_01"
    assert requests[0].value == "01"  # Power on
    assert requests[1].name == "p_01"
    assert requests[1].value == "0200"  # Cool mode

    # Test temperature setting
    requests = []
    device.requests = requests
    device._handle_temperature_setting({'stemp': '25.0'}, requests)
    assert len(requests) == 1
    assert requests[0].name == "p_02"  # Cool mode temp parameter
    assert requests[0].value == "32"  # 25°C in hex

    # Test fan setting
    requests = []
    device.requests = requests
    device._handle_fan_setting({'f_rate': 'auto'}, requests)
    assert len(requests) == 1
    assert requests[0].name == "p_09"  # Cool mode fan parameter
    assert requests[0].value == "0A00"  # Auto fan speed

    # Test swing setting
    requests = []
    device.requests = requests
    device._handle_swing_setting({'f_dir': 'both'}, requests)
    assert len(requests) == 2
    assert requests[0].name == "p_05"  # Vertical swing parameter for cool mode
    assert requests[0].value == device.TURN_ON_SWING_AXIS
    assert requests[1].name == "p_06"  # Horizontal swing parameter for cool mode
    assert requests[1].value == device.TURN_ON_SWING_AXIS

    # Test the full set method with multiple settings
    await device.set({
        'mode': 'cool',
        'stemp': '26.0',
        'f_rate': 'auto',
        'f_dir': 'both'
    })

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_add_request_direct(client_session):
    """Test the add_request method directly."""
    device = DaikinBRP084('ip', session=client_session)
    
    # Initialize requests list
    device.requests = []
    
    # Test adding a power request
    power_path = device.get_path("power")
    device.add_request(power_path, "01")  # Power on
    
    assert len(device.requests) == 1
    assert device.requests[0].name == "p_01"
    assert device.requests[0].value == "01"
    assert device.requests[0].path == ["e_1002", "e_A002"]
    assert device.requests[0].to == "/dsiot/edge/adr_0100.dgc_status"
    
    # Test adding a mode request
    mode_path = device.get_path("mode")
    device.add_request(mode_path, "0200")  # Cool mode
    
    assert len(device.requests) == 2
    assert device.requests[1].name == "p_01"
    assert device.requests[1].value == "0200"
    assert device.requests[1].path == ["e_1002", "e_3001"]
    assert device.requests[1].to == "/dsiot/edge/adr_0100.dgc_status"
    
    # Test adding a temperature request
    temp_path = device.get_path("temp_settings", "cool")
    device.add_request(temp_path, "32")  # 25°C
    
    assert len(device.requests) == 3
    assert device.requests[2].name == "p_02"
    assert device.requests[2].value == "32"
    assert device.requests[2].path == ["e_1002", "e_3001"]
    assert device.requests[2].to == "/dsiot/edge/adr_0100.dgc_status"
