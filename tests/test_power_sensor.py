"""Test for Daikin AC power & energy sensors."""
from asyncio import coroutine
from datetime import datetime, timedelta
import random
from unittest.mock import patch
from pydaikin.daikin_base import Appliance, ATTR_TOTAL, ATTR_COOL, ATTR_HEAT
from pydaikin.daikin_brp069 import DaikinBRP069

from freezegun import freeze_time
import pytest


@pytest.fixture
def device():
    """Mock daikin power/energy endpoints."""

    # Each ticks represent 100w consumption
    cool_energy_100w_ticks = set()
    heat_energy_100w_ticks = set()

    def _consume_100w_cool():
        # Simulate 100w consumption in cool mode
        # print(['COOL', datetime.utcnow().strftime('%H:%M')])
        cool_energy_100w_ticks.add(datetime.utcnow())

    def _consume_100w_heat():
        # Simulate 100w consumption in heat mode
        # print(['HEAT', datetime.utcnow().strftime('%H:%M')])
        heat_energy_100w_ticks.add(datetime.utcnow())

    def _get_total_kW_last_30_minutes():
        # The DaikinPowerSensor should return the same state
        ticks = cool_energy_100w_ticks.union(heat_energy_100w_ticks)
        dt0 = datetime.utcnow()
        return sum(0.2 for dt in ticks if dt0 - timedelta(minutes=30) < dt <= dt0)

    def _get_cool_kWh_previous_hour():
        # The DaikinEnergySensor (cool) should return the same state
        dt0 = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        return sum(
            0.1 for dt in cool_energy_100w_ticks if dt0 - timedelta(hours=1) < dt <= dt0
        )

    def _get_heat_kWh_previous_hour():
        # The DaikinEnergySensor (heat) should return the same state
        dt0 = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        return sum(
            0.1 for dt in heat_energy_100w_ticks if dt0 - timedelta(hours=1) < dt <= dt0
        )

    def get_value(key, default=None):
        if key == "name":
            return "ac-bedroom"
        if key == "mac":
            return "0"
        if key == "frate_steps":
            return "2"
        if key in ("previous_year", "this_year"):
            return '/'.join(map(str, range(12)))
        if key == "datas":
            ticks = cool_energy_100w_ticks.union(heat_energy_100w_ticks)
            dt0 = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            return "/".join(
                str(
                    sum(
                        100
                        for dt in ticks
                        if dt0 - timedelta(days=d) < dt <= dt0 - timedelta(days=d - 1)
                    )
                )
                for d in reversed(range(7))
            )
        if key in (
            "prev_1day_cool",
            "curr_day_cool",
            "prev_1day_heat",
            "curr_day_heat",
        ):
            ticks = cool_energy_100w_ticks if "cool" in key else heat_energy_100w_ticks
            dt0 = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            dt0 = dt0 if "curr" in key else dt0 - timedelta(days=1)
            return "/".join(
                str(
                    sum(
                        1
                        for dt in ticks
                        if dt0 + timedelta(hours=h)
                        < dt
                        <= dt0 + timedelta(hours=h + 1)
                        < datetime.utcnow()
                    )
                )
                for h in reversed(range(24))
            )

    # monkey patch async MagicMock
    async def magic_get_resource(resource, retries=3):
        return dict(foo='bar')

    with patch.object(DaikinBRP069, 'discover_ip'):
        device = DaikinBRP069('ip')
        device._cool_energy_100w_ticks = cool_energy_100w_ticks
        device._heat_energy_100w_ticks = heat_energy_100w_ticks
        device._consume_100w_cool = _consume_100w_cool
        device._consume_100w_heat = _consume_100w_heat
        device._get_total_kW_last_30_minutes = _get_total_kW_last_30_minutes
        device._get_cool_kWh_previous_hour = _get_cool_kWh_previous_hour
        device._get_heat_kWh_previous_hour = _get_heat_kWh_previous_hour

        with patch.object(device, 'values') as values, patch.object(device, '_get_resource') as get_resource:
            get_resource.side_effect = magic_get_resource
            values.get.side_effect = get_value
            values.__getitem__ = get_value
            values.__contains__ = lambda self, key: get_value(key) is not None

            yield device


VERBOSE_TOTAL = False
VERBOSE_HEAT = False
VERBOSE_COOL = False


