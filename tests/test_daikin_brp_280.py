"""Verify that init() calls the expected set of endpoints for firmware 2.8.0 devices."""

from aiohttp import ClientSession
import json
import pytest
import pytest_asyncio

from pydaikin.daikin_brp_280 import DaikinBRP280


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.asyncio
async def test_daikin_brp_280(aresponses, client_session):
    """Test the DaikinBRP280 class for firmware 2.8.0 devices."""
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
                                {
                                    "pn": "e_A002",
                                    "pch": [{"pn": "p_01", "pv": "01"}]
                                },
                                {
                                    "pn": "e_3001",
                                    "pch": [
                                        {"pn": "p_01", "pv": "0200"},  # Mode (COOL)
                                        {"pn": "p_02", "pv": "32"},     # Cool temp (25°C)
                                        {"pn": "p_09", "pv": "0A00"},   # Cool fan speed (AUTO)
                                        {"pn": "p_05", "pv": "000000"}, # Vertical swing OFF
                                        {"pn": "p_06", "pv": "000000"}  # Horizontal swing OFF
                                    ]
                                },
                                {
                                    "pn": "e_A00B",
                                    "pch": [
                                        {"pn": "p_01", "pv": "18"},  # Room temp (24°C)
                                        {"pn": "p_02", "pv": "3c"}   # Humidity (60%)
                                    ]
                                }
                            ]
                        }
                    ]
                },
                "rsc": 2000
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
                                    "pch": [{"pn": "p_01", "pv": "22"}]  # Outside temp (17°C)
                                }
                            ]
                        }
                    ]
                },
                "rsc": 2000
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {
                    "pn": "week_power",
                    "pch": [
                        {"pn": "today_runtime", "pv": "120"},
                        {"pn": "datas", "pv": [100, 200, 300, 400, 500, 600, 700]}
                    ]
                },
                "rsc": 2000
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {
                    "pn": "adp_i",
                    "pch": [{"pn": "mac", "pv": "112233445566"}]
                },
                "rsc": 2000
            }
        ]
    }
    
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=json.dumps(mock_response),
    )
    
    # Mock response for setting temperature
    temp_update_response = {
        "responses": [
            {
                "fr": "/dsiot/edge/adr_0100.dgc_status",
                "rsc": 2004
            }
        ]
    }
    
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=json.dumps(temp_update_response),
    )
    
    # Add another mock for the status update after setting
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=json.dumps(mock_response),
    )

    device = DaikinBRP280('ip', session=client_session)
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