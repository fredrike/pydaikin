"""Pydaikin power mixin."""

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
    """Mixin to provide power monitoring capability"""

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
                        # State has not changed, nothing to register,
                        # we just update the cmp_freq average
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

        if curr.yesterday is None:
            _LOGGER.error(
                'Decreasing today state and missing yesterday state caused an '
                'impossible energy consumption measure of %s',
                mode,
            )
            return None

        if curr.yesterday >= prev.today:
            # If today state is not growing (or even declines), we probably have
            # shifted 1 day. Thus we should have yesterday state greater or equal
            # to previous today state (in most cases it will be equal)
            return curr.yesterday - prev.today + curr.today

        _LOGGER.error('Impossible energy consumption measure of %s', mode)
        return None

    def current_power_consumption(  # pylint: disable=too-many-branches
        self,
        mode=ATTR_TOTAL,
        exp_diff_time_value=None,
        exp_diff_time_margin_factor=None,
        min_power=0.1,
    ):
        """
        Return the current power consumption of a given mode by estimating the slope
        of the energy consumption. When 100Wh have been consumed, it is assumed that
        the next 100Wh will be consumed in the same duration with a given margin in
        case the power consumption has been lowered (to smooth the consumption).
        """
        if exp_diff_time_value is None and exp_diff_time_margin_factor is None:
            exp_diff_time_margin_factor = timedelta(minutes=5)

        if exp_diff_time_value is not None and not isinstance(
            exp_diff_time_value, timedelta
        ):
            raise TypeError(exp_diff_time_value)
        if exp_diff_time_margin_factor is not None and not isinstance(
            exp_diff_time_margin_factor, (timedelta, float)
        ):
            raise TypeError(exp_diff_time_margin_factor)

        if not self._energy_consumption_history:
            # The sensor has not been properly initialized
            return 0

        history = list(reversed(self._energy_consumption_history[mode]))

        energy_to_log = 0
        exp_diff_time = None
        est_power = 0

        for prev, curr in zip(history, history[1:]):
            diff_time = curr.datetime - prev.datetime
            diff_energy = self._compute_diff_energy(mode, curr, prev)

            # We remove the energy we've logged since last state update
            # This is to fix an incorrect estimation of the previous exp_diff_time
            if exp_diff_time and est_power > 0:
                # We know that the power will be cut off once the exp_diff_time is
                # surpassed. Note this can result in negative value of energy_to_log
                # when the exp_diff_timehas been over-estimated.
                energy_to_log -= max(est_power, min_power) * (
                    min(exp_diff_time, diff_time).total_seconds() / 3600
                )

            # We expect the consumption to be stable so the next diff_time should be
            # barely the same as the previous one. If we over-estimate this duration,
            # it will result in an irregular power consumption, often going back to 0.
            # If we under-estimate this duration, it will ultimately result in a too
            # smoothed power consumption.  Feel free to fine-tune this variable to fit
            # your needs...
            if exp_diff_time_value is None:
                if prev.first_state:
                    # We skip the first state as we cannot trust its datetime for
                    # exp_diff_time estimation
                    continue
                exp_diff_time = diff_time
            else:
                exp_diff_time = exp_diff_time_value

            # Once we have estimated the next diff_time we can compute the estimated
            # current power
            energy_to_log += diff_energy
            est_power = energy_to_log / (exp_diff_time.total_seconds() / 3600)
            est_power = max(est_power, 0)

            # We add some margins to the exp_diff_time AFTER the est_power computation
            # We prefer having an accurate est_power than an accurate est_energy
            if isinstance(exp_diff_time_margin_factor, timedelta):
                exp_diff_time += exp_diff_time_margin_factor
            if isinstance(exp_diff_time_margin_factor, float):
                exp_diff_time *= 1 + exp_diff_time_margin_factor

            if min_power is not None and est_power > 0:
                est_power = max(est_power, min_power)

        if exp_diff_time and datetime.utcnow() > history[-1].datetime + exp_diff_time:
            # The power estimation was computed for a given duration
            # So if we exceed this duration we should return a zero power
            est_power = 0

        if min_power is not None and est_power > 0:
            est_power = max(est_power, min_power)

        return est_power
