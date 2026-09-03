"""Test DaikinBRP069 set methods and error handling."""

from aiohttp import ClientSession
import pytest
import pytest_asyncio

from pydaikin.daikin_brp069 import DaikinBRP069


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.asyncio
async def test_set_holiday(aresponses, client_session):
    """Test set_holiday method."""
    # Mock response
    aresponses.add(
        path_pattern="/common/set_holiday",
        method_pattern="GET",
        response="ret=OK",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.set_holiday("1")

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_set_advanced_mode(aresponses, client_session):
    """Test set_advanced_mode method."""
    # Mock response for set_special_mode endpoint
    aresponses.add(
        path_pattern="/aircon/set_special_mode",
        method_pattern="GET",
        response="ret=OK,adv=13",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.set_advanced_mode("powerful", "1")

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_set_streamer(aresponses, client_session):
    """Test set_streamer method."""
    # Mock response for enabling streamer
    aresponses.add(
        path_pattern="/aircon/set_special_mode",
        method_pattern="GET",
        response="ret=OK",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.set_streamer("1")

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_set_streamer_invalid_value(aresponses, client_session):
    """Test set_streamer with invalid value does nothing."""
    device = DaikinBRP069("192.168.1.100", session=client_session)

    # Should not make any requests with invalid value
    await device.set_streamer("invalid")

    # No requests should have been made
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_set_clock(aresponses, client_session):
    """Test set_clock method."""
    # Mock response
    aresponses.add(
        path_pattern="/common/notify_date_time",
        method_pattern="GET",
        response="ret=OK",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.set_clock()

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_set_clock_error_handling(aresponses, client_session):
    """Test set_clock error handling."""
    # Mock error response - the error is caught so request completes.
    # The retry logic makes 3 attempts, so register the route 3 times.
    for _ in range(3):
        aresponses.add(
            path_pattern="/common/notify_date_time",
            method_pattern="GET",
            response=aresponses.Response(status=500, text="Error"),
        )

    device = DaikinBRP069("192.168.1.100", session=client_session)

    # Should not raise exception, just log error
    await device.set_clock()

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_auto_set_clock(aresponses, client_session):
    """Test auto_set_clock method."""
    # Mock response
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.auto_set_clock()

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_auto_set_clock_error_handling(aresponses, client_session):
    """Test auto_set_clock error handling."""
    # Mock error response - the error is caught so request completes.
    # The retry logic makes 3 attempts, so register the route 3 times.
    for _ in range(3):
        aresponses.add(
            path_pattern="/common/get_datetime",
            method_pattern="GET",
            response=aresponses.Response(status=500, text="Error"),
        )

    device = DaikinBRP069("192.168.1.100", session=client_session)

    # Should not raise exception, just log error
    await device.auto_set_clock()

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_set_zone(aresponses, client_session):
    """Test set_zone method (empty implementation)."""
    device = DaikinBRP069("192.168.1.100", session=client_session)

    # Should not fail, just do nothing
    await device.set_zone(1, 'key', 'value')


@pytest.mark.asyncio
async def test_get_demand_control(aresponses, client_session):
    """Test get_demand_control returns cached values without a request."""
    device = DaikinBRP069("192.168.1.100", session=client_session)
    # Data is fetched and cached by update_status
    device.values.update_by_resource(
        "aircon/get_demand_control",
        {"en_demand": "1", "mode": "0", "max_pow": "45"},
    )

    response = device.get_demand_control()

    assert response == {"en_demand": "1", "mode": "0", "max_pow": "45"}

    # No HTTP request should be made (no routes are registered)


@pytest.mark.asyncio
async def test_get_demand_control_unsupported(aresponses, client_session):
    """Test get_demand_control on a device that does not support it."""
    device = DaikinBRP069("192.168.1.100", session=client_session)
    # Unit does not advertise demand control capability via model_info (dmnd)
    device.values["dmnd"] = "0"

    response = device.get_demand_control()

    assert response == {}
    assert device.support_demand_control is False


@pytest.mark.asyncio
async def test_set_demand_control(aresponses, client_session):
    """Test set_demand_control method."""
    aresponses.add(
        path_pattern="/aircon/set_demand_control",
        method_pattern="GET",
        response="ret=OK",
    )
    aresponses.add(
        path_pattern="/aircon/get_demand_control",
        method_pattern="GET",
        response="ret=OK,type=1,en_demand=1,mode=0,max_pow=40,scdl_per_day=4,moc=0,tuc=0,wec=0,thc=0,frc=0,sac=0,suc=0",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.set_demand_control(en_demand="1", max_pow=40, mode="0")

    # Verify the set request carried the right query params
    request = aresponses.history[0].request
    assert request.path == "/aircon/set_demand_control"
    assert request.query["en_demand"] == "1"
    assert request.query["max_pow"] == "40"
    assert request.query["mode"] == "0"

    # State should be refreshed from the follow-up get request
    assert device.values.get("max_pow", invalidate=False) == "40"
    # Demand control "mode" is remapped to "dmd_mode" in flat values
    assert device.values.get("dmd_mode", invalidate=False) == "0"

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_set_demand_control_human_values(aresponses, client_session):
    """Test set_demand_control maps human values to Daikin values."""
    aresponses.add(
        path_pattern="/aircon/set_demand_control",
        method_pattern="GET",
        response="ret=OK",
    )
    aresponses.add(
        path_pattern="/aircon/get_demand_control",
        method_pattern="GET",
        response="ret=OK,type=1,en_demand=1,mode=0,max_pow=30,scdl_per_day=4,moc=0,tuc=0,wec=0,thc=0,frc=0,sac=0,suc=0",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.set_demand_control(en_demand="on", max_pow=30)

    request = aresponses.history[0].request
    assert request.query["en_demand"] == "1"
    assert request.query["max_pow"] == "30"

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_get_info_resources_demand_control(aresponses, client_session):
    """Test get_info_resources includes demand control when supported."""
    device = DaikinBRP069("192.168.1.100", session=client_session)

    assert "aircon/get_demand_control" not in device.get_info_resources()

    device.values["dmnd"] = "1"
    assert "aircon/get_demand_control" in device.get_info_resources()

    device.values["dmnd"] = "0"
    assert "aircon/get_demand_control" not in device.get_info_resources()


@pytest.mark.asyncio
async def test_update_status_demand_control_remapping(aresponses, client_session):
    """Test that update_status remaps demand control 'mode' to 'dmd_mode'."""
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25,otemp=20",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=3,stemp=22",
    )
    aresponses.add(
        path_pattern="/aircon/get_demand_control",
        method_pattern="GET",
        response="ret=OK,en_demand=1,mode=0,max_pow=45",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.values["dmnd"] = "1"
    await device.update_status()

    # HVAC mode from get_control_info is stored as "mode"
    assert device.values.get("mode", invalidate=False) == "3"
    # Demand control mode is remapped to "dmd_mode"
    assert device.values.get("dmd_mode", invalidate=False) == "0"
    # Raw resource response still contains the original "mode" key
    raw = device.values.values_for_resource(
        "aircon/get_demand_control", invalidate=False
    )
    assert raw["mode"] == "0"
