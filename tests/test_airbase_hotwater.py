"""Tests for Daikin AirBase heat pump hot water devices."""

import re
from unittest.mock import MagicMock

from aiohttp import ClientSession
import pytest
import pytest_asyncio

from pydaikin.daikin_airbase_hotwater import (
    AirBaseHotWaterResponseError,
    DaikinAirBaseHotWater,
)


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.asyncio
async def test_init(aresponses, client_session):
    """Test fetching and representing hot water status."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response=(
            "ret=OK,pow=1,boost=0,vacation=0,vacation_days=3,"
            "temp_set=63.0,temp_tank=56,temp_outside=13,boil_level=0,drive_p=5,"
            "drive_p1s=42,drive_p1e=14,drive_p2s=22,drive_p2e=28"
        ),
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.init()

    assert device.values.get("pow", invalidate=False) == "1"
    assert device.values.get("mode", invalidate=False) == "auto"
    assert device.represent("pow") == ("power", "on")
    assert device.represent("mode") == ("mode", "auto")
    assert device.represent("temp_tank") == ("tank temp", "56")
    assert device.represent("drive_p") == ("drive program", "program_1")
    assert device.represent("drive_p1s") == ("program 1 start", "21:00")
    assert device.represent("drive_p1e") == ("program 1 end", "07:00")
    assert device.represent("drive_p2s") == ("program 2 start", "11:00")
    assert device.represent("drive_p2e") == ("program 2 end", "14:00")
    assert device.tank_temperature == 56.0
    assert device.target_temperature == 63.0
    assert device.outside_temperature == 13.0
    assert device.support_away_mode is False
    assert device.support_fan_rate is False
    assert device.support_swing_mode is False
    assert device.support_humidity is False

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_get_status_returns_typed_values(aresponses, client_session):
    """Test fetching typed hot water status."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response=(
            "ret=OK,pow=1,boost=0,vacation=0,vacation_days=3,"
            "temp_set=63.0,temp_tank=56,temp_outside=13,boil_level=0,drive_p=5,"
            "drive_p1s=42,drive_p1e=14,drive_p2s=22,drive_p2e=28"
        ),
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    assert await device.get_status() == {
        "power": True,
        "boost": False,
        "vacation": False,
        "vacation_days": 3,
        "boil_level": 0,
        "drive_p": 5,
        "drive_program": "program_1",
        "set_program": None,
        "manual_program_1": True,
        "manual_program_2": False,
        "mode": "auto",
        "temp_set": 63.0,
        "temp_tank": 56.0,
        "temp_outside": 13.0,
        "drive_p1s": 42,
        "drive_p1e": 14,
        "drive_p2s": 22,
        "drive_p2e": 28,
        "program_1_start": "21:00",
        "program_1_end": "07:00",
        "program_2_start": "11:00",
        "program_2_end": "14:00",
    }

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_get_status_returns_manual_program_pair(aresponses, client_session):
    """Test drive_p=6 represents manual programs 1 and 2 together."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=OK,pow=1,boil_level=0,drive_p=6",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    status = await device.get_status()

    assert status["drive_p"] == 6
    assert status["drive_program"] == "program_1_and_2"
    assert status["set_program"] is None
    assert status["manual_program_1"] is True
    assert status["manual_program_2"] is True
    assert device.represent("drive_p") == ("drive program", "program_1_and_2")

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_get_status_returns_set_program(aresponses, client_session):
    """Test set programs are represented as mutually exclusive selections."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=OK,pow=1,boil_level=0,drive_p=2",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    status = await device.get_status()

    assert status["drive_p"] == 2
    assert status["drive_program"] == "set_02"
    assert status["set_program"] == 2
    assert status["manual_program_1"] is False
    assert status["manual_program_2"] is False

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_manual_mode(aresponses, client_session):
    """Test that non-zero boil levels are manual mode."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=OK,pow=1,boost=1,vacation=0,vacation_days=0,boil_level=4",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.init()

    assert device.values.get("boil_level", invalidate=False) == "4"
    assert device.values.get("mode", invalidate=False) == "manual"
    assert device.represent("mode") == ("mode", "manual")

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_power_off_represents_mode_as_off(aresponses, client_session):
    """Test powered off hot water devices follow the existing mode=off convention."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=OK,pow=0,boost=0,vacation=0,vacation_days=0,boil_level=4",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.init()

    assert device.values.get("mode", invalidate=False) == "manual"
    assert device.represent("mode") == ("mode", "off")

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_get_status_rejects_bad_ret(aresponses, client_session):
    """Test bad status responses raise a clear exception."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=NG",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    with pytest.raises(AirBaseHotWaterResponseError):
        await device.get_status()

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_get_status_rejects_invalid_boil_level(aresponses, client_session):
    """Test invalid boil levels in status responses raise a clear exception."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=OK,boil_level=7",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    with pytest.raises(AirBaseHotWaterResponseError):
        await device.get_status()

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_get_status_rejects_invalid_drive_program_time(
    aresponses, client_session
):
    """Test invalid drive program slots in status responses raise clearly."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=OK,boil_level=0,drive_p1s=48",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    with pytest.raises(AirBaseHotWaterResponseError):
        await device.get_status()

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_get_status_rejects_invalid_drive_program(aresponses, client_session):
    """Test invalid drive program values in status responses raise clearly."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/get_unit_info",
        method_pattern="GET",
        response="ret=OK,boil_level=0,drive_p=7",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    with pytest.raises(AirBaseHotWaterResponseError):
        await device.get_status()

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_set_control_sends_normalized_params(aresponses, client_session):
    """Test setting multiple writable controls."""
    aresponses.add(
        path_pattern=re.compile(
            r"/skyfi/hotwater/set_control_info\?"
            r"(?=.*boil_level=6)(?=.*boost=1)(?=.*vacation=0)"
            r"(?=.*drive_p=5)(?=.*drive_p1s=42)(?=.*drive_p1e=14)"
        ),
        method_pattern="GET",
        match_querystring=True,
        response="ret=OK",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.set_control(
        boil_level=6,
        boost=True,
        vacation=0,
        drive_program="program_1",
        program_1_start="21:00",
        program_1_end="07:00",
    )

    assert device.values.get("boil_level", invalidate=False) == "6"
    assert device.values.get("boost", invalidate=False) == "1"
    assert device.values.get("vacation", invalidate=False) == "0"
    assert device.values.get("drive_p", invalidate=False) == "5"
    assert device.values.get("drive_p1s", invalidate=False) == "42"
    assert device.values.get("drive_p1e", invalidate=False) == "14"
    assert device.values.get("mode", invalidate=False) == "manual"

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_set_mode_auto_sends_power_and_boil_level(aresponses, client_session):
    """Test setting auto mode powers on and sets boil level to auto."""
    aresponses.add(
        path_pattern=re.compile(
            r"/skyfi/hotwater/set_control_info\?(?=.*pow=1)(?=.*boil_level=0)"
        ),
        method_pattern="GET",
        match_querystring=True,
        response="ret=OK",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.set({"mode": "auto"})

    assert device.values.get("pow", invalidate=False) == "1"
    assert device.values.get("boil_level", invalidate=False) == "0"
    assert device.values.get("mode", invalidate=False) == "auto"

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_set_mode_off_sends_power_off(aresponses, client_session):
    """Test setting mode off uses the existing CLI mode convention."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/set_control_info?pow=0",
        method_pattern="GET",
        match_querystring=True,
        response="ret=OK",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.set({"mode": "off"})

    assert device.values.get("pow", invalidate=False) == "0"

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_helper_methods(aresponses, client_session):
    """Test helper setters call the control endpoint."""
    for expected_path in [
        re.compile(r"/skyfi/hotwater/set_control_info\?(?=.*pow=1)(?=.*boil_level=0)"),
        re.compile(r"/skyfi/hotwater/set_control_info\?(?=.*pow=1)(?=.*boil_level=3)"),
        "/skyfi/hotwater/set_control_info?boost=0",
        "/skyfi/hotwater/set_control_info?vacation=1",
        "/skyfi/hotwater/set_control_info?pow=0",
    ]:
        aresponses.add(
            path_pattern=expected_path,
            method_pattern="GET",
            match_querystring=True,
            response="ret=OK",
        )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.set_mode_auto()
    await device.set_mode_manual(3)
    await device.set_boost(False)
    await device.set_vacation(True)
    await device.set_power(False)

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_vacation_days_helper(aresponses, client_session):
    """Test vacation days helper validation and request."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/set_control_info?vacation_days=14",
        method_pattern="GET",
        match_querystring=True,
        response="ret=OK",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.set_vacation_days(14)

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_drive_program_helpers(aresponses, client_session):
    """Test drive program helper methods normalize human and raw times."""
    for expected_path in [
        re.compile(
            r"/skyfi/hotwater/set_control_info\?(?=.*drive_p1s=42)(?=.*drive_p1e=14)"
        ),
        re.compile(
            r"/skyfi/hotwater/set_control_info\?(?=.*drive_p2s=22)(?=.*drive_p2e=28)"
        ),
    ]:
        aresponses.add(
            path_pattern=expected_path,
            method_pattern="GET",
            match_querystring=True,
            response="ret=OK",
        )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.set_drive_program_1("21:00", "07:00")
    await device.set_drive_program_2(22, 28)

    assert device.values.get("drive_p1s", invalidate=False) == "42"
    assert device.values.get("drive_p1e", invalidate=False) == "14"
    assert device.values.get("drive_p2s", invalidate=False) == "22"
    assert device.values.get("drive_p2e", invalidate=False) == "28"

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_drive_program_selection_helper(aresponses, client_session):
    """Test active drive program helper accepts generic labels."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/set_control_info?drive_p=5",
        method_pattern="GET",
        match_querystring=True,
        response="ret=OK",
    )
    aresponses.add(
        path_pattern="/skyfi/hotwater/set_control_info?drive_p=6",
        method_pattern="GET",
        match_querystring=True,
        response="ret=OK",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)

    await device.set_drive_program_selection("program_1")
    await device.set_drive_program_selection("program_1_and_2")

    assert device.values.get("drive_p", invalidate=False) == "6"

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_program_2_selection_requires_program_1_when_current_program_is_known(
    client_session,
):
    """Test program 2 selection is blocked when program 1 is known inactive."""
    device = DaikinAirBaseHotWater("ip", session=client_session)
    device.values["drive_p"] = "4"

    with pytest.raises(ValueError):
        await device.set_drive_program_selection("program_2")


@pytest.mark.asyncio
async def test_set_program_selection_is_mutually_exclusive(aresponses, client_session):
    """Test selecting a fixed set program sends one drive_p value."""
    aresponses.add(
        path_pattern="/skyfi/hotwater/set_control_info?drive_p=3",
        method_pattern="GET",
        match_querystring=True,
        response="ret=OK",
    )

    device = DaikinAirBaseHotWater("ip", session=client_session)
    device.values["drive_p"] = "2"

    await device.set_drive_set_program(3)

    assert device.values.get("drive_p", invalidate=False) == "3"

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


def test_set_control_validation():
    """Test invalid control values are rejected before HTTP requests."""
    device = DaikinAirBaseHotWater("ip", session=MagicMock())

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"temp_set": 60})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"boil_level": 7})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"mode": "manual"})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params(
            {"mode": "auto", "boil_level": 3}
        )

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"vacation_days": 366})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"pow": 2})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"drive_p": 0})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"drive_program": "set_07"})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"drive_p1s": 48})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"drive_p1s": "21:15"})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"drive_p1s": "24:00"})

    with pytest.raises(ValueError):
        DaikinAirBaseHotWater._normalize_control_params({"program_1_start": True})

    assert DaikinAirBaseHotWater._normalize_control_params(
        {
            "power": "on",
            "boost": "off",
            "vacation_days": 14,
            "drive_program": "set_04",
            "program_1_start": "21:00",
            "program_1_end": "7:00",
            "program_2_start": "22",
            "program_2_end": 28,
        }
    ) == {
        "pow": "1",
        "boost": "0",
        "vacation_days": "14",
        "drive_p": "4",
        "drive_p1s": "42",
        "drive_p1e": "14",
        "drive_p2s": "22",
        "drive_p2e": "28",
    }

    assert DaikinAirBaseHotWater._normalize_control_params(
        {"drive_program": "program_1_and_2"}
    ) == {
        "drive_p": "6",
    }

    assert DaikinAirBaseHotWater._normalize_control_params(
        {"drive_program": "program_2"}
    ) == {
        "drive_p": "6",
    }

    assert DaikinAirBaseHotWater._drive_time_slot_to_time(42, "drive_p1s") == "21:00"

    assert device.humidity is None
