"""Pydaikin appliance, represent a Daikin BRP device with firmware 2.8.0."""

from dataclasses import dataclass, field
import json
import logging
from typing import Any, Dict, List, Optional

from aiohttp import ClientSession

from .daikin_base import Appliance
from .exceptions import DaikinException

_LOGGER = logging.getLogger(__name__)


@dataclass
class DaikinAttribute:
    """Represent a Daikin attribute for firmware 2.8.0."""

    name: str
    value: Any
    path: List[str]
    to: str

    def format(self) -> Dict:
        """Format the attribute for the API request."""
        return {"pn": self.name, "pv": self.value}


@dataclass
class DaikinRequest:
    """Represent a Daikin request for firmware 2.8.0."""

    attributes: List[DaikinAttribute] = field(default_factory=list)

    def serialize(self, payload=None) -> Dict:
        """Serialize the request to JSON payload."""
        if payload is None:
            payload = {'requests': []}

        def get_existing_index(name: str, children: List[Dict]) -> int:
            for index, child in enumerate(children):
                if child.get("pn") == name:
                    return index
            return -1

        def get_existing_to(to: str, requests: List[Dict]) -> Optional[Dict]:
            for request in requests:
                this_to = request.get("to")
                if this_to == to:
                    return request
            return None

        for attribute in self.attributes:
            to = get_existing_to(attribute.to, payload['requests'])
            if to is None:
                payload['requests'].append(
                    {'op': 3, 'pc': {"pn": "dgc_status", "pch": []}, "to": attribute.to}
                )
                to = payload['requests'][-1]
            entry = to['pc']['pch']
            for pn in attribute.path:
                index = get_existing_index(pn, entry)
                if index == -1:
                    entry.append({"pn": pn, "pch": []})
                entry = entry[-1]['pch']
            entry.append(attribute.format())
        return payload


