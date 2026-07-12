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


# pylint: disable=abstract-method
class DaikinBRP084(Appliance):
    """Daikin class for BRP devices with firmware 2.8.0."""

    # Centralized API paths for easier maintenance and better organization
    E_1002_PATH = [
        "/dsiot/edge/adr_0100.dgc_status",
        "dgc_status",
        "e_1002",
    ]
    E_1002_E_3001_PATH = E_1002_PATH + ["e_3001"]

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
        # Outdoor unit e_2006 (discovered via setpoint-sweep probing on FTXM71):
        # p_01 = compressor run flag, p_04 = compressor frequency (u16 LE, Hz),
        # p_0B = refrigerant temp (i16 LE / 10 °C), p_25 = heat-exchanger temp.
        "compressor_running": [
            "/dsiot/edge/adr_0200.dgc_status",
            "dgc_status",
            "e_1003",
            "e_2006",
            "p_01",
        ],
        "compressor_frequency": [
            "/dsiot/edge/adr_0200.dgc_status",
            "dgc_status",
            "e_1003",
            "e_2006",
            "p_04",
        ],
        "outdoor_refrigerant_temp": [
            "/dsiot/edge/adr_0200.dgc_status",
            "dgc_status",
            "e_1003",
            "e_2006",
            "p_0B",
        ],
        "outdoor_hx_temp": [
            "/dsiot/edge/adr_0200.dgc_status",
            "dgc_status",
            "e_1003",
            "e_2006",
            "p_25",
        ],
        # Outdoor unit other diagnostics (verified via fan-mode probe):
        #   e_2005/p_01 = electronic expansion valve position (u16 LE, steps)
        #   e_2008/p_01 = outdoor fan step (u16 LE)
        "eev_position": [
            "/dsiot/edge/adr_0200.dgc_status",
            "dgc_status",
            "e_1003",
            "e_2005",
            "p_01",
        ],
        "outdoor_fan_step": [
            "/dsiot/edge/adr_0200.dgc_status",
            "dgc_status",
            "e_1003",
            "e_2008",
            "p_01",
        ],
        # Indoor unit e_3003/p_0C — internal "compensated target" the firmware
        # uses for control, computed as user setpoint + 3-4°C control curve
        # offset (verified via setpoint sweep: setpoint=20→23°C, p_0C=23→27°C).
        # Encoding matches the user-facing setpoints in e_3001 (u8/2 = °C).
        # Writable but auto-overwritten by control logic within ~10s.
        # The gap between this and the user setpoint is the most likely cause
        # of the "+5°C overshoot" Daikin owners often report.
        "internal_heat_target": [
            "/dsiot/edge/adr_0100.dgc_status",
            "dgc_status",
            "e_1002",
            "e_3003",
            "p_0C",
        ],
        # Indoor unit e_2015_02 (discovered via fan-mode probe on FTXM71):
        # both sensors converge with compressor off → same coil, two locations.
        # In hot mode: p_03 (refrigerant inlet, hot gas from compressor) is
        # 20-30°C above p_02 (refrigerant outlet, after dumping heat to room).
        # In cool mode the relationship inverts.
        "indoor_coil_inlet_temp": [
            "/dsiot/edge/adr_0100.dgc_status",
            "dgc_status",
            "e_1002",
            "e_2015_02",
            "p_03",
        ],
        "indoor_coil_outlet_temp": [
            "/dsiot/edge/adr_0100.dgc_status",
            "dgc_status",
            "e_1002",
            "e_2015_02",
            "p_02",
        ],
        "mac_address": ["/dsiot/edge.adp_i", "adp_i", "mac"],
        # Adapter firmware version (e.g. "3_12_3" -> "3.12.3")
        "firmware_version": ["/dsiot/edge.adp_i", "adp_i", "ver"],
        # Unit model code, ASCII-hex encoded in e_A001/p_0D (e.g. "43393431" -> "C941")
        "model_code": E_1002_PATH + ["e_A001", "p_0D"],
        # Mode-specific paths for temperature settings
        "temp_settings": {
            "cool": E_1002_E_3001_PATH + ["p_02"],
            "hot": E_1002_E_3001_PATH + ["p_03"],
            "auto": E_1002_E_3001_PATH + ["p_1D"],
        },
        # Fan settings organized by mode
        "fan_settings": {
            "auto": E_1002_E_3001_PATH + ["p_26"],
            "cool": E_1002_E_3001_PATH + ["p_09"],
            "hot": E_1002_E_3001_PATH + ["p_0A"],
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
            "hot": {
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
            '0100': 'hot',
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
    }

    # Mapping between the values from firmware 2.8.0 to traditional API values
    MODE_MAP = {
        '0300': 'auto',
        '0200': 'cool',
        '0100': 'hot',
        '0000': 'fan',
        '0500': 'dry',
    }

    # Aliases accepted from callers (e.g. Home Assistant's climate integration
    # passes "heat" as an alias for "hot").
    MODE_ALIASES = {
        'heat': 'hot',
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
    def hex_le_u16(value: str) -> Optional[int]:
        """Decode a 2-byte little-endian unsigned integer from a 4-char hex string."""
        if not isinstance(value, str) or len(value) < 4:
            return None
        try:
            return int(value[2:4] + value[0:2], 16)
        except ValueError:
            return None

    @staticmethod
    def hex_le_i16_div10(value: str) -> Optional[float]:
        """Decode a 2-byte little-endian signed int16 / 10 from a 4-char hex string.

        Used for refrigerant / heat-exchanger / coil temperatures across both
        the indoor and outdoor units. Returns degrees Celsius.
        """
        if not isinstance(value, str) or len(value) < 4:
            return None
        try:
            raw = int.from_bytes(bytes.fromhex(value[:4]), 'little', signed=True)
            return raw / 10.0
        except ValueError:
            return None

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

            # Get temperatures
            self.values['otemp'] = str(
                self.hex_to_temp(
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

            # Get compressor state (outdoor unit e_2006). Present on FTXM-series;
            # absent on units that don't expose e_2006 — in that case we leave
            # the values unset and support_compressor_frequency stays False.
            try:
                freq_hex = self.find_value_by_pn(
                    response, *self.get_path("compressor_frequency")
                )
                freq = self.hex_le_u16(freq_hex)
                if freq is not None:
                    self.values['cmpfreq'] = str(freq)
            except DaikinException:
                pass

            try:
                run_flag = self.find_value_by_pn(
                    response, *self.get_path("compressor_running")
                )
                if run_flag is not None:
                    self.values['compressor_running'] = (
                        '1' if run_flag == '01' else '0'
                    )
            except DaikinException:
                pass

            # Diagnostic temperature sensors (i16 LE / 10 °C). Each wrapped in
            # try/except so units that don't expose the entity stay quiet.
            for values_key, path_key in (
                ('outdoor_refrigerant_temp', 'outdoor_refrigerant_temp'),
                ('outdoor_hx_temp',          'outdoor_hx_temp'),
                ('indoor_coil_inlet_temp',   'indoor_coil_inlet_temp'),
                ('indoor_coil_outlet_temp',  'indoor_coil_outlet_temp'),
            ):
                try:
                    raw = self.find_value_by_pn(response, *self.get_path(path_key))
                    decoded = self.hex_le_i16_div10(raw)
                    if decoded is not None:
                        self.values[values_key] = str(decoded)
                except DaikinException:
                    pass

            # Diagnostic step values (u16 LE, raw step counts).
            for values_key, path_key in (
                ('eev_position',     'eev_position'),
                ('outdoor_fan_step', 'outdoor_fan_step'),
            ):
                try:
                    raw = self.find_value_by_pn(response, *self.get_path(path_key))
                    decoded = self.hex_le_u16(raw)
                    if decoded is not None:
                        self.values[values_key] = str(decoded)
                except DaikinException:
                    pass

            # Internal compensated target (u8 / 2 = °C, same encoding
            # as e_3001/p_03 user setpoint). See API_PATHS comment above.
            try:
                raw = self.find_value_by_pn(
                    response, *self.get_path("internal_heat_target")
                )
                if raw and len(raw) >= 2:
                    self.values['internal_heat_target'] = str(int(raw[:2], 16) / 2)
            except DaikinException:
                pass
            except ValueError:
                pass

            # Estimated indoor temperature (hot mode only): the indoor sensor
            # is a return-air thermistor that reads several °C above actual
            # room air. The firmware silently compensates by aiming for a
            # higher internal target (e_3003/p_0C = user setpoint + bias).
            # Subtract that same bias from the return-air reading to estimate
            # actual room temperature.
            #
            #   estimated = indoor_temp - (internal_heat_target - user_setpoint)
            #
            # Only computed in hot mode (internal_heat_target is hot-mode-specific
            # and undefined in cool/fan/dry/auto/off).
            if self.values.get('mode', invalidate=False) == 'hot':
                try:
                    htemp = float(self.values['htemp'])
                    stemp = float(self.values['stemp'])
                    iht = float(self.values['internal_heat_target'])
                    bias = iht - stemp
                    self.values['estimated_indoor_temp'] = str(round(htemp - bias, 1))
                except (KeyError, ValueError, TypeError):
                    pass

            # Device identity — firmware version (from WiFi adapter) and model
            # code (ASCII-hex in e_A001/p_0D). entity.py in HA expects these
            # under `ver` and `model` respectively for the DeviceInfo panel.
            try:
                ver = self.find_value_by_pn(
                    response, *self.get_path("firmware_version")
                )
                if ver:
                    self.values['ver'] = ver
            except DaikinException:
                pass

            try:
                model_hex = self.find_value_by_pn(
                    response, *self.get_path("model_code")
                )
                if model_hex:
                    try:
                        self.values['model'] = (
                            bytes.fromhex(model_hex)
                            .decode('ascii', errors='replace')
                            .strip()
                        )
                    except ValueError:
                        pass
            except DaikinException:
                pass

        except DaikinException as e:
            _LOGGER.error("Error extracting values: %s", e)
            raise

        # Feed the energy-consumption history buffer. The base-class
        # Appliance.update_status() does this automatically, but BRP084
        # overrides the method and so we must call it explicitly — otherwise
        # current_power_consumption() never leaves its "not initialized"
        # branch and HA's "Estimated power draw" sensor stays at 0 kW.
        self._register_energy_consumption_history()

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
                # Normalize alias so cached mode matches what was written
                self.values['mode'] = self.MODE_ALIASES.get(value, value)
            else:
                self.values[key] = value

        return self.values

    def add_request(self, requests, path, value):
        """Append DaikinAttribute to requests."""
        requests.append(DaikinAttribute(path[-1], value, path[2:4], path[0]))

    def _handle_power_setting(self, settings, requests):
        """Handle power-related settings.

        Mirrors BRP069's contract (see daikin_brp069.py _update_settings,
        the `'mode' in settings or not settings → pow='1'` branch):
          - device.set({})            → power ON (HA's toggle switch path)
          - device.set({'mode':'off'}) → power OFF
          - device.set({'mode': X})   → power ON + set mode X
          - device.set({'stemp': X})  → temperature only, leave power as-is
                                         (so changing setpoint on a powered-
                                         off unit does NOT turn it on).
        """
        # Truly empty settings → HA's "turn on" path. Only this empty case
        # forces a power write; other partial settings (e.g. just stemp)
        # leave power untouched.
        if not settings:
            self.add_request(requests, self.get_path("power"), "01")
            return

        # Settings present but no mode key → no power write.
        if 'mode' not in settings:
            return

        # Mode change → write power explicitly.
        power_path = self.get_path("power")
        self.add_request(
            requests, power_path, "00" if settings['mode'] == 'off' else "01"
        )

        if settings['mode'] == 'off':
            return

        # Set mode. Apply caller-side aliases (e.g. HA passes "heat" for hot).
        requested_mode = self.MODE_ALIASES.get(settings['mode'], settings['mode'])
        mode_value = self.REVERSE_MODE_MAP.get(requested_mode)
        if mode_value:
            mode_path = self.get_path("mode")
            self.add_request(requests, mode_path, mode_value)
        else:
            _LOGGER.warning(
                "Unrecognized mode %r; no mode write will be sent",
                settings['mode'],
            )

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

        # Set vertical swing
        vertical_path = self.get_path("swing_settings", self.values['mode"], "vertical")
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

    async def set(self, settings):
        """Set settings on Daikin device."""
        await self._update_settings(settings)
        requests = []

        # Handle different types of settings
        self._handle_power_setting(settings, requests)
        self._handle_temperature_setting(settings, requests)
        self._handle_fan_setting(settings, requests)
        self._handle_swing_setting(settings, requests)

        if requests:
            request_payload = DaikinRequest(requests).serialize()
            _LOGGER.debug("Sending request: %s", request_payload)
            response = await self._get_resource("", params=request_payload)
            _LOGGER.debug("Response: %s", response)

            # Update status after setting
            await self.update_status()

    @property
    def today_energy_consumption(self):
        """Return today's energy consumption in kWh.

        BRP084 reports only aggregate daily energy (via the `datas` array); the
        cool/hot per-day split used by BRP069 (`curr_day_cool`/`curr_day_hot`)
        is not available on this firmware. Fall back to the total so HA energy
        sensors populate instead of staying at 0.
        """
        return super().today_energy_consumption or self.today_total_energy_consumption

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
