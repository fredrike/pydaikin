"""Pydaikin base appliance, represent a Daikin device."""

import logging
import socket
from urllib.parse import unquote

from aiohttp import ClientSession, ServerDisconnectedError

import pydaikin.discovery as discovery

_LOGGER = logging.getLogger(__name__)


class Appliance:  # pylint: disable=too-many-public-methods
    """Daikin main appliance class."""

    TRANSLATIONS = {}

    VALUES_TRANSLATION = {}

    VALUES_SUMMARY = []

    INFO_RESOURCES = []

    @classmethod
    def daikin_to_human(cls, dimension, value):
        """Return converted values from Daikin to Human."""
        return cls.TRANSLATIONS.get(dimension, {}).get(value, str(value))

    @classmethod
    def human_to_daikin(cls, dimension, value):
        """Return converted values from Human to Daikin."""
        translations_rev = {
            dim: {v: k for k, v in item.items()}
            for dim, item in cls.TRANSLATIONS.items()
        }
        return translations_rev.get(dimension, {}).get(value, value)

    @classmethod
    def daikin_values(cls, dimension):
        """Return sorted list of translated values."""
        return sorted(list(cls.TRANSLATIONS[dimension].values()))

    @staticmethod
    async def factory(device_id, session=None):
        """Factory to init the corresponding Daikin class."""
        from .daikin_airbase import (  # pylint: disable=import-outside-toplevel
            DaikinAirBase,
        )
        from .daikin_brp069 import (  # pylint: disable=import-outside-toplevel
            DaikinBRP069,
        )

        appl = DaikinBRP069(device_id, session)
        await appl.update_status(appl.HTTP_RESOURCES[:1])
        if appl.values == {}:
            appl = DaikinAirBase(device_id, session)
        await appl.init()
        return appl

    @staticmethod
    def parse_response(response_body):
        """Parse respose from Daikin."""
        response = dict([e.split('=') for e in response_body.split(',')])
        if 'ret' not in response:
            raise ValueError("missing 'ret' field in response")
        if response['ret'] != 'OK':
            return {}
        if 'name' in response:
            response['name'] = unquote(response['name'])
        return response

    @staticmethod
    def translate_mac(value):
        """Return translated MAC address."""
        return ':'.join(value[i : i + 2] for i in range(0, len(value), 2))

    @staticmethod
    def discover_ip(device_id):
        """Return translated name to ip address."""
        try:
            socket.inet_aton(device_id)
            device_ip = device_id  # id is an IP
        except socket.error:
            device_ip = None

        if device_ip is None:
            # id is a common name, try discovery
            device_name = discovery.get_name(device_id)
            if device_name is None:
                # try DNS
                try:
                    device_ip = socket.gethostbyname(device_id)
                except socket.gaierror:
                    raise ValueError("no device found for %s" % device_id)
            else:
                device_ip = device_name['ip']
        return device_id

    def __init__(self, device_id, session=None):
        """Init the pydaikin appliance, representing one Daikin device."""
        self.values = {}
        self.session = session
        if session:
            self._device_ip = device_id
        else:
            self._device_ip = self.discover_ip(device_id)

    def __getitem__(self, name):
        """Return values from self.value."""
        if name in self.values:
            return self.values[name]
        raise AttributeError("No such attribute: " + name)

    async def init(self):
        """Init status."""
        await self.update_status()

    async def _get_resource(self, resource, retries=3):
        """Update resource."""
        try:
            if self.session and not self.session.closed:
                return await self._run_get_resource(resource)
            async with ClientSession() as self.session:
                return await self._run_get_resource(resource)
        except ServerDisconnectedError as error:
            _LOGGER.debug("ServerDisconnectedError %d", retries)
            if retries == 0:
                raise error
            return await self._get_resource(resource, retries=retries - 1)

    async def _run_get_resource(self, resource):
        """Make the http request."""
        async with self.session.get(f'http://{self._device_ip}/{resource}') as resp:
            if resp.status == 200:
                return self.parse_response(await resp.text())
            return {}

    async def update_status(self, resources=None):
        """Update status from resources."""
        if resources is None:
            resources = self.INFO_RESOURCES
        _LOGGER.debug("Updating %s", resources)
        for resource in resources:
            self.values.update(await self._get_resource(resource))

    def show_values(self, only_summary=False):
        """Print values."""
        if only_summary:
            keys = self.VALUES_SUMMARY
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, val) = self._represent(key)
                print("%18s: %s" % (k, val))

    def _represent(self, key):
        """Return translated value from key."""
        k = self.VALUES_TRANSLATION.get(key, key)

        # adapt the value
        val = self.values[key]

        if key == 'mode' and self.values['pow'] == '0':
            val = 'off'
        elif key == 'mac':
            val = self.translate_mac(val)
            val = unquote(self.values[key]).split(';')
        else:
            val = self.daikin_to_human(key, val)

        _LOGGER.debug('Represent: %s, %s, %s', key, k, val)
        return (k, val)

    def _temperature(self, dimension):
        """Parse temperature."""
        try:
            return float(self.values.get(dimension))
        except ValueError:
            return False

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return 'en_hol' in self.values

    @property
    def support_fan_rate(self):
        """Return True if the device support setting fan_rate."""
        return 'f_rate' in self.values

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return 'f_dir' in self.values

    @property
    def support_outside_temperature(self):
        """Return True if the device is not an AirBase unit."""
        return self.outside_temperature is not None

    @property
    def outside_temperature(self):
        """Return current outside temperature."""
        return self._temperature('otemp')

    @property
    def inside_temperature(self):
        """Return current inside temperature."""
        return self._temperature('htemp')

    @property
    def target_temperature(self):
        """Return current target temperature."""
        return self._temperature('stemp')

    @property
    def fan_rate(self):
        """Return list of supported fan modes."""
        return list(map(str.title, self.TRANSLATIONS.get('f_rate', {}).values()))

    async def set(self, settings):
        """Set settings on Daikin device."""
        raise NotImplementedError

    async def set_holiday(self, mode):
        """Set holiday mode."""
        raise NotImplementedError

    @property
    def zones(self):
        """Return list of zones."""
        return

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        raise NotImplementedError
