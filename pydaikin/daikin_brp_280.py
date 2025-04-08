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


class DaikinBRP280(Appliance):
    """Daikin class for BRP devices with firmware 2.8.0."""

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

    FAN_MODE_MAP = {
        '0A00': 'auto',
        '0B00': 'quiet',
        '0300': '1',
        '0400': '2',
        '0500': '3',
        '0600': '4',
        '0700': '5',
    }

    # For each mode, mapping to the temperature parameter and swing parameters
    HVAC_MODE_TO_TEMP_HEX = {
        'cool': 'p_02',
        'hot': 'p_03',
        'auto': 'p_1D',
    }

    HVAC_MODE_TO_SWING_ATTR_NAMES = {
        'auto': ('p_20', 'p_21'),
        'cool': ('p_05', 'p_06'),
        'hot': ('p_07', 'p_08'),
        'fan': ('p_24', 'p_25'),
        'dry': ('p_22', 'p_23'),
    }

    HVAC_MODE_TO_FAN_SPEED_ATTR_NAME = {
        'auto': 'p_26',
        'cool': 'p_09',
        'hot': 'p_0A',
        'fan': 'p_28',
    }

    # The values for turning swing axis on/off
    TURN_OFF_SWING_AXIS = "000000"
    TURN_ON_SWING_AXIS = "0F0000"

    REVERSE_MODE_MAP = {v: k for k, v in MODE_MAP.items()}
    REVERSE_FAN_MODE_MAP = {v: k for k, v in FAN_MODE_MAP.items()}

    INFO_RESOURCES = []

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
        if mode is None or mode == 'off':
            return 'off'

        if mode not in self.HVAC_MODE_TO_SWING_ATTR_NAMES:
            return 'off'

        vertical_attr_name, horizontal_attr_name = self.HVAC_MODE_TO_SWING_ATTR_NAMES[
            mode
        ]

        try:
            vertical = "F" in self.find_value_by_pn(
                data,
                "/dsiot/edge/adr_0100.dgc_status",
                "dgc_status",
                "e_1002",
                "e_3001",
                vertical_attr_name,
            )
            horizontal = "F" in self.find_value_by_pn(
                data,
                "/dsiot/edge/adr_0100.dgc_status",
                "dgc_status",
                "e_1002",
                "e_3001",
                horizontal_attr_name,
            )

            if horizontal and vertical:
                return 'both'
            if horizontal:
                return 'horizontal'
            if vertical:
                return 'vertical'

            return 'off'
        except DaikinException:
            return 'off'

    async def init(self):
        """Initialize the device and fetch initial state."""
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
            _LOGGER.error("Error communicating with device: %s", e)
            raise DaikinException(f"Failed to communicate with device: {e}") from e

        # Extract basic info
        try:
            # Get MAC address
            mac = self.find_value_by_pn(response, "/dsiot/edge.adp_i", "adp_i", "mac")
            self.values['mac'] = mac

            # Get power state
            is_off = (
                self.find_value_by_pn(
                    response,
                    "/dsiot/edge/adr_0100.dgc_status",
                    "dgc_status",
                    "e_1002",
                    "e_A002",
                    "p_01",
                )
                == "00"
            )

            # Get mode
            mode_value = self.find_value_by_pn(
                response,
                '/dsiot/edge/adr_0100.dgc_status',
                'dgc_status',
                'e_1002',
                'e_3001',
                'p_01',
            )

            self.values['pow'] = "0" if is_off else "1"
            self.values['mode'] = 'off' if is_off else self.MODE_MAP[mode_value]

            # Get temperatures
            self.values['otemp'] = str(
                self.hex_to_temp(
                    self.find_value_by_pn(
                        response,
                        '/dsiot/edge/adr_0200.dgc_status',
                        'dgc_status',
                        'e_1003',
                        'e_A00D',
                        'p_01',
                    )
                )
            )

            self.values['htemp'] = str(
                self.hex_to_temp(
                    self.find_value_by_pn(
                        response,
                        '/dsiot/edge/adr_0100.dgc_status',
                        'dgc_status',
                        'e_1002',
                        'e_A00B',
                        'p_01',
                    ),
                    divisor=1,
                )
            )

            # Get humidity
            try:
                self.values['hhum'] = str(
                    int(
                        self.find_value_by_pn(
                            response,
                            '/dsiot/edge/adr_0100.dgc_status',
                            'dgc_status',
                            'e_1002',
                            'e_A00B',
                            'p_02',
                        ),
                        16,
                    )
                )
            except DaikinException:
                self.values['hhum'] = "--"

            # Get target temperature
            if self.values['mode'] in self.HVAC_MODE_TO_TEMP_HEX:
                temp_param = self.HVAC_MODE_TO_TEMP_HEX[self.values['mode']]
                self.values['stemp'] = str(
                    self.hex_to_temp(
                        self.find_value_by_pn(
                            response,
                            '/dsiot/edge/adr_0100.dgc_status',
                            'dgc_status',
                            'e_1002',
                            'e_3001',
                            temp_param,
                        )
                    )
                )
            else:
                self.values['stemp'] = "--"

            # Get fan mode
            if self.values['mode'] in self.HVAC_MODE_TO_FAN_SPEED_ATTR_NAME:
                fan_param = self.HVAC_MODE_TO_FAN_SPEED_ATTR_NAME[self.values['mode']]
                fan_value = self.find_value_by_pn(
                    response,
                    "/dsiot/edge/adr_0100.dgc_status",
                    "dgc_status",
                    "e_1002",
                    "e_3001",
                    fan_param,
                )
                self.values['f_rate'] = self.FAN_MODE_MAP.get(fan_value, 'auto')
            else:
                self.values['f_rate'] = 'auto'

            # Get swing mode
            self.values['f_dir'] = self.get_swing_state(response)

            # Get energy data
            try:
                self.values['today_runtime'] = self.find_value_by_pn(
                    response,
                    '/dsiot/edge/adr_0100.i_power.week_power',
                    'week_power',
                    'today_runtime',
                )

                energy_data = self.find_value_by_pn(
                    response,
                    '/dsiot/edge/adr_0100.i_power.week_power',
                    'week_power',
                    'datas',
                )
                if isinstance(energy_data, list) and len(energy_data) > 0:
                    self.values['datas'] = '/'.join(map(str, energy_data))
            except DaikinException:
                pass

        except DaikinException as e:
            _LOGGER.error("Error extracting values: %s", e)
            raise

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

    async def set(self, settings):
        """Set settings on Daikin device."""
        await self._update_settings(settings)

        requests = []

        # Handle power state
        if 'mode' in settings and settings['mode'] == 'off':
            # Turn off
            requests.append(
                DaikinAttribute(
                    "p_01",
                    "00",
                    ["e_1002", "e_A002"],
                    "/dsiot/edge/adr_0100.dgc_status",
                )
            )
        else:
            # If turning on or changing mode
            if 'mode' in settings and settings['mode'] != 'off':
                # Turn on
                requests.append(
                    DaikinAttribute(
                        "p_01",
                        "01",
                        ["e_1002", "e_A002"],
                        "/dsiot/edge/adr_0100.dgc_status",
                    )
                )

                # Set mode
                mode_value = self.REVERSE_MODE_MAP.get(settings['mode'])
                if mode_value:
                    requests.append(
                        DaikinAttribute(
                            "p_01",
                            mode_value,
                            ["e_1002", "e_3001"],
                            "/dsiot/edge/adr_0100.dgc_status",
                        )
                    )

            # Set temperature if applicable
            if (
                'stemp' in settings
                and self.values['mode'] in self.HVAC_MODE_TO_TEMP_HEX
            ):
                temp_param = self.HVAC_MODE_TO_TEMP_HEX[self.values['mode']]
                temp_hex = self.temp_to_hex(float(settings['stemp']))
                requests.append(
                    DaikinAttribute(
                        temp_param,
                        temp_hex,
                        ["e_1002", "e_3001"],
                        "/dsiot/edge/adr_0100.dgc_status",
                    )
                )

            # Set fan mode if applicable
            if (
                'f_rate' in settings
                and self.values['mode'] in self.HVAC_MODE_TO_FAN_SPEED_ATTR_NAME
            ):
                fan_param = self.HVAC_MODE_TO_FAN_SPEED_ATTR_NAME[self.values['mode']]
                fan_value = None

                # Try both formats - the internal one and the user-friendly one
                for key, value in self.FAN_MODE_MAP.items():
                    if value == settings['f_rate'] or key == settings['f_rate']:
                        fan_value = key
                        break

                if fan_value:
                    requests.append(
                        DaikinAttribute(
                            fan_param,
                            fan_value,
                            ["e_1002", "e_3001"],
                            "/dsiot/edge/adr_0100.dgc_status",
                        )
                    )

            # Set swing mode if applicable
            if (
                'f_dir' in settings
                and self.values['mode'] in self.HVAC_MODE_TO_SWING_ATTR_NAMES
            ):
                vertical_attr_name, horizontal_attr_name = (
                    self.HVAC_MODE_TO_SWING_ATTR_NAMES[self.values['mode']]
                )

                if settings['f_dir'] in ('off', 'horizontal'):
                    # Turn off vertical swing
                    requests.append(
                        DaikinAttribute(
                            vertical_attr_name,
                            self.TURN_OFF_SWING_AXIS,
                            ["e_1002", "e_3001"],
                            "/dsiot/edge/adr_0100.dgc_status",
                        )
                    )
                else:
                    # Turn on vertical swing
                    requests.append(
                        DaikinAttribute(
                            vertical_attr_name,
                            self.TURN_ON_SWING_AXIS,
                            ["e_1002", "e_3001"],
                            "/dsiot/edge/adr_0100.dgc_status",
                        )
                    )

                if settings['f_dir'] in ('off', 'vertical'):
                    # Turn off horizontal swing
                    requests.append(
                        DaikinAttribute(
                            horizontal_attr_name,
                            self.TURN_OFF_SWING_AXIS,
                            ["e_1002", "e_3001"],
                            "/dsiot/edge/adr_0100.dgc_status",
                        )
                    )
                else:
                    # Turn on horizontal swing
                    requests.append(
                        DaikinAttribute(
                            horizontal_attr_name,
                            self.TURN_ON_SWING_AXIS,
                            ["e_1002", "e_3001"],
                            "/dsiot/edge/adr_0100.dgc_status",
                        )
                    )

        if requests:
            request_payload = DaikinRequest(requests).serialize()
            _LOGGER.debug("Sending request: %s", request_payload)
            response = await self._get_resource("", params=request_payload)
            _LOGGER.debug("Response: %s", response)

            # Update status after setting
            await self.update_status()
async def set_holiday(self, mode):
    """Set holiday mode. Not supported in this firmware."""
    _LOGGER.warning("Holiday mode not supported in firmware 2.8.0")

async def set_advanced_mode(self, mode, value):
    """Set advanced mode. Not supported in this firmware."""
    _LOGGER.warning("Advanced mode not supported in firmware 2.8.0")

async def set_streamer(self, mode):
    """Set streamer mode. Not supported in this firmware."""
    _LOGGER.warning("Streamer mode not supported in firmware 2.8.0")

async def set_zone(self, zone_id, status):
    """Set zone status. Not supported in this firmware."""
    _LOGGER.warning("Zone control not supported in firmware 2.8.0")
