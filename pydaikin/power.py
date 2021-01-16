from collections import namedtuple
from datetime import datetime, timedelta
import logging

ENERGY_CONSUMPTION_MAX_HISTORY = timedelta(hours=6)

ATTR_TOTAL = 'total'
ATTR_COOL = 'cool'
ATTR_HEAT = 'heat'

TIME_TODAY = 'today'
TIME_YESTERDAY = 'yesterday'
TIME_THIS_YEAR = 'this_year'
TIME_LAST_YEAR = 'last_year'

EnergyConsumptionParser = namedtuple(
    'EnergyConsumptionParser', ['dimension', 'reducer', 'divider']
)

EnergyConsumptionState = namedtuple(
    'EnergyConsumptionState', ['datetime', 'first_state', 'today', 'yesterday']
)

_LOGGER = logging.getLogger(__name__)


class DaikinPowerMixin:
    _energy_consumption_history = None
    values = None

    ENERGY_CONSUMPTION_PARSERS = {
        f'{ATTR_TOTAL}_{TIME_TODAY}': EnergyConsumptionParser(
            dimension='datas', reducer=lambda values: values[-1], divider=1000
        ),
        f'{ATTR_COOL}_{TIME_TODAY}': EnergyConsumptionParser(
            dimension='curr_day_cool', reducer=sum, divider=10
        ),
        f'{ATTR_HEAT}_{TIME_TODAY}': EnergyConsumptionParser(
            dimension='curr_day_heat', reducer=sum, divider=10
        ),
        f'{ATTR_TOTAL}_{TIME_YESTERDAY}': EnergyConsumptionParser(
            dimension='datas', reducer=lambda values: values[-2], divider=1000
        ),
        f'{ATTR_COOL}_{TIME_YESTERDAY}': EnergyConsumptionParser(
            dimension='prev_1day_cool', reducer=sum, divider=10
        ),
        f'{ATTR_HEAT}_{TIME_YESTERDAY}': EnergyConsumptionParser(
            dimension='prev_1day_heat', reducer=sum, divider=10
        ),
        f'{ATTR_TOTAL}_{TIME_THIS_YEAR}': EnergyConsumptionParser(
            dimension='this_year', reducer=sum, divider=1
        ),
        f'{ATTR_TOTAL}_{TIME_LAST_YEAR}': EnergyConsumptionParser(
            dimension='previous_year', reducer=sum, divider=1
        ),
    }

    @property
    def support_energy_consumption(self):
        """Return True if the device supports energy consumption monitoring."""
        return (self.energy_consumption(mode=ATTR_TOTAL, time=TIME_THIS_YEAR) or 0) + (
            self.energy_consumption(mode=ATTR_TOTAL, time=TIME_LAST_YEAR) or 0
        ) > 0

    def _register_energy_consumption_history(self):
        if not self.support_energy_consumption:
            return

        for mode in (ATTR_TOTAL, ATTR_COOL, ATTR_HEAT):
            new_state = EnergyConsumptionState(
                datetime=datetime.utcnow(),
                first_state=not (self._energy_consumption_history[mode]),
                today=self.energy_consumption(mode=mode, time=TIME_TODAY),
                yesterday=self.energy_consumption(mode=mode, time=TIME_YESTERDAY),
            )
            if new_state.today is None:
                continue

            if not new_state.first_state:
                old_state = self._energy_consumption_history[mode][0]

                if new_state.today == old_state.today:
                    if new_state.yesterday == old_state.yesterday:
                        # State has not changed, nothing to register, we just update the cmp_freq average
                        continue

            self._energy_consumption_history[mode].insert(0, new_state)

            # We can remove very old states (except the latest one)
            idx = (
                min(
                    (
                        i
                        for i, state in enumerate(
                            self._energy_consumption_history[mode]
                        )
                        if state.datetime
                        < datetime.utcnow() - ENERGY_CONSUMPTION_MAX_HISTORY
                    ),
                    default=len(self._energy_consumption_history[mode]),
                )
                + 1
            )

            self._energy_consumption_history[mode] = self._energy_consumption_history[
                mode
            ][:idx]

    def energy_consumption(self, mode=ATTR_TOTAL, time=TIME_TODAY):
        """Return today/yesterday energy consumption in kWh of a given mode."""
        parser = self.ENERGY_CONSUMPTION_PARSERS.get(f'{mode}_{time}')
        if parser is None:
            raise ValueError(f'Unsupported mode {mode} on {time}.')

        try:
            values = [int(x) for x in self.values.get(parser.dimension).split('/')]
            value = parser.reducer(values)
            value /= parser.divider
            return value
        except (TypeError, IndexError, AttributeError, ValueError):
            return None

    @staticmethod
    def _compute_diff_energy(mode: str, curr, prev):
        """Return the energy consumption delta between two states"""
        if curr.today > prev.today:
            # Normal behavior, today state is growing
            return curr.today - prev.today
        elif curr.yesterday is None:
            _LOGGER.error(
                f'Decreasing today state and missing yesterday state caused an impossible energy consumption measure of {mode}'
            )
            return None
        elif curr.yesterday >= prev.today:
            # If today state is not growing (or even declines), we probably have shifted 1 day
            # Thus we should have yesterday state greater or equal to previous today state
            # (in most cases it will be equal)
            return curr.yesterday - prev.today + curr.today
        else:
            _LOGGER.error(f'Impossible energy consumption measure of {mode}')
            return None

    def current_power_consumption(
        self, mode=ATTR_TOTAL, margin_window=None, margin_factor=None, min_power=0.1
    ):
        """
        Return the current power consumption of a given mode by estimating the slope of the energy consumption.
        When 100Wh have been consumed, it is assumed that the next 100Wh will be consumed in the same duration with a
        given margin in case the power consumption has been lowered (to smooth the consumption).
        """
        if not self._energy_consumption_history:
            # The sensor has not been properly initialized
            return 0

        if margin_window is None:
            margin_window = timedelta(seconds=0)
        if margin_factor is None:
            margin_factor = 0

        history = list(reversed(self._energy_consumption_history[mode]))

        energy_to_log = 0
        exp_diff_time = None
        est_power = 0

        for i, (prev, curr) in enumerate(zip(history, history[1:])):
            if prev.first_state:
                # We skip the first state as we cannot trust its datetime
                continue

            diff_time = curr.datetime - prev.datetime
            diff_energy = self._compute_diff_energy(mode, curr, prev)

            # We add the energy we should log right now
            energy_to_log += diff_energy

            # We remove the energy we've logged since last state update
            # This is to fix an incorrect estimation of the previous exp_diff_time
            if exp_diff_time and est_power > 0:
                # We know that the power will be cut off once the exp_diff_time is surpassed
                # Note this can result in negative value of energy_to_log when the exp_diff_time has been over-estimated
                energy_to_log -= max(est_power, min_power) * (
                    min(exp_diff_time, diff_time).total_seconds() / 3600
                )

            # We expect the consumption to be stable so the next diff_time should be barely the same as the previous one
            # If we over-estimate this duration, it will result in an irregular power consumption, often going back to 0
            # If we under-estimate this duration, it will ultimately result in a too smoothed power consumption
            # Feel free to fine-tune this variable to fit your needs...
            exp_diff_time = (diff_time + margin_window) * (1 + margin_factor)

            # Once we have estimated the next diff_time we can compute the estimated current power
            est_power = energy_to_log / (exp_diff_time.total_seconds() / 3600)
            est_power = max(est_power, 0)

            if min_power is not None and est_power > 0:
                est_power = max(est_power, min_power)

        if exp_diff_time and datetime.utcnow() > history[-1].datetime + exp_diff_time:
            # The power estimation was computed for a given duration
            # So if we exceed this duration we should return a zero power
            est_power = 0

        if min_power is not None and est_power > 0:
            est_power = max(est_power, min_power)

        return est_power
