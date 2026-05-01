"""Pydaikin appliance for Daikin AirBase heat pump hot water devices."""

from __future__ import annotations

from datetime import datetime, timezone
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
    MAX_CONCURRENT_REQUESTS = 1

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
    }

    VALUES_SUMMARY = [
        "mode",
        "pow",
        "boost",
        "vacation",
        "vacation_days",
        "boil_level",
        "temp_tank",
        "temp_set",
        "temp_outside",
    ]

    VALUES_TRANSLATION = {
        "pow": "power",
        "temp_set": "target temp",
        "temp_tank": "tank temp",
        "temp_outside": "outside temp",
        "boil_level": "boil level",
        "vacation_days": "vacation days",
    }

    _BOOL_CONTROL_FIELDS = {"pow", "boost", "vacation"}
    _INT_CONTROL_FIELDS = {"boil_level", "vacation_days"}
    _READ_ONLY_FIELDS = {"temp_set", "temp_tank", "temp_outside"}
    _VALID_CONTROL_FIELDS = _BOOL_CONTROL_FIELDS | _INT_CONTROL_FIELDS
    _CONTROL_ALIASES = {
        "power": "pow",
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
        return response

    async def get_status(self) -> dict[str, StatusValue]:
        """Fetch and return typed hot water status data."""
        self.values.invalidate_resource(self.GET_UNIT_INFO)
        await self.update_status(self.HTTP_RESOURCES)
        return {
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

    async def set(self, settings):
        """Set settings on Daikin AirBase hot water device."""
        params = self._normalize_control_params(settings)
        if not params:
            return

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

    @staticmethod
    def _is_missing(value: str | None) -> bool:
        """Return True when a status field is absent or intentionally blank."""
        return value in (None, "", "-")


AirBaseHotWaterDevice = DaikinAirBaseHotWater
