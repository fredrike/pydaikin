"""Pydaikin appliance for Daikin AirBase heat pump hot water devices."""

from __future__ import annotations

from datetime import datetime, time, timezone
import logging
import re
from typing import Any, Optional

from aiohttp import ClientSession

from .daikin_base import Appliance
from .exceptions import DaikinException

_LOGGER = logging.getLogger(__name__)

StatusValue = bool | int | float | str | None


class AirBaseHotWaterError(DaikinException):
    """Daikin AirBase hot water base exception."""


class AirBaseHotWaterResponseError(AirBaseHotWaterError):
    """Raised when the AirBase hot water device returns an invalid response."""


class DaikinAirBaseHotWater(Appliance):  # pylint: disable=too-many-public-methods
    """Daikin class for AirBase heat pump hot water devices.

    These controllers use the BRP15B61/AirBase-style local API: HTTP on port 80,
    no SkyFi password, and paths under ``/skyfi``.
    """

    GET_UNIT_INFO = "skyfi/hotwater/get_unit_info"
    SET_CONTROL_INFO = "skyfi/hotwater/set_control_info"

    HTTP_RESOURCES = [GET_UNIT_INFO]
    INFO_RESOURCES = HTTP_RESOURCES

    MAX_VACATION_DAYS = 365
    DRIVE_TIME_SLOT_MINUTES = 30
    DRIVE_TIME_SLOTS_PER_DAY = 24 * 60 // DRIVE_TIME_SLOT_MINUTES
    MAX_CONCURRENT_REQUESTS = 1
    PROGRAM_1 = 5
    PROGRAM_1_AND_2 = 6
    PROGRAM_2 = PROGRAM_1_AND_2

    TRANSLATIONS = {
        "pow": {
            "0": "off",
            "1": "on",
        },
        "boost": {
            "0": "off",
            "1": "on",
        },
        "vacation": {
            "0": "off",
            "1": "on",
        },
        "mode": {
            "auto": "auto",
            "manual": "manual",
            "off": "off",
        },
        "drive_p": {
            "1": "set_01",
            "2": "set_02",
            "3": "set_03",
            "4": "set_04",
            "5": "program_1",
            "6": "program_1_and_2",
        },
    }

    VALUES_SUMMARY = [
        "mode",
        "pow",
        "boost",
        "vacation",
        "vacation_days",
        "boil_level",
        "drive_p",
        "temp_tank",
        "temp_set",
        "temp_outside",
        "drive_p1s",
        "drive_p1e",
        "drive_p2s",
        "drive_p2e",
    ]

    VALUES_TRANSLATION = {
        "pow": "power",
        "temp_set": "target temp",
        "temp_tank": "tank temp",
        "temp_outside": "outside temp",
        "boil_level": "boil level",
        "vacation_days": "vacation days",
        "drive_p": "drive program",
        "drive_p1s": "program 1 start",
        "drive_p1e": "program 1 end",
        "drive_p2s": "program 2 start",
        "drive_p2e": "program 2 end",
    }

    _DRIVE_PROGRAM_ALIASES = {
        "set_01": 1,
        "set_1": 1,
        "set01": 1,
        "set1": 1,
        "set_02": 2,
        "set_2": 2,
        "set02": 2,
        "set2": 2,
        "set_03": 3,
        "set_3": 3,
        "set03": 3,
        "set3": 3,
        "set_04": 4,
        "set_4": 4,
        "set04": 4,
        "set4": 4,
        "program_1": PROGRAM_1,
        "program1": PROGRAM_1,
        "prog_1": PROGRAM_1,
        "prog1": PROGRAM_1,
        "drive_p1": PROGRAM_1,
        "program_1_and_2": PROGRAM_1_AND_2,
        "programs_1_and_2": PROGRAM_1_AND_2,
        "program_1_2": PROGRAM_1_AND_2,
        "programs_1_2": PROGRAM_1_AND_2,
        "prog_1_and_2": PROGRAM_1_AND_2,
        "progs_1_and_2": PROGRAM_1_AND_2,
        "prog_1_2": PROGRAM_1_AND_2,
        "progs_1_2": PROGRAM_1_AND_2,
        "drive_p1_p2": PROGRAM_1_AND_2,
        "program_2": PROGRAM_1_AND_2,
        "program2": PROGRAM_1_AND_2,
        "prog_2": PROGRAM_1_AND_2,
        "prog2": PROGRAM_1_AND_2,
        "drive_p2": PROGRAM_1_AND_2,
    }
    _DRIVE_PROGRAM_FIELD = "drive_p"
    _DRIVE_TIME_FIELDS = {"drive_p1s", "drive_p1e", "drive_p2s", "drive_p2e"}
    _DRIVE_TIME_STATUS_FIELDS = {
        "drive_p1s": "program_1_start",
        "drive_p1e": "program_1_end",
        "drive_p2s": "program_2_start",
        "drive_p2e": "program_2_end",
    }
    _BOOL_CONTROL_FIELDS = {"pow", "boost", "vacation"}
    _INT_CONTROL_FIELDS = {
        "boil_level",
        "vacation_days",
        _DRIVE_PROGRAM_FIELD,
    } | _DRIVE_TIME_FIELDS
    _READ_ONLY_FIELDS = {"temp_set", "temp_tank", "temp_outside"}
    _VALID_CONTROL_FIELDS = _BOOL_CONTROL_FIELDS | _INT_CONTROL_FIELDS
    _CONTROL_ALIASES = {
        "power": "pow",
        "drive_program": "drive_p",
        "drive_program_selection": "drive_p",
        "program1_start": "drive_p1s",
        "program1_end": "drive_p1e",
        "program2_start": "drive_p2s",
        "program2_end": "drive_p2e",
        "program_1_start": "drive_p1s",
        "program_1_end": "drive_p1e",
        "program_2_start": "drive_p2s",
        "program_2_end": "drive_p2e",
        "drive_program_1_start": "drive_p1s",
        "drive_program_1_end": "drive_p1e",
        "drive_program_2_start": "drive_p2s",
        "drive_program_2_end": "drive_p2e",
    }

    def __init__(
        self,
        device_id: str,
        session: ClientSession | None = None,
    ) -> None:
        """Init Daikin AirBase heat pump hot water device."""
        super().__init__(device_id, session)

    async def init(self):
        """Init status."""
        if not self.values:
            await self.update_status(self.HTTP_RESOURCES)
        if not self.values:
            raise DaikinException("Empty values.")

    @staticmethod
    def parse_response(response_body):
        """Parse response from the AirBase hot water API."""
        _LOGGER.debug("Parsing %s", response_body)
        response = dict(
            (match.group(1), match.group(2))
            for match in re.finditer(r"(\w+)=([^=]*)(?:,|$)", response_body)
        )
        if "ret" not in response:
            raise AirBaseHotWaterResponseError("missing 'ret' field in response")
        ret = response.pop("ret")
        if ret != "OK":
            raise AirBaseHotWaterResponseError(f"ret={ret!r}")
        boil_level = response.get("boil_level")
        if boil_level is not None:
            try:
                DaikinAirBaseHotWater._validate_int_range(
                    "boil_level", boil_level, minimum=0, maximum=6
                )
            except ValueError as exc:
                raise AirBaseHotWaterResponseError(str(exc)) from exc
            response["mode"] = "auto" if boil_level == "0" else "manual"
        drive_program = response.get("drive_p")
        if drive_program is not None:
            try:
                DaikinAirBaseHotWater._normalize_drive_program(drive_program)
            except ValueError as exc:
                raise AirBaseHotWaterResponseError(str(exc)) from exc
        for key in DaikinAirBaseHotWater._DRIVE_TIME_FIELDS:
            drive_time = response.get(key)
            if not DaikinAirBaseHotWater._is_missing(drive_time):
                try:
                    DaikinAirBaseHotWater._validate_drive_time_slot(key, drive_time)
                except ValueError as exc:
                    raise AirBaseHotWaterResponseError(str(exc)) from exc
        return response

    async def get_status(self) -> dict[str, StatusValue]:
        """Fetch and return typed hot water status data."""
        self.values.invalidate_resource(self.GET_UNIT_INFO)
        await self.update_status(self.HTTP_RESOURCES)
        drive_program_value = self._to_drive_program_value(
            self.values.get("drive_p", invalidate=False)
        )
        status: dict[str, StatusValue] = {
            "power": self._to_bool(self.values.get("pow", invalidate=False), "pow"),
            "boost": self._to_bool(self.values.get("boost", invalidate=False), "boost"),
            "vacation": self._to_bool(
                self.values.get("vacation", invalidate=False), "vacation"
            ),
            "vacation_days": self._to_int(
                self.values.get("vacation_days", invalidate=False), "vacation_days"
            ),
            "boil_level": self._to_int(
                self.values.get("boil_level", invalidate=False), "boil_level"
            ),
            "drive_p": drive_program_value,
            "drive_program": self._drive_program_label(drive_program_value),
            "set_program": self._drive_set_program(drive_program_value),
            "manual_program_1": self._manual_program_1_enabled(drive_program_value),
            "manual_program_2": self._manual_program_2_enabled(drive_program_value),
            "mode": self.represent("mode")[1] if "mode" in self.values else None,
            "temp_set": self._to_float(
                self.values.get("temp_set", invalidate=False), "temp_set"
            ),
            "temp_tank": self._to_float(
                self.values.get("temp_tank", invalidate=False), "temp_tank"
            ),
            "temp_outside": self._to_float(
                self.values.get("temp_outside", invalidate=False), "temp_outside"
            ),
        }
        for source, target in self._DRIVE_TIME_STATUS_FIELDS.items():
            raw_value = self.values.get(source, invalidate=False)
            status[source] = self._to_drive_time_slot(raw_value, source)
            status[target] = self._to_drive_time(raw_value, source)
        return status

    async def set(self, settings):
        """Set settings on Daikin AirBase hot water device."""
        params = self._normalize_control_params(settings)
        if not params:
            return
        self._validate_drive_program_selection(params)

        _LOGGER.debug(
            "Sending request to %s with params: %s", self.SET_CONTROL_INFO, params
        )
        await self._get_resource(self.SET_CONTROL_INFO, params)
        self.values.update_by_resource(self.GET_UNIT_INFO, params)
        if "boil_level" in params:
            self.values["mode"] = "auto" if params["boil_level"] == "0" else "manual"

    async def set_holiday(self, mode):
        """Set holiday mode."""

    async def set_advanced_mode(self, mode, value):
        """Set advanced mode."""

    async def set_streamer(self, mode):
        """Set streamer mode."""

    async def set_control(self, **kwargs: Any) -> None:
        """Set writable hot water control parameters."""
        await self.set(kwargs)

    async def set_boil_level(self, level: int) -> None:
        """Set boil level, where 0 is auto and 1-6 are manual levels."""
        await self.set({"boil_level": level})

    async def set_mode_auto(self) -> None:
        """Set automatic boil mode."""
        await self.set({"mode": "auto"})

    async def set_mode_manual(self, level: int) -> None:
        """Set manual boil mode level from 1 to 6."""
        level = self._validate_int_range(
            "manual boil level", level, minimum=1, maximum=6
        )
        await self.set({"mode": "manual", "boil_level": level})

    async def set_boost(self, mode) -> None:
        """Turn boost mode on or off."""
        await self.set({"boost": mode})

    async def set_vacation(self, mode) -> None:
        """Turn vacation mode on or off."""
        await self.set({"vacation": mode})

    async def set_vacation_days(self, days: int) -> None:
        """Set vacation days from 0 to MAX_VACATION_DAYS."""
        await self.set({"vacation_days": days})

    async def set_power(self, mode) -> None:
        """Turn the hot water system on or off."""
        await self.set({"pow": mode})

    async def set_drive_program_selection(self, program: Any) -> None:
        """Set the active drive program.

        ``program_1_and_2`` enables both manually configured programs. Program 2
        cannot be active by itself.
        """
        await self.set({"drive_p": program})

    async def set_drive_set_program(self, program: int) -> None:
        """Set one of the mutually exclusive fixed drive programs 1-4."""
        program = self._validate_int_range("set program", program, minimum=1, maximum=4)
        await self.set_drive_program_selection(program)

    async def set_drive_program(self, program: int, start: Any, end: Any) -> None:
        """Set a drive program start and end time.

        Args:
            program: Drive program number, either 1 or 2.
            start: Start time as a 0-47 half-hour slot or HH:MM string.
            end: End time as a 0-47 half-hour slot or HH:MM string.
        """
        if program == 1:
            await self.set({"drive_p1s": start, "drive_p1e": end})
        elif program == 2:
            await self.set({"drive_p2s": start, "drive_p2e": end})
        else:
            raise ValueError("drive program must be 1 or 2")

    async def set_drive_program_1(self, start: Any, end: Any) -> None:
        """Set drive program 1 start and end time."""
        await self.set_drive_program(1, start, end)

    async def set_drive_program_2(self, start: Any, end: Any) -> None:
        """Set drive program 2 start and end time."""
        await self.set_drive_program(2, start, end)

    async def set_zone(self, zone_id, key, value):
        """Set zone status."""

    @property
    def support_away_mode(self):
        """Return False as hot water vacation mode is separate from away mode."""
        return False

    @property
    def support_fan_rate(self):
        """Return False as hot water devices do not have a fan setting."""
        return False

    @property
    def support_swing_mode(self):
        """Return False as hot water devices do not have swing modes."""
        return False

    @property
    def support_humidity(self) -> bool:
        """Return False as hot water devices do not have a humidity sensor."""
        return False

    @property
    def humidity(self) -> Optional[float]:
        """Return None as hot water devices do not have a humidity sensor."""
        return None

    @property
    def support_outside_temperature(self):
        """Return True if the device reports an outside temperature."""
        return "temp_outside" in self.values and self.values["temp_outside"] != "-"

    @property
    def outside_temperature(self) -> Optional[float]:
        """Return current outside temperature."""
        return self._parse_number("temp_outside")

    @property
    def inside_temperature(self) -> Optional[float]:
        """Return current tank temperature for sensor compatibility."""
        return self._parse_number("temp_tank")

    @property
    def tank_temperature(self) -> Optional[float]:
        """Return current hot water tank temperature."""
        return self._parse_number("temp_tank")

    @property
    def target_temperature(self) -> Optional[float]:
        """Return current hot water target temperature."""
        return self._parse_number("temp_set")

    def represent(self, key):
        """Return translated value from key."""
        if key in self._DRIVE_TIME_FIELDS:
            k = self.VALUES_TRANSLATION.get(key, key)
            return (k, self._to_drive_time(self.values.get(key), key))
        return super().represent(key)

    def _validate_drive_program_selection(self, params: dict[str, str]) -> None:
        """Validate program 2 is only selected after program 1 is active."""
        if params.get("drive_p") != str(self.PROGRAM_1_AND_2):
            return

        current_program = self.values.get("drive_p", invalidate=False)
        if current_program is None:
            return
        if current_program not in {str(self.PROGRAM_1), str(self.PROGRAM_1_AND_2)}:
            raise ValueError("program_1_and_2 requires program_1 to be selected first")

    def show_sensors(self):
        """Print hot water sensors."""
        data = [
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        ]
        if self.tank_temperature is not None:
            data.append(f"tank_temp={self.tank_temperature:.0f}°C")
        if self.target_temperature is not None:
            data.append(f"target_temp={self.target_temperature:.0f}°C")
        if self.support_outside_temperature and self.outside_temperature is not None:
            data.append(f"out_temp={self.outside_temperature:.0f}°C")
        print("  ".join(data))

    def log_sensors(self, file):
        """Log hot water sensors to a file."""
        data = [
            ("datetime", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")),
            ("tank_temp", self.tank_temperature),
            ("target_temp", self.target_temperature),
        ]
        if self.support_outside_temperature:
            data.append(("out_temp", self.outside_temperature))
        if file.tell() == 0:
            file.write(",".join(k for k, _ in data))
            file.write("\n")
        file.write(",".join(str(v) for _, v in data))
        file.write("\n")
        file.flush()

    @classmethod
    def _normalize_control_params(cls, params: dict[str, Any]) -> dict[str, str]:
        """Validate and convert control parameters for the device API."""
        normalized: dict[str, str] = {}

        params = {
            cls._CONTROL_ALIASES.get(key, key): value for key, value in params.items()
        }

        mode = params.pop("mode", None)
        if mode is not None:
            cls._normalize_mode(mode, params, normalized)

        for key, value in params.items():
            if key in cls._READ_ONLY_FIELDS:
                raise ValueError(f"{key} is read-only and cannot be set")
            if key not in cls._VALID_CONTROL_FIELDS:
                raise ValueError(f"Unsupported control parameter: {key}")

            if key in cls._BOOL_CONTROL_FIELDS:
                normalized[key] = cls._normalize_bool_control(key, value)
            elif key == "boil_level":
                normalized[key] = str(
                    cls._validate_int_range(key, value, minimum=0, maximum=6)
                )
            elif key == "vacation_days":
                normalized[key] = str(
                    cls._validate_int_range(
                        key,
                        value,
                        minimum=0,
                        maximum=cls.MAX_VACATION_DAYS,
                    )
                )
            elif key == cls._DRIVE_PROGRAM_FIELD:
                normalized[key] = str(cls._normalize_drive_program(value))
            elif key in cls._DRIVE_TIME_FIELDS:
                normalized[key] = str(cls._normalize_drive_time(key, value))

        return normalized

    @classmethod
    def _normalize_mode(
        cls,
        mode: Any,
        params: dict[str, Any],
        normalized: dict[str, str],
    ) -> None:
        """Normalize mode into writable hot water controls."""
        if mode == "off":
            normalized["pow"] = "0"
        elif mode == "auto":
            if "boil_level" in params:
                boil_level = cls._validate_int_range(
                    "boil_level", params["boil_level"], minimum=0, maximum=6
                )
                if boil_level != 0:
                    raise ValueError("auto mode requires boil_level 0")
                params.pop("boil_level")
            normalized["pow"] = "1"
            normalized["boil_level"] = "0"
        elif mode == "manual":
            if "boil_level" not in params:
                raise ValueError("manual mode requires boil_level")
            normalized["pow"] = "1"
        else:
            raise ValueError(f"Unsupported mode for AirBase hot water: {mode}")

    @staticmethod
    def _normalize_bool_control(key: str, value: Any) -> str:
        """Normalize a bool-like control value to 0 or 1."""
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, int) and value in (0, 1):
            return str(value)
        if isinstance(value, str):
            if value in {"0", "1"}:
                return value
            if value in {"off", "on"}:
                return "1" if value == "on" else "0"
        raise ValueError(f"{key} must be a boolean or 0/1")

    @staticmethod
    def _validate_int_range(
        key: str,
        value: Any,
        *,
        minimum: int,
        maximum: int,
    ) -> int:
        """Validate an integer falls inside an inclusive range."""
        if isinstance(value, bool):
            raise ValueError(f"{key} must be an integer")

        try:
            int_value = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be an integer") from exc

        if int_value < minimum or int_value > maximum:
            raise ValueError(f"{key} must be between {minimum} and {maximum}")
        return int_value

    @classmethod
    def _normalize_drive_time(cls, key: str, value: Any) -> int:
        """Normalize a drive program time to a half-hour slot."""
        if isinstance(value, time):
            return cls._time_parts_to_drive_slot(key, value.hour, value.minute)
        if isinstance(value, str):
            if re.fullmatch(r"\d+", value):
                return cls._validate_drive_time_slot(key, value)
            match = re.fullmatch(r"(\d{1,2}):(\d{2})", value)
            if match:
                return cls._time_parts_to_drive_slot(
                    key,
                    int(match.group(1)),
                    int(match.group(2)),
                )
            raise ValueError(f"{key} must be a 0-47 slot or HH:MM time")
        return cls._validate_drive_time_slot(key, value)

    @classmethod
    def _validate_drive_time_slot(cls, key: str, value: Any) -> int:
        """Validate a drive program time slot."""
        return cls._validate_int_range(
            key, value, minimum=0, maximum=cls.DRIVE_TIME_SLOTS_PER_DAY - 1
        )

    @classmethod
    def _normalize_drive_program(cls, value: Any) -> int:
        """Normalize a drive program selector to its API value."""
        if isinstance(value, str):
            normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
            if normalized in cls._DRIVE_PROGRAM_ALIASES:
                return cls._DRIVE_PROGRAM_ALIASES[normalized]
        return cls._validate_int_range("drive_p", value, minimum=1, maximum=6)

    @classmethod
    def _time_parts_to_drive_slot(cls, key: str, hour: int, minute: int) -> int:
        """Convert HH:MM parts to a half-hour drive time slot."""
        if hour < 0 or hour > 23:
            raise ValueError(f"{key} hour must be between 0 and 23")
        if minute % cls.DRIVE_TIME_SLOT_MINUTES != 0 or minute < 0 or minute > 59:
            raise ValueError(f"{key} must use 30 minute increments")
        return (hour * 60 + minute) // cls.DRIVE_TIME_SLOT_MINUTES

    @classmethod
    def _drive_time_slot_to_time(cls, value: Any, key: str) -> str:
        """Convert a half-hour drive time slot to HH:MM."""
        slot = cls._validate_drive_time_slot(key, value)
        minutes = slot * cls.DRIVE_TIME_SLOT_MINUTES
        hour, minute = divmod(minutes, 60)
        return f"{hour:02d}:{minute:02d}"

    @classmethod
    def _to_bool(cls, value: str | None, key: str) -> bool | None:
        """Convert a 0/1 status value to bool."""
        if cls._is_missing(value):
            return None
        if value == "1":
            return True
        if value == "0":
            return False
        raise AirBaseHotWaterResponseError(f"{key} must be 0 or 1, got {value!r}")

    @classmethod
    def _to_int(cls, value: str | None, key: str) -> int | None:
        """Convert a status value to int."""
        if cls._is_missing(value):
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise AirBaseHotWaterResponseError(
                f"{key} must be an integer, got {value!r}"
            ) from exc

    @classmethod
    def _to_float(cls, value: str | None, key: str) -> float | None:
        """Convert a status value to float."""
        if cls._is_missing(value):
            return None
        try:
            return float(value)
        except ValueError as exc:
            raise AirBaseHotWaterResponseError(
                f"{key} must be a float, got {value!r}"
            ) from exc

    @classmethod
    def _to_drive_time_slot(cls, value: str | None, key: str) -> int | None:
        """Convert a status drive program time to its raw half-hour slot."""
        if cls._is_missing(value):
            return None
        try:
            return cls._validate_drive_time_slot(key, value)
        except ValueError as exc:
            raise AirBaseHotWaterResponseError(str(exc)) from exc

    @classmethod
    def _to_drive_time(cls, value: str | None, key: str) -> str | None:
        """Convert a status drive program time to HH:MM."""
        if cls._is_missing(value):
            return None
        try:
            return cls._drive_time_slot_to_time(value, key)
        except ValueError as exc:
            raise AirBaseHotWaterResponseError(str(exc)) from exc

    @classmethod
    def _to_drive_program_value(cls, value: str | None) -> int | None:
        """Convert a status drive program selector to its raw value."""
        if cls._is_missing(value):
            return None
        try:
            return cls._normalize_drive_program(value)
        except ValueError as exc:
            raise AirBaseHotWaterResponseError(str(exc)) from exc

    @classmethod
    def _to_drive_program(cls, value: str | None) -> str | None:
        """Convert a status drive program selector to its generic label."""
        if cls._is_missing(value):
            return None
        raw_value = cls._to_drive_program_value(value)
        return cls._drive_program_label(raw_value)

    @classmethod
    def _drive_program_label(cls, raw_value: int | None) -> str | None:
        """Return the generic label for a drive program selector."""
        if raw_value is None:
            return None
        return cls.daikin_to_human("drive_p", str(raw_value))

    @classmethod
    def _drive_set_program(cls, raw_value: int | None) -> int | None:
        """Return selected fixed set program number, if any."""
        if raw_value is None or raw_value > 4:
            return None
        return raw_value

    @classmethod
    def _manual_program_1_enabled(cls, raw_value: int | None) -> bool | None:
        """Return whether manual program 1 is selected."""
        if raw_value is None:
            return None
        return raw_value in {cls.PROGRAM_1, cls.PROGRAM_1_AND_2}

    @classmethod
    def _manual_program_2_enabled(cls, raw_value: int | None) -> bool | None:
        """Return whether manual program 2 is selected."""
        if raw_value is None:
            return None
        return raw_value == cls.PROGRAM_1_AND_2

    @staticmethod
    def _is_missing(value: str | None) -> bool:
        """Return True when a status field is absent or intentionally blank."""
        return value in (None, "", "-")


AirBaseHotWaterDevice = DaikinAirBaseHotWater