# pylint: disable=abstract-method,too-many-public-methods
class DaikinBRP084(Appliance):
    """Daikin class for BRP devices with firmware 2.8.0."""

    # Centralized API paths for easier maintenance and better organization
    E_1002_PATH = [
        "/dsiot/edge/adr_0100.dgc_status",
        "dgc_status",
        "e_1002",
    ]
    E_1002_E_3001_PATH = E_1002_PATH + ["e_3001"]
    E_1002_E_3003_PATH = E_1002_PATH + ["e_3003"]
    E_1003_PATH = [
        "/dsiot/edge/adr_0200.dgc_status",
        "dgc_status",
        "e_1003",
    ]
    ADP_I_PATH = ["/dsiot/edge.adp_i", "adp_i"]

    API_PATHS = {
        # Basic paths
        "power": E_1002_PATH + ["e_A002", "p_01"],
        "mode": E_1002_PATH + ["e_3001", "p_01"],
        "indoor_temp": E_1002_PATH + ["e_A00B", "p_01"],
        "indoor_humidity": E_1002_PATH + ["e_A00B", "p_02"],
        "outdoor_temp": [
            "/dsiot/edge/adr_0200.dgc_status",
            "dgc_status",
            "e_1003",
            "e_A00D",
            "p_01",
        ],
        "mac_address": ADP_I_PATH + ["mac"],
        # Adapter info / capability flags
        "firmware_ver": ADP_I_PATH + ["ver"],
        "api_ver": ADP_I_PATH + ["api_ver"],
        # Comfort airflow (e_3003/p_1D): 00=off, 01=on
        "comfort": E_1002_E_3003_PATH + ["p_1D"],
        # Econo (e_3003/p_24): 00=off, 01=on. Verified live read+write.
        "econo": E_1002_E_3003_PATH + ["p_24"],
        # Outdoor unit quiet (outdoor e_3002/p_3D): 00=off, 01=on.
        "outdoor_quiet": E_1003_PATH + ["e_3002", "p_3D"],
        # Powerful (outdoor e_3002/p_44): 00=off, 01=on. Verified live
        # read+write; the unit also auto-cancels after ~20 min.
        "powerful": E_1003_PATH + ["e_3002", "p_44"],
        # Outdoor unit sensors (read-only)
        "compressor_temp": E_1003_PATH + ["e_A005", "p_01"],
        "discharge_temp": E_1003_PATH + ["e_A005", "p_02"],
        "indoor_model": E_1002_PATH + ["e_A001", "p_01"],
        "outdoor_model": E_1003_PATH + ["e_A001", "p_01"],
        # Mode-specific paths for temperature settings
        "temp_settings": {
            "cool": E_1002_E_3001_PATH + ["p_02"],
            "heat": E_1002_E_3001_PATH + ["p_03"],
            "auto": E_1002_E_3001_PATH + ["p_1D"],
        },
        # Fan settings organized by mode
        "fan_settings": {
            "auto": E_1002_E_3001_PATH + ["p_26"],
            "cool": E_1002_E_3001_PATH + ["p_09"],
            "heat": E_1002_E_3001_PATH + ["p_0A"],
            "fan": E_1002_E_3001_PATH + ["p_28"],
        },
        # Swing settings organized by mode
        "swing_settings": {
            "auto": {
                "vertical": E_1002_E_3001_PATH + ["p_20"],
                "horizontal": E_1002_E_3001_PATH + ["p_21"],
            },
            "cool": {
                "vertical": E_1002_E_3001_PATH + ["p_05"],
                "horizontal": E_1002_E_3001_PATH + ["p_06"],
            },
            "heat": {
                "vertical": E_1002_E_3001_PATH + ["p_07"],
                "horizontal": E_1002_E_3001_PATH + ["p_08"],
            },
            "fan": {
                "vertical": E_1002_E_3001_PATH + ["p_24"],
                "horizontal": E_1002_E_3001_PATH + ["p_25"],
            },
            "dry": {
                "vertical": E_1002_E_3001_PATH + ["p_22"],
                "horizontal": E_1002_E_3001_PATH + ["p_23"],
            },
        },
        # Energy data
        "energy": {
            "today_runtime": [
                "/dsiot/edge/adr_0100.i_power.week_power",
                "week_power",
                "today_runtime",
            ],
            "weekly_data": [
                "/dsiot/edge/adr_0100.i_power.week_power",
                "week_power",
                "datas",
            ],
        },
    }

    TRANSLATIONS = {
        'mode': {
            '0300': 'auto',
            '0200': 'cool',
            '0100': 'heat',
            '0000': 'fan',
            '0500': 'dry',
            '00': 'off',
            '01': 'on',
        },
        'f_rate': {
            '0A00': 'auto',
            '0B00': 'quiet',
            '0300': '1',
            '0400': '2',
            '0500': '3',
            '0600': '4',
            '0700': '5',
        },
        'f_dir': {
            'off': 'off',
            'vertical': 'vertical',
            'horizontal': 'horizontal',
            'both': '3d',
        },
        'en_hol': {
            '0': 'off',
            '1': 'on',
        },
        'comfort': {
            '00': 'off',
            '01': 'on',
        },
        'econo': {
            '00': 'off',
            '01': 'on',
        },
        'outdoor_quiet': {
            '00': 'off',
            '01': 'on',
        },
        'powerful': {
            '00': 'off',
            '01': 'on',
        },
    }

    # Discrete vertical vane states. Only byte-0 has physical effect on this
    # firmware (verified live): 'off'=neutral, 'swing'=oscillate, 'down'=floor.
    # There is no continuous angle and no distinct "up" preset over wifi -
    # byte-1 is accepted but inert, so 00800000 ("up") is NOT included.
    VERTICAL_VANE_MAP = {
        '00000000': 'off',
        '17000000': 'down',
        '0F000000': 'swing',
    }
    REVERSE_VERTICAL_VANE_MAP = {v: k for k, v in VERTICAL_VANE_MAP.items()}

    # Mapping between the values from firmware 2.8.0 to traditional API values
    MODE_MAP = {
        '0300': 'auto',
        '0200': 'cool',
        '0100': 'heat',
        '0000': 'fan',
        '0500': 'dry',
    }

    FAN_MODE_MAP = {
        '0A00': 'auto',
        '0B00': 'quiet',
        '0300': '1',
        '0400': '2',
        '0500': '3',
        '0600': '4',
        '0700': '5',
    }

    # These mappings are now handled by the API_PATHS dictionary

    # The values for turning swing axis on/off
    TURN_OFF_SWING_AXIS = "000000"
    TURN_ON_SWING_AXIS = "0F0000"

    REVERSE_MODE_MAP = {v: k for k, v in MODE_MAP.items()}
    REVERSE_FAN_MODE_MAP = {v: k for k, v in FAN_MODE_MAP.items()}

    # On/off feature toggles handled together (share mutual-exclusion rules).
    POWER_TOGGLES = ('comfort', 'econo', 'outdoor_quiet', 'powerful')

    INFO_RESOURCES = []

    def get_path(self, *keys):
        """Get API path from the nested dictionary structure.

        Args:
            *keys: Variable length list of keys to navigate the API_PATHS dictionary.
                  For example: "temp_settings", "cool" would return the path for
                  cool mode temperature.

        Returns:
            List of path components to use with find_value_by_pn.

        Raises:
            DaikinException: If the path is not found in the API_PATHS dictionary.
        """
        current = self.API_PATHS
        for key in keys:
            if key not in current:
                raise DaikinException(f"Path key {key} not found")
            current = current[key]
        return current

    def __init__(self, device_id, session: Optional[ClientSession] = None) -> None:
        """Initialize the Daikin appliance for firmware 2.8.0."""
        super().__init__(device_id, session)
        self.url = f"{self.base_url}/dsiot/multireq"

    @staticmethod
    def hex_to_temp(value: str, divisor=2) -> float:
        """Convert hexadecimal temperature to float."""
        return int(value[:2], 16) / divisor

    @staticmethod
    def temp_to_hex(temperature: float, divisor=2) -> str:
        """Convert temperature to hexadecimal."""
        return format(int(temperature * divisor), '02x')

    @staticmethod
    def hex_to_int(value: str) -> int:
        """Convert hexadecimal string to integer."""
        return int(value, 16)

    @staticmethod
    def hex_le_to_int(value: str, signed: bool = False) -> int:
        """Convert a little-endian hex string (byte pairs) to an integer.

        Multi-byte dgc_status values (e.g. outdoor temperature ``0D00`` or
        compressor temperature ``8C0000``) are little-endian. Reading only the
        first byte breaks for values that spill into the second byte or that are
        negative (two's complement), e.g. a sub-zero outdoor temperature.
        """
        raw = bytes.fromhex(value)
        return int.from_bytes(raw, byteorder='little', signed=signed)

    @classmethod
    def hex_le_to_temp(cls, value: str, divisor=2) -> float:
        """Convert a little-endian signed hex temperature to degrees Celsius."""
        return cls.hex_le_to_int(value, signed=True) / divisor

    @staticmethod
    def hex_to_ascii(value: str) -> str:
        """Decode a hex-encoded ASCII string (model/serial), trimming padding."""
        try:
            return bytes.fromhex(value).decode('ascii').strip()
        except (ValueError, UnicodeDecodeError):
            return value

    @staticmethod
    def find_value_by_pn(data: dict, fr: str, *keys):
        """Find values in nested response data."""
        data = [x['pc'] for x in data['responses'] if x['fr'] == fr]

        while keys:
            current_key = keys[0]
            keys = keys[1:]
            found = False
            for pcs in data:
                if pcs['pn'] == current_key:
                    if not keys:
                        return pcs['pv']
                    data = pcs['pch']
                    found = True
                    break
            if not found:
                raise DaikinException(f'Key {current_key} not found')
        return None

    def get_swing_state(self, data: dict) -> str:
        """Get the current swing state from response data."""
        mode = self.values.get('mode', invalidate=False)
        if (
            mode is not None
            and mode != 'off'
            and mode in self.API_PATHS["swing_settings"]
        ):
            try:
                vertical = "F" in self.find_value_by_pn(
                    data, *self.get_path("swing_settings", mode, "vertical")
                )
                horizontal = "F" in self.find_value_by_pn(
                    data, *self.get_path("swing_settings", mode, "horizontal")
                )

                if horizontal and vertical:
                    return 'both'
                if horizontal:
                    return 'horizontal'
                if vertical:
                    return 'vertical'
            except DaikinException:
                pass  # Keep default 'off'

        return 'off'  # Default return value

    async def init(self):
        """Initialize the device and fetch initial state."""
        # Only update if values haven't been populated yet (e.g., by factory detection)
        if not self.values:
            await self.update_status()

    async def update_status(self, resources=None):
        """Update device status."""
        payload = {
            "requests": [
                {"op": 2, "to": "/dsiot/edge/adr_0100.dgc_status?filter=pv,pt,md"},
                {"op": 2, "to": "/dsiot/edge/adr_0200.dgc_status?filter=pv,pt,md"},
                {
                    "op": 2,
                    "to": "/dsiot/edge/adr_0100.i_power.week_power?filter=pv,pt,md",
                },
                {"op": 2, "to": "/dsiot/edge.adp_i"},
            ]
        }

        try:
            response = await self._get_resource("", params=payload)

            if not response or 'responses' not in response:
                raise DaikinException("Invalid response from device")
        except Exception as e:
            _LOGGER.info("Error communicating with device: %s", e)
            raise DaikinException(f"Failed to communicate with device: {e}") from e

        # Extract basic info
        try:
            # Get MAC address
            mac = self.find_value_by_pn(response, *self.get_path("mac_address"))
            self.values['mac'] = mac

            # Get power state
            is_off = self.find_value_by_pn(response, *self.get_path("power")) == "00"

            # Get mode
            mode_value = self.find_value_by_pn(response, *self.get_path("mode"))

            self.values['pow'] = "0" if is_off else "1"
            self.values['mode'] = 'off' if is_off else self.MODE_MAP[mode_value]

            # Get temperatures. Outdoor temp is a little-endian signed 2-byte
            # value, so it must be decoded as such to handle sub-zero readings.
            self.values['otemp'] = str(
                self.hex_le_to_temp(
                    self.find_value_by_pn(response, *self.get_path("outdoor_temp"))
                )
            )

            self.values['htemp'] = str(
                self.hex_to_temp(
                    self.find_value_by_pn(response, *self.get_path("indoor_temp")),
                    divisor=1,
                )
            )

            # Get humidity
            try:
                self.values['hhum'] = str(
                    self.hex_to_int(
                        self.find_value_by_pn(
                            response, *self.get_path("indoor_humidity")
                        )
                    )
                )
            except DaikinException:
                self.values['hhum'] = "--"

            # Get target temperature
            if self.values['mode'] in self.API_PATHS["temp_settings"]:
                self.values['stemp'] = str(
                    self.hex_to_temp(
                        self.find_value_by_pn(
                            response,
                            *self.get_path("temp_settings", self.values['mode']),
                        )
                    )
                )
            else:
                self.values['stemp'] = "--"

            # Get fan mode
            if self.values['mode'] in self.API_PATHS["fan_settings"]:
                fan_value = self.find_value_by_pn(
                    response, *self.get_path("fan_settings", self.values['mode'])
                )
                self.values['f_rate'] = self.FAN_MODE_MAP.get(fan_value, 'auto')
            else:
                self.values['f_rate'] = 'auto'

            # Get swing mode
            self.values['f_dir'] = self.get_swing_state(response)

            # Optional feature toggles, vane position, capability flags and
            # outdoor sensors (each guarded - not all firmware exposes them).
            self._extract_optional_readings(response)

            # Get energy data
            try:
                self.values['today_runtime'] = self.find_value_by_pn(
                    response, *self.get_path("energy", "today_runtime")
                )

                energy_data = self.find_value_by_pn(
                    response, *self.get_path("energy", "weekly_data")
                )
                if isinstance(energy_data, list) and len(energy_data) > 0:
                    self.values['datas'] = '/'.join(map(str, energy_data))

            except DaikinException:
                pass

        except DaikinException as e:
            _LOGGER.error("Error extracting values: %s", e)
            raise

    def _extract_optional_readings(self, response):
        """Extract optional values that not all firmware/models expose.

        Covers the on/off feature toggles, the active-mode vertical vane
        position, adapter capability/firmware info and outdoor-unit sensors.
        Each read is guarded individually so a missing container just leaves
        that value unset rather than failing the whole status update.
        """
        # On/off feature toggles (comfort/econo/outdoor_quiet/powerful).
        for key in self.POWER_TOGGLES:
            try:
                raw = self.find_value_by_pn(response, *self.get_path(key))
                self.values[key] = self.TRANSLATIONS[key].get(raw, 'off')
            except DaikinException:
                pass

        # Current vertical vane position for the active mode.
        try:
            if self.values['mode'] in self.API_PATHS["swing_settings"]:
                vane_raw = self.find_value_by_pn(
                    response,
                    *self.get_path("swing_settings", self.values['mode'], "vertical"),
                )
                self.values['vane_vertical'] = self.VERTICAL_VANE_MAP.get(
                    vane_raw, 'off'
                )
        except DaikinException:
            pass

        # Adapter capability flags / firmware info.
        for key, path_key in (('ver', 'firmware_ver'), ('api_ver', 'api_ver')):
            try:
                self.values[key] = str(
                    self.find_value_by_pn(response, *self.get_path(path_key))
                )
            except DaikinException:
                pass

        # Outdoor-unit compressor temperature.
        try:
            self.values['cmp_temp'] = str(
                self.hex_le_to_temp(
                    self.find_value_by_pn(response, *self.get_path("compressor_temp"))
                )
            )
        except DaikinException:
            pass

        # Decoded model strings.
        for key, path_key in (
            ('model', 'indoor_model'),
            ('outdoor_model', 'outdoor_model'),
        ):
            try:
                self.values[key] = self.hex_to_ascii(
                    self.find_value_by_pn(response, *self.get_path(path_key))
                )
            except DaikinException:
                pass

    async def _get_resource(self, path: str, params: Optional[Dict] = None):
        """Make the HTTP request to the device."""
        _LOGGER.debug(
            "Calling: %s %s",
            self.url,
            json.dumps(params) if params else "{}",
        )

        try:
            async with self.request_semaphore:
                async with self.session.post(
                    self.url,
                    json=params,
                    headers=self.headers,
                    ssl=self.ssl_context,
                    timeout=5,  # Add a timeout to avoid hanging
                ) as response:
                    response.raise_for_status()
                    return await response.json()
        except Exception as e:
            _LOGGER.debug("Error in _get_resource: %s", e)
            raise

    async def _update_settings(self, settings):
        """Update settings to set on Daikin device."""
        # Start with current values
        _LOGGER.debug("Updating settings: %s", settings)

        # Handle specific translations for this firmware version
        for key, value in settings.items():
            if key == 'mode' and value == 'off':
                self.values['pow'] = '0'
            elif key == 'mode':
                self.values['pow'] = '1'
                self.values['mode'] = value
            else:
                self.values[key] = value

        return self.values

    def add_request(self, requests, path, value):
        """Append DaikinAttribute to requests."""
        requests.append(DaikinAttribute(path[-1], value, path[2:4], path[0]))

    def _handle_power_setting(self, settings, requests):
        """Handle power-related settings."""
        if 'mode' not in settings:
            return

        # Turn off/on
        power_path = self.get_path("power")
        self.add_request(
            requests, power_path, "00" if settings['mode'] == 'off' else "01"
        )

        if settings['mode'] == 'off':
            return

        # Set mode
        mode_value = self.REVERSE_MODE_MAP.get(settings['mode'])
        if mode_value:
            mode_path = self.get_path("mode")
            self.add_request(requests, mode_path, mode_value)

    def _handle_temperature_setting(self, settings, requests):
        """Handle temperature-related settings."""
        if (
            'stemp' not in settings
            or self.values['mode'] not in self.API_PATHS["temp_settings"]
        ):
            return

        path = self.get_path("temp_settings", self.values['mode'])
        temp_hex = self.temp_to_hex(float(settings['stemp']))
        self.add_request(requests, path, temp_hex)

    def _handle_fan_setting(self, settings, requests):
        """Handle fan-related settings."""
        if (
            'f_rate' not in settings
            or self.values['mode'] not in self.API_PATHS["fan_settings"]
        ):
            return

        path = self.get_path("fan_settings", self.values['mode'])
        fan_value = None

        # Try both formats - the internal one and the user-friendly one
        for key, value in self.FAN_MODE_MAP.items():
            if value == settings['f_rate'] or key == settings['f_rate']:
                fan_value = key
                break

        if fan_value:
            self.add_request(requests, path, fan_value)

    def _handle_swing_setting(self, settings, requests):
        """Handle swing-related settings."""
        if (
            'f_dir' not in settings
            or self.values['mode'] not in self.API_PATHS["swing_settings"]
        ):
            return

        # Set vertical swing, unless an explicit vane position is also being
        # set (that takes precedence for the vertical axis, handled separately).
        if 'vane_vertical' not in settings:
            vertical_path = self.get_path(
                "swing_settings", self.values['mode'], "vertical"
            )
            self.add_request(
                requests,
                vertical_path,
                (
                    self.TURN_OFF_SWING_AXIS
                    if settings['f_dir'] in ('off', 'horizontal')
                    else self.TURN_ON_SWING_AXIS
                ),
            )

        # Set horizontal swing
        horizontal_path = self.get_path(
            "swing_settings", self.values['mode'], "horizontal"
        )
        self.add_request(
            requests,
            horizontal_path,
            (
                self.TURN_OFF_SWING_AXIS
                if settings['f_dir'] in ('off', 'vertical')
                else self.TURN_ON_SWING_AXIS
            ),
        )

    def _handle_feature_toggles(self, settings, requests):
        """Handle comfort/econo/outdoor_quiet/powerful on-off toggles.

        Each accepts human ('on'/'off') or raw ('01'/'00') values. Enforces
        the hardware mutual-exclusion documented in the unit's manual: Powerful
        and {Comfort, Econo, Outdoor Quiet} cannot be active at the same time,
        so enabling one side clears the other (mirroring the remote's
        last-button-pressed-wins behaviour).
        """
        requested = {}
        for key in self.POWER_TOGGLES:
            if key not in settings:
                continue
            raw = self.human_to_daikin(key, settings[key])
            if raw in ('00', '01'):
                requested[key] = raw

        if not requested:
            return

        trio = ('comfort', 'econo', 'outdoor_quiet')
        # Turning Powerful on clears any currently-active trio member...
        if requested.get('powerful') == '01':
            for k in trio:
                if self.values.get(k) == 'on' and k not in requested:
                    requested[k] = '00'
        # ...and turning on any trio member clears an active Powerful.
        if any(requested.get(k) == '01' for k in trio):
            if self.values.get('powerful') == 'on' and 'powerful' not in requested:
                requested['powerful'] = '00'

        for key, raw in requested.items():
            self.add_request(requests, self.get_path(key), raw)

    def _handle_vane_setting(self, settings, requests):
        """Handle discrete vertical vane position settings.

        Distinct from swing (f_dir): pins the vane to the floor ('down') or
        restores 'off'/'swing'. Mode-specific, like swing. Only these byte-0
        states have physical effect on this firmware.
        """
        if (
            'vane_vertical' not in settings
            or self.values['mode'] not in self.API_PATHS["swing_settings"]
        ):
            return

        raw = self.REVERSE_VERTICAL_VANE_MAP.get(settings['vane_vertical'])
        if raw is None:
            return

        path = self.get_path("swing_settings", self.values['mode'], "vertical")
        self.add_request(requests, path, raw)

    async def set(self, settings):
        """Set settings on Daikin device."""
        await self._update_settings(settings)
        requests = []

        # Handle different types of settings
        self._handle_power_setting(settings, requests)
        self._handle_temperature_setting(settings, requests)
        self._handle_fan_setting(settings, requests)
        # vane_vertical takes precedence over swing for the vertical axis, so
        # handle swing first and let an explicit vane position override it.
        self._handle_swing_setting(settings, requests)
        self._handle_vane_setting(settings, requests)
        self._handle_feature_toggles(settings, requests)

        if requests:
            request_payload = DaikinRequest(requests).serialize()
            _LOGGER.debug("Sending request: %s", request_payload)
            response = await self._get_resource("", params=request_payload)
            _LOGGER.debug("Response: %s", response)

            # Update status after setting
            await self.update_status()

    # pylint: disable=unused-argument
    async def set_streamer(self, mode):
        """Streamer mode not supported in firmware 2.8.0"""
        _LOGGER.debug("Streamer mode not supported in firmware 2.8.0")

    # pylint: disable=unused-argument
    async def set_holiday(self, mode):
        """Set holiday mode."""
        _LOGGER.debug("Holiday mode not supported in firmware 2.8.0")

    # pylint: disable=unused-argument
    async def set_advanced_mode(self, mode, value):
        """Set advanced mode."""
        _LOGGER.debug("Advanced mode not supported in firmware 2.8.0")

    @property
    def support_away_mode(self) -> bool:
        """Set holiday mode not supported in firmware 2.8.0"""
        return False

    @property
    def support_advanced_modes(self) -> bool:
        """Advanced mode not supported in firmware 2.8.0"""
        return False

    @property
    def support_zone_count(self) -> bool:
        """Zones mode not supported in firmware 2.8.0"""
        return False

    async def set_comfort_mode(self, mode):
        """Enable or disable comfort airflow ('on'/'off')."""
        await self.set({'comfort': mode})

    @property
    def support_comfort_mode(self) -> bool:
        """Return True if the device exposes comfort airflow."""
        return 'comfort' in self.values

    @property
    def comfort_mode(self) -> Optional[str]:
        """Return current comfort airflow state ('on'/'off')."""
        return self.values.get('comfort')

    @property
    def vertical_vane(self) -> Optional[str]:
        """Return current vertical vane position ('off'/'down'/'swing')."""
        return self.values.get('vane_vertical')

    async def set_vertical_vane(self, position):
        """Set the vertical vane position ('off'/'down'/'swing')."""
        await self.set({'vane_vertical': position})

    async def set_econo_mode(self, mode):
        """Enable or disable Econo mode ('on'/'off')."""
        await self.set({'econo': mode})

    @property
    def support_econo_mode(self) -> bool:
        """Return True if the device exposes Econo mode."""
        return 'econo' in self.values

    @property
    def econo_mode(self) -> Optional[str]:
        """Return current Econo state ('on'/'off')."""
        return self.values.get('econo')

    async def set_outdoor_quiet_mode(self, mode):
        """Enable or disable outdoor-unit quiet mode ('on'/'off')."""
        await self.set({'outdoor_quiet': mode})

    @property
    def support_outdoor_quiet_mode(self) -> bool:
        """Return True if the device exposes outdoor-unit quiet mode."""
        return 'outdoor_quiet' in self.values

    @property
    def outdoor_quiet_mode(self) -> Optional[str]:
        """Return current outdoor-unit quiet state ('on'/'off')."""
        return self.values.get('outdoor_quiet')

    async def set_powerful_mode(self, mode):
        """Enable or disable Powerful mode ('on'/'off').

        The unit also auto-cancels Powerful after ~20 minutes on its own.
        """
        await self.set({'powerful': mode})

    @property
    def support_powerful_mode(self) -> bool:
        """Return True if the device exposes Powerful mode."""
        return 'powerful' in self.values

    @property
    def powerful_mode(self) -> Optional[str]:
        """Return current Powerful state ('on'/'off')."""
        return self.values.get('powerful')

    @property
    def support_compressor_temperature(self) -> bool:
        """Return True if the device reports outdoor compressor temperature."""
        return 'cmp_temp' in self.values

    @property
    def compressor_temperature(self) -> Optional[float]:
        """Return outdoor compressor temperature in Celsius (approximate)."""
        return self._parse_number('cmp_temp')

    @property
    def model(self) -> Optional[str]:
        """Return the decoded indoor unit model string."""
        return self.values.get('model')

    @property
    def outdoor_model(self) -> Optional[str]:
        """Return the decoded outdoor unit model string."""
        return self.values.get('outdoor_model')

    @property
    def firmware_version(self) -> Optional[str]:
        """Return the adapter firmware version."""
        return self.values.get('ver')
