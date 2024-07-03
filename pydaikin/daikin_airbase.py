"""Pydaikin appliance, represent a Daikin AirBase device."""

import logging
from typing import Optional
from urllib.parse import quote, unquote

from .daikin_brp069 import DaikinBRP069
from .exceptions import DaikinException

_LOGGER = logging.getLogger(__name__)


class DaikinAirBase(DaikinBRP069):
    """Daikin class for AirBase (BRP15B61) units."""

    TRANSLATIONS = dict(
        DaikinBRP069.TRANSLATIONS,
        **{
            "mode": {
                "0": "fan",
                "1": "hot",
                "2": "cool",
                "3": "auto",
                "7": "dry",
            },
            "f_rate": {
                "0": "auto",
                "1": "low",
                "3": "mid",
                "5": "high",
                "1a": "low/auto",
                "3a": "mid/auto",
                "5a": "high/auto",
            },
        },
    )

    HTTP_RESOURCES = [
        "common/basic_info",
        "aircon/get_control_info",
        "aircon/get_model_info",
        "aircon/get_sensor_info",
        "aircon/get_zone_setting",
    ]

    INFO_RESOURCES = DaikinBRP069.INFO_RESOURCES + ["aircon/get_zone_setting"]

    DEFAULTS = {"htemp": "-", "otemp": "-", "shum": "--"}

    @staticmethod
    def parse_response(response_body):
        """Parse response from Daikin, add support for f_rate-auto."""
        _LOGGER.debug("Parsing %s", response_body)
        response = super(DaikinAirBase, DaikinAirBase).parse_response(response_body)
        if response.get("f_auto") == "1":
            response["f_rate"] = f'{response["f_rate"]}a'

        return response

    def __init__(  # pylint:disable=useless-parent-delegation
        self, device_id, session=None
    ) -> None:
        """Init Daikin AirBase (BRP15B61) device."""
        super().__init__(device_id, session)

    async def init(self):
        """Init status and set defaults."""
        await super().init()
        if not self.values:
            raise DaikinException("Empty values.")
        self.values.update({**self.DEFAULTS, **self.values})
        # Friendly display the model
        if self.values.get("model", None) == "NOTSUPPORT":
            self.values["model"] = "Airbase BRP15B61"

    async def _get_resource(self, path: str, params: Optional[dict] = None):
        """Make the http request."""
        path = f"skyfi/{path}"
        return await super()._get_resource(path, params)

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return False

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return False

    @property
    def outside_temperature(self):
        """AirBase unit returns otemp if master controller starts before it.

        No Outside Thermometor returns a '-' (Non Number).
        Return current outside temperature if available.
        """
        value = self.values.get("otemp")
        return self._parse_number("otemp") if value != "-" else None

    @property
    def support_zone_temperature(self):
        """Return True if the device support setting zone_temperature."""
        return "lztemp_c" in self.values and "lztemp_h" in self.values

    @property
    def fan_rate(self):
        """Return list of supported fan rates."""
        fan_rates = list(map(str.title, self.TRANSLATIONS.get("f_rate", {}).values()))
        if self.values.get("frate_steps") == "2":
            if self.values.get("en_frate_auto") == "0":
                return fan_rates[1:4:2]
            return fan_rates[:3:2] + fan_rates[3::2]
        if self.values.get("en_frate_auto") == "0":
            return fan_rates[1:4]
        return fan_rates

    async def _update_settings(self, settings):
        """Update settings to set on Daikin device."""

        # Call the base BRP069 method to update the settings; it will
        # return the current values it retrieves from the controller
        # so we can further process them
        current_val = await super()._update_settings(settings)

        # f_auto requires some special handling, as it is managed as an
        # attribute of f_rate and we don't directly set it - so when f_rate
        # is being changed, ensure we update f_auto accordingly if it is
        # defined in the current device's returned settings
        if "f_auto" in current_val:
            # The system supports f_auto; if we are setting the fan speed
            # then ensure we update the f_auto setting as well
            if "f_rate" in settings:
                self.values["f_auto"] = "1" if "a" in self.values["f_rate"] else "0"
            else:
                key = "auto" + self.values["mode"]
                if key in current_val:
                    self.values["f_auto"] = current_val[key]

                    # The f_rate value would have been retrieved from the unit's current
                    # operating mode fan rate setting, and needs the 'a' suffix reinstated
                    # if we are running in an automatic fan speed mode
                    if self.values["f_auto"] == "1":
                        self.values["f_rate"] = f'{self.values["f_rate"]}a'

        return current_val

    async def set(self, settings):
        """Set settings on Daikin device."""
        await self._update_settings(settings)

        self.values.setdefault("f_airside", 0)

        path = "aircon/set_control_info"
        params = {
            "f_airside": self.values["f_airside"],
            "f_auto": self.values["f_auto"],
            "f_dir": self.values["f_dir"],
            "f_rate": self.values["f_rate"][0],
            "lpw": "",
            "mode": self.values["mode"],
            "pow": self.values["pow"],
            "shum": self.values["shum"],
            "stemp": self.values["stemp"],
        }

        _LOGGER.debug("Sending request to %s with params: %s", path, params)
        await self._get_resource(path, params)

    def represent(self, key):
        """Return translated value from key."""
        k, val = super().represent(key)

        if key in ["zone_name", "zone_onoff", "lztemp_c", "lztemp_h"]:
            val = unquote(self.values[key]).split(";")

        return (k, val)

    @property
    def zones(self):
        """Return list of zones."""
        if not self.values.get("zone_name"):
            return None
        enabled_zones = len(self.represent("zone_name")[1])
        if self.support_zone_count:
            enabled_zones = int(self.zone_count)  # float to int
        zone_onoff = self.represent("zone_onoff")[1]
        zone_list = self.represent("zone_name")[1][
            :enabled_zones
        ]  # Slicing to limit zones
        if self.support_zone_temperature:
            mode = self.values["mode"]

            if mode == "3":
                mode = self.values["operate"]

            if mode == "1":
                zone_temp = self.represent("lztemp_h")[1]
            elif mode == "2":
                zone_temp = self.represent("lztemp_c")[1]
            else:
                zone_temp = [self.values["stemp"]] * len(zone_list)

            return [
                (name.strip(" +,"), zone_onoff[i], float(zone_temp[i]))
                for i, name in enumerate(zone_list)
            ]

        return [
            (name.strip(" +,"), zone_onoff[i], 0) for i, name in enumerate(zone_list)
        ]

    async def set_zone(self, zone_id, key, value):
        """Set zone status."""
        current_state = await self._get_resource("aircon/get_zone_setting")
        self.values.update(current_state)
        if key == "lztemp":
            mode = self.values["mode"]

            if mode == "3":
                mode = self.values["operate"]

            if mode == "1":
                key = "lztemp_h"
            elif mode == "2":
                key = "lztemp_c"

        if key not in current_state:
            raise KeyError

        current_group = self.represent(key)[1]
        current_group[zone_id] = value
        self.values[key] = quote(";".join(current_group)).lower()

        path = "aircon/set_zone_setting"
        params = {
            "zone_name": current_state["zone_name"],
            "zone_onoff": self.values["zone_onoff"],
        }

        if self.support_zone_temperature:
            params.update({"lztemp_c": self.values["lztemp_c"]})
            params.update({"lztemp_h": self.values["lztemp_h"]})

        # Zone Name requires %20 encoding which is not handled well
        # within yarl resulting in '%20' being encoded again to '%2520'
        # For detailed info before changing query string to pparam
        # refer to: https://github.com/fredrike/pydaikin/pull/11

        # # Convert params dictionary to query string format
        params_str = "&".join(f"{k}={v}" for k, v in params.items())
        path = f"{path}?{params_str}"  # Append params as query string to path

        _LOGGER.debug(
            "Updating ['aircon/set_zone_setting']: %s",
            ",".join(f"{k}={unquote(v)}" for k, v in params.items()),
        )
        await self._get_resource(path)
