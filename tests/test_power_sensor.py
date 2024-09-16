"""Test for Daikin AC power & energy sensors."""

from datetime import datetime, timedelta
import random
from unittest.mock import patch

from freezegun import freeze_time
import pytest

from pydaikin.daikin_brp069 import DaikinBRP069

from .test_init import client_session


@pytest.fixture
def device():
    """Mock daikin power/energy endpoints."""

    # Each ticks represent 100w consumption
    cool_energy_100w_ticks = set()
    heat_energy_100w_ticks = set()

    def _consume_100w_cool():
        # Simulate 100w consumption in cool mode
        cool_energy_100w_ticks.add(datetime.utcnow())

    def _consume_100w_heat():
        # Simulate 100w consumption in heat mode
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

    def values_get(key, default=None):
        try:
            return values_getitem(key)
        except KeyError:
            return default

    def values_getitem(key):
        if key == "name":
            return "ac-bedroom"
        if key == "mac":
            return "0"
        if key == "frate_steps":
            return "2"
        if key in ("previous_year", "this_year"):
            return '/'.join(map(str, range(12)))
        if key == "htemp":
            return 22.0
        if key == "otemp":
            return 14.0
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
        raise KeyError(key)

    # monkey patch async MagicMock
    async def magic_get_resource(resource, retries=3):
        return dict(foo='bar')

    with patch.object(DaikinBRP069, 'discover_ip'):
        device = DaikinBRP069('ip', client_session)
        device._cool_energy_100w_ticks = cool_energy_100w_ticks
        device._heat_energy_100w_ticks = heat_energy_100w_ticks
        device._consume_100w_cool = _consume_100w_cool
        device._consume_100w_heat = _consume_100w_heat
        device._get_total_kW_last_30_minutes = _get_total_kW_last_30_minutes
        device._get_cool_kWh_previous_hour = _get_cool_kWh_previous_hour
        device._get_heat_kWh_previous_hour = _get_heat_kWh_previous_hour

        with (
            patch.object(device, 'values') as values,
            patch.object(device, '_get_resource') as get_resource,
        ):
            get_resource.side_effect = magic_get_resource
            values.get.side_effect = values_get
            values.__getitem__ = values_getitem
            values.__contains__ = lambda self, key: values_get(key) is not None

            yield device


VERBOSE = True


def relative_error(measured, expected):
    return abs(measured - expected) / expected


@pytest.mark.parametrize(
    "initial_date,duration,tick_step",
    [
        (
            datetime.utcnow().replace(hour=10, minute=0),
            timedelta(hours=5, minutes=20),
            timedelta(minutes=2),
        ),
        (
            datetime.utcnow().replace(hour=23, minute=5),
            timedelta(hours=3, minutes=30),
            timedelta(seconds=30),
        ),
        (
            datetime.utcnow().replace(hour=20, minute=0),
            timedelta(hours=28),
            timedelta(minutes=4),
        ),
    ],
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

        total_energy = 0
        cool_energy = 0
        heat_energy = 0

        while datetime.utcnow() < initial_date + duration:
            # We simulate the consumption
            # The consumption is stopped 2 hours before the end of the simulation to let the monitoring stabilize
            if datetime.utcnow() < initial_date + duration - timedelta(hours=2):
                if random.random() < (0.5 if datetime.utcnow().hour % 6 == 0 else 0.05):
                    if random.random() < 0.7:
                        if VERBOSE:
                            print(
                                '%s COOL'
                                % datetime.utcnow().strftime('%m/%d/%Y %H:%M:%S')
                            )
                        device._consume_100w_cool()
                    else:
                        if VERBOSE:
                            print(
                                '%s HEAT'
                                % datetime.utcnow().strftime('%m/%d/%Y %H:%M:%S')
                            )
                        device._consume_100w_heat()

            # We update the device
            await device.update_status()

            if VERBOSE:
                device.show_sensors()

            if dt is not None:
                diff = abs(
                    device._get_total_kW_last_30_minutes()
                    - device.current_total_power_consumption
                )
                assert diff < 1e-6

                diff = abs(
                    device._get_cool_kWh_previous_hour()
                    - device.last_hour_cool_energy_consumption
                )
                if diff >= 1e-6:
                    # If the expected measure is 0 the appliance will measure it with a delay
                    cool_error_duration += dt
                else:
                    cool_error_duration = timedelta(minutes=0)
                assert cool_error_duration < timedelta(minutes=10) + tick_step

                diff = abs(
                    device._get_heat_kWh_previous_hour()
                    - device.last_hour_heat_energy_consumption
                )
                if diff >= 1e-6:
                    # If the expected measure is 0 the appliance will measure it with a delay
                    heat_error_duration += dt
                else:
                    heat_error_duration = timedelta(minutes=0)
                assert heat_error_duration < timedelta(minutes=10) + tick_step

                total_energy += (
                    device.current_total_power_consumption * dt / timedelta(hours=1)
                )
                cool_energy += (
                    device.last_hour_cool_energy_consumption * dt / timedelta(hours=1)
                )
                heat_energy += (
                    device.last_hour_heat_energy_consumption * dt / timedelta(hours=1)
                )

            # Random ticking
            dt = timedelta(
                seconds=random.randint(1, tick_step.total_seconds()),
                milliseconds=random.randint(0, 1000),
            )
            ft.tick(dt)

    max_relative_error = tick_step.total_seconds() / timedelta(hours=1).total_seconds()
    assert (
        relative_error(
            total_energy,
            (len(device._cool_energy_100w_ticks) + len(device._heat_energy_100w_ticks))
            / 10,
        )
        < max_relative_error
    )
    assert (
        relative_error(cool_energy, len(device._cool_energy_100w_ticks) / 10)
        < max_relative_error
    )
    assert (
        relative_error(heat_energy, len(device._heat_energy_100w_ticks) / 10)
        < max_relative_error
    )
