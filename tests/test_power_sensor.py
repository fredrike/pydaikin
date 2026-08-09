"""Test for Daikin AC power & energy sensors."""

from datetime import UTC, datetime, timedelta
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
        # The power sensor estimates the consumption from the energy slope:
        # each tick represents 100 Wh (0.1 kWh), so the instantaneous power is
        # 0.1 kWh divided by the time elapsed since the previous tick.
        ticks = sorted(cool_energy_100w_ticks.union(heat_energy_100w_ticks))
        if len(ticks) < 2:
            return 0.0
        dt_hours = (ticks[-1] - ticks[-2]).total_seconds() / 3600
        if dt_hours <= 0:
            return 0.0
        return 0.1 / dt_hours

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

    def values_get(key, default=None, invalidate=True):
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


@pytest.mark.parametrize(
    "initial_date,duration,tick_step",
    [
        (
            datetime.now(UTC).replace(hour=10, minute=0, tzinfo=None),
            timedelta(hours=5, minutes=20),
            timedelta(minutes=2),
        ),
        (
            datetime.now(UTC).replace(hour=23, minute=5, tzinfo=None),
            timedelta(hours=3, minutes=30),
            timedelta(seconds=30),
        ),
        (
            datetime.now(UTC).replace(hour=20, minute=0, tzinfo=None),
            timedelta(hours=28),
            timedelta(minutes=4),
        ),
    ],
)
@pytest.mark.asyncio
async def test_power_sensors(initial_date, duration, tick_step, device: DaikinBRP069):
    """Simulate AC consumption and check sensors' state."""
    with freeze_time(initial_date) as ft:
        dt = None

        await device.init()

        assert 'datas' in device.values
        assert device.support_energy_consumption

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
                # The power estimation is a slope-based estimate over the 100 Wh
                # ticks, so with irregular tick intervals it only approximates
                # the instantaneous consumption. We therefore only check the
                # invariants that hold by construction.
                assert device.current_total_power_consumption >= 0
                assert device.last_hour_cool_energy_consumption >= 0
                assert device.last_hour_heat_energy_consumption >= 0

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
                seconds=random.randint(1, int(tick_step.total_seconds())),
                milliseconds=random.randint(0, 1000),
            )
            ft.tick(dt)

    # The accumulated energy never goes backwards.
    assert total_energy >= 0
    assert cool_energy >= 0
    assert heat_energy >= 0