@pytest.mark.parametrize(
    "initial_date,duration,tick_step",
    [
        (datetime.utcnow().replace(hour=10, minute=10), timedelta(hours=5), timedelta(minutes=2)),
        (datetime.utcnow().replace(hour=23, minute=5), timedelta(hours=3), timedelta(seconds=30)),
        (datetime.utcnow().replace(hour=20, minute=0), timedelta(hours=36), timedelta(minutes=5)),
    ]
)
async def test_power_sensors(initial_date, duration, tick_step, device: DaikinBRP069):
    """Simulate AC consumption and check sensors' state."""
    with freeze_time(initial_date) as ft:
        dt = None

        await device.init()

        assert 'datas' in device.values
        assert device.support_energy_consumption

        # For energy sensors, we tolerate a delay before we receive the right value
        cool_error_duration = timedelta(minutes=0)
        heat_error_duration = timedelta(minutes=0)

        while datetime.utcnow() < initial_date + duration:

            # We simulate the consumption
            if random.random() < (0.5 if datetime.utcnow().hour % 6 == 0 else 0.05):
                if random.random() < 0.7:
                    if VERBOSE_COOL or VERBOSE_TOTAL: print('%s COOL' % datetime.utcnow().time().strftime('%H:%M'))
                    device._consume_100w_cool()
                else:
                    if VERBOSE_HEAT or VERBOSE_TOTAL: print('%s HEAT' % datetime.utcnow().time().strftime('%H:%M'))
                    device._consume_100w_heat()

            # We update the device
            await device.update_status()

            if dt is not None:
                diff = abs(device._get_total_kW_last_30_minutes() - device.current_total_power_consumption)
                if VERBOSE_TOTAL:
                    print('%s total // real=%.02f meas_today=%.02f, meas_yest=%0.2f, meas_current=%.02f %d %s-%s %s' % (
                        datetime.utcnow().time().strftime('%H:%M'),
                        device._get_total_kW_last_30_minutes(),
                        device.today_energy_consumption(ATTR_TOTAL),
                        device.yesterday_energy_consumption(ATTR_TOTAL),
                        device.current_total_power_consumption,
                        len(device._energy_consumption_history['heat']),
                        device._energy_consumption_history['total'][-1][0].time().strftime('%H:%M'),
                        device._energy_consumption_history['total'][0][0].time().strftime('%H:%M'),
                        ' DIFF !!' if diff > 1e-6 else '',
                    ))
                assert diff < 1e-6

                diff = abs(device._get_cool_kWh_previous_hour() - device.last_hour_cool_power_consumption)
                if VERBOSE_COOL:
                    print('%s cool  // real=%.02f meas_today=%.02f, meas_yest=%0.2f, meas_current=%.02f %d %s-%s %s' % (
                        datetime.utcnow().time().strftime('%H:%M'),
                        device._get_cool_kWh_previous_hour(),
                        device.today_energy_consumption(ATTR_COOL),
                        device.yesterday_energy_consumption(ATTR_COOL),
                        device.last_hour_cool_power_consumption,
                        len(device._energy_consumption_history['cool']),
                        device._energy_consumption_history['cool'][-1][0].time().strftime('%H:%M'),
                        device._energy_consumption_history['cool'][0][0].time().strftime('%H:%M'),
                        ' DIFF !!' if diff > 1e-6 else '',
                    ))
                if device._get_cool_kWh_previous_hour() > 1e-6:
                    assert diff < 1e-6
                elif diff >= 1e-6:
                    # If the expected measure is 0 the appliance will measure it with a delay
                    cool_error_duration += dt
                else:
                    cool_error_duration = timedelta(minutes=0)
                assert cool_error_duration < timedelta(minutes=10) + tick_step

                diff = abs(device._get_heat_kWh_previous_hour() - device.last_hour_heat_power_consumption)
                if VERBOSE_HEAT:
                    print('%s heat  // real=%.02f meas_today=%.02f, meas_yest=%0.2f, meas_current=%.02f %d %s-%s %s' % (
                        datetime.utcnow().time().strftime('%H:%M'),
                        device._get_heat_kWh_previous_hour(),
                        device.today_energy_consumption(ATTR_HEAT),
                        device.yesterday_energy_consumption(ATTR_HEAT),
                        device.last_hour_heat_power_consumption,
                        len(device._energy_consumption_history['heat']),
                        device._energy_consumption_history['heat'][-1][0].time().strftime('%H:%M'),
                        device._energy_consumption_history['heat'][0][0].time().strftime('%H:%M'),
                        ' DIFF !!' if diff > 1e-6 else '',
                    ))
                if device._get_heat_kWh_previous_hour() > 1e-6:
                    assert diff < 1e-6
                elif diff >= 1e-6:
                    # If the expected measure is 0 the appliance will measure it with a delay
                    heat_error_duration += dt
                else:
                    heat_error_duration = timedelta(minutes=0)
                assert heat_error_duration < timedelta(minutes=10) + tick_step

            # Random ticking
            dt = timedelta(seconds=random.randint(1, tick_step.total_seconds()), milliseconds=random.randint(0, 1000))
            ft.tick(dt)
