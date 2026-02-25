"""Test energy consumption and power monitoring."""

from unittest.mock import MagicMock

from aiohttp import ClientSession
import pytest
import pytest_asyncio

from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.power import (
    ATTR_COOL,
    ATTR_HEAT,
    ATTR_TOTAL,
    TIME_LAST_7_DAYS,
    TIME_LAST_YEAR,
    TIME_THIS_YEAR,
    TIME_TODAY,
    TIME_YESTERDAY,
)


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.asyncio
async def test_energy_consumption_with_data(aresponses, client_session):
    """Test energy consumption with actual data."""
    # Mock BRP069 responses
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,pow=1,mac=112233445566",
    )
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2",
    )
    aresponses.add(
        path_pattern="/aircon/get_day_power_ex",
        method_pattern="GET",
        response="ret=OK,curr_day_heat=10/20/30/40/50/60/70/80/90/100/110/120/130/140/150/160/170/180/190/200/210/220/230/240,prev_1day_heat=50/60/70/80/90/100/110/120/130/140/150/160/170/180/190/200/210/220/230/240/250/260/270/280,curr_day_cool=15/25/35/45/55/65/75/85/95/105/115/125/135/145/155/165/175/185/195/205/215/225/235/245,prev_1day_cool=55/65/75/85/95/105/115/125/135/145/155/165/175/185/195/205/215/225/235/245/255/265/275/285",
    )
    aresponses.add(
        path_pattern="/aircon/get_week_power",
        method_pattern="GET",
        response="ret=OK,today_runtime=38,datas=1000/2000/3000/4000/5000/6000/700",
    )
    aresponses.add(
        path_pattern="/aircon/get_year_power",
        method_pattern="GET",
        response="ret=OK,previous_year=100/200/300/400/500/600/700/800/900/1000/1100/1200,this_year=50/100/150/200/250/300/350/400",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.init()

    # Test support_energy_consumption (should be True with data)
    assert device.support_energy_consumption is True

    # Test today's cool energy consumption
    cool_today = device.energy_consumption(
        mode=ATTR_COOL, time=TIME_TODAY, invalidate=False
    )
    assert cool_today is not None
    assert cool_today > 0

    # Test today's heat energy consumption
    heat_today = device.energy_consumption(
        mode=ATTR_HEAT, time=TIME_TODAY, invalidate=False
    )
    assert heat_today is not None
    assert heat_today > 0

    # Test yesterday's cool energy
    cool_yesterday = device.energy_consumption(
        mode=ATTR_COOL, time=TIME_YESTERDAY, invalidate=False
    )
    assert cool_yesterday is not None

    # Test yesterday's heat energy
    heat_yesterday = device.energy_consumption(
        mode=ATTR_HEAT, time=TIME_YESTERDAY, invalidate=False
    )
    assert heat_yesterday is not None

    # Test total energy for last 7 days
    total_7days = device.energy_consumption(
        mode=ATTR_TOTAL, time=TIME_LAST_7_DAYS, invalidate=False
    )
    assert total_7days is not None
    assert total_7days > 0

    # Test this year's total
    this_year = device.energy_consumption(
        mode=ATTR_TOTAL, time=TIME_THIS_YEAR, invalidate=False
    )
    assert this_year is not None
    assert this_year > 0

    # Test last year's total
    last_year = device.energy_consumption(
        mode=ATTR_TOTAL, time=TIME_LAST_YEAR, invalidate=False
    )
    assert last_year is not None
    assert last_year > 0

    # Test property wrappers
    assert device.today_cool_energy_consumption is not None
    assert device.today_heat_energy_consumption is not None
    assert device.today_total_energy_consumption is not None
    assert device.today_energy_consumption is not None

    aresponses.assert_all_requests_matched()


@pytest.mark.asyncio
async def test_energy_consumption_no_data(aresponses, client_session):
    """Test energy consumption when no data is available."""
    # Mock BRP069 responses with no power data
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,pow=1,mac=112233445566",
    )
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2",
    )
    aresponses.add(
        path_pattern="/aircon/get_day_power_ex",
        method_pattern="GET",
        response="ret=OK,curr_day_heat=0/0/0/0,prev_1day_heat=0/0/0/0,curr_day_cool=0/0/0/0,prev_1day_cool=0/0/0/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_week_power",
        method_pattern="GET",
        response="ret=OK,today_runtime=0,datas=0/0/0/0/0/0/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_year_power",
        method_pattern="GET",
        response="ret=OK,previous_year=0/0/0/0/0/0/0/0/0/0/0/0,this_year=0/0/0/0/0/0/0/0",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.init()

    # Test support_energy_consumption (should be False with no data)
    assert device.support_energy_consumption is False

    aresponses.assert_all_requests_matched()


def test_energy_consumption_invalid_parser():
    """Test energy consumption with invalid mode/time combination."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update({'datas': '100/200/300'})

    # Invalid mode/time combination should raise ValueError
    with pytest.raises(ValueError, match='Unsupported mode'):
        device.energy_consumption(
            mode='invalid_mode', time=TIME_TODAY, invalidate=False
        )


def test_energy_consumption_malformed_data():
    """Test energy consumption with malformed data."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)

    # Missing dimension
    device.values.update({})
    result = device.energy_consumption(
        mode=ATTR_TOTAL, time=TIME_TODAY, invalidate=False
    )
    assert result is None

    # Non-numeric data
    device.values.update({'curr_day_cool': 'invalid/data'})
    result = device.energy_consumption(
        mode=ATTR_COOL, time=TIME_TODAY, invalidate=False
    )
    assert result is None

    # Empty data
    device.values.update({'curr_day_cool': ''})
    result = device.energy_consumption(
        mode=ATTR_COOL, time=TIME_TODAY, invalidate=False
    )
    assert result is None


def test_energy_today_wrapper_properties():
    """Test today's energy consumption wrapper properties."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device.values.update(
        {
            'curr_day_cool': '10/20/30/40',
            'curr_day_heat': '15/25/35/45',
            'datas': '1000/2000/3000/4000/5000/6000/7000',
        }
    )

    # Test individual properties
    cool = device.today_cool_energy_consumption
    heat = device.today_heat_energy_consumption
    total = device.today_total_energy_consumption
    combined = device.today_energy_consumption

    assert cool is not None
    assert heat is not None
    assert total is not None
    assert combined is not None
    assert combined == (cool + heat)


def test_compute_diff_energy_normal():
    """Test _compute_diff_energy with normal increasing consumption."""
    from datetime import datetime, timezone

    from pydaikin.power import EnergyConsumptionState

    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)

    # Normal case: today growing
    prev_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=10.0,
        yesterday=5.0,
    )
    curr_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=12.0,
        yesterday=5.0,
    )

    diff = device._compute_diff_energy(ATTR_TOTAL, curr_state, prev_state)
    assert diff == 2.0


def test_compute_diff_energy_day_rollover():
    """Test _compute_diff_energy with day rollover scenario."""
    from datetime import datetime, timezone

    from pydaikin.power import EnergyConsumptionState

    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)

    # Day rollover: today decreased, yesterday >= prev.today
    prev_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=23.0,
        yesterday=10.0,
    )
    curr_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=2.0,
        yesterday=23.0,
    )

    diff = device._compute_diff_energy(ATTR_TOTAL, curr_state, prev_state)
    # Should be: yesterday - prev.today + today = 23.0 - 23.0 + 2.0 = 2.0
    assert diff == 2.0


def test_compute_diff_energy_missing_yesterday():
    """Test _compute_diff_energy with missing yesterday data."""
    from datetime import datetime, timezone

    from pydaikin.power import EnergyConsumptionState

    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)

    # Decreasing today with no yesterday data
    prev_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=23.0,
        yesterday=10.0,
    )
    curr_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=2.0,
        yesterday=None,
    )

    diff = device._compute_diff_energy(ATTR_TOTAL, curr_state, prev_state)
    # Should return None due to impossible measurement
    assert diff is None


def test_compute_diff_energy_impossible():
    """Test _compute_diff_energy with impossible scenario."""
    from datetime import datetime, timezone

    from pydaikin.power import EnergyConsumptionState

    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)

    # Impossible case: yesterday < prev.today and today < prev.today
    prev_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=23.0,
        yesterday=10.0,
    )
    curr_state = EnergyConsumptionState(
        datetime=datetime.now(timezone.utc),
        first_state=False,
        today=2.0,
        yesterday=15.0,
    )

    diff = device._compute_diff_energy(ATTR_TOTAL, curr_state, prev_state)
    # Should return None due to impossible measurement
    assert diff is None


def test_current_power_consumption_no_history():
    """Test current_power_consumption with no history."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)
    device._energy_consumption_history = {}

    power = device.current_power_consumption(mode=ATTR_TOTAL)
    assert power == 0


def test_current_power_consumption_type_errors():
    """Test current_power_consumption with invalid parameter types."""
    mock_session = MagicMock()
    device = DaikinBRP069('127.0.0.1', session=mock_session)

    # Invalid exp_diff_time_value type
    with pytest.raises(TypeError):
        device.current_power_consumption(exp_diff_time_value="invalid")

    # Invalid exp_diff_time_margin_factor type
    with pytest.raises(TypeError):
        device.current_power_consumption(exp_diff_time_margin_factor="invalid")
