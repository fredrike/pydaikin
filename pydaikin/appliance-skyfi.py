"""Pydaikin appliance, represent a Daikin device."""

import logging
import socket

import pydaikin.discovery as discovery
import pydaikin.entity as entity
import pydaikin.appliance as Appliance

_LOGGER = logging.getLogger(__name__)

SKYFI_RESOURCES = [
    'ac.cgi?',
]

VALUES_SUMMARY_SKYFI = [
    'opmode',
    'settemp',
    'fanspeed',
    'fanflags',
    'acmode',
    'roomtemp',
    'outsidetemp',
    'zone',
    'flt',
]

VALUES_TRANSLATION_SKYFI = {
    'opmode': 'power',
    'settemp': 'target temp',
    'fanspeed': 'fan rate',
    'fanflags': 'fan direction',
    'acmode': 'mode',
    'roomtemp': 'inside temp',
    'outsidetemp': 'outside temp',
    'err': 'error code',
    'en_hol': 'away_mode',
}


TRANSLATIONS_SKYFI = {  # Needs updating
    'mode': {'0': 'fan', '1': 'hot', '2': 'cool', '7': 'dry'},
    'f_rate': {'1': 'low', '3': 'mid', '5': 'high'},
    'f_dir': {'0': 'off', '1': 'vertical', '2': 'horizontal', '3': '3d'},
}


def daikin_to_human(dimension, value):
    """Return converted values from Daikin to Human."""
    translations = TRANSLATIONS_SKYFI
    return translations.get(dimension, {}).get(value, str(value))


def human_to_daikin(dimension, value):
    """Return converted values from Human to Daikin."""
    translations = TRANSLATIONS_SKYFI
    translations_rev = {
        dim: {v: k for k, v in item.items()} for dim, item in translations.items()
    }
    return translations_rev.get(dimension, {}).get(value, value)


def daikin_values(dimension):
    """Return sorted list of translated values."""
    return sorted(list(TRANSLATIONS_SKYFI[dimension].values()))


class Appliance_SkyFi(Appliance):
    """Daikin appliance class."""

    def __init__(self, id, password, session=None):
        """Init the pydaikin appliance, representing one Daikin device."""
        entity.Entity.__init__(self)
        self._password = password
        self._fan_rate = TRANSLATIONS_SKYFI['f_rate']
        self.session = session

        if session:
            self.ip = id
            return

        try:
            socket.inet_aton(id)
            ip = id  # id is an IP
        except socket.error:
            ip = None

        if ip is None:
            # id is a common name, try discovery
            e = discovery.get_name(id)
            if e is None:
                # try DNS
                try:
                    ip = socket.gethostbyname(id)
                except socket.gaierror:
                    raise ValueError("no device found for %s" % id)
            else:
                ip = e['ip']

        self.ip = ip

    async def init(self):
        """Init status."""
        await self.update_status(SKYFI_RESOURCES)

    @property
    def fan_rate(self):
        """Return list of supported fan modes."""
        return list(map(str.title, self._fan_rate.values()))

    @property
    def support_away_mode(self):
        """Return True if the device support away_mode."""
        return False

    @property
    def support_fan_rate(self):
        """Return True if the device support setting fan_rate."""
        return True

    @property
    def support_swing_mode(self):
        """Return True if the device support setting swing_mode."""
        return False

    def parse_response(self, body):
        """FIXME: Map the parsed data to general Daikin format."""
        response = super().parse_response(body)
        return response

    async def _get_resource(self, resource):
        """Make the http request."""
        resource = "{}pass={}".format(resource, self._password)
        return await super()._get_resource(resource)

    async def update_status(self, resources=SKYFI_RESOURCES):
        """Update status from resources."""
        super().update_status(resources)

    def show_values(self, only_summary=False):
        """Print values."""
        if only_summary:
            keys = VALUES_SUMMARY_SKYFI
        else:
            keys = sorted(self.values.keys())

        for key in keys:
            if key in self.values:
                (k, v) = self.represent(key)
                print("%18s: %s" % (k, v))

    def represent(
        self, key
    ):  # FIXME: should use the parent class (make sure it works).
        """Return translated value from key."""
        from urllib.parse import unquote

        # adapt the key
        k = VALUES_TRANSLATION_SKYFI.get(key, key)

        # adapt the value
        v = self.values[key]

        if key == 'mode' and self.values['pow'] == '0':
            v = 'off'
        elif key == 'mac':
            v = self.translate_mac(v)
        elif key in ['zone_name', 'zone_onoff']:
            v = unquote(self.values[key]).split(';')
        else:
            v = daikin_to_human(key, v, self._airbase)

        _LOGGER.debug('Represent: %s, %s, %s', key, k, v)
        return (k, v)

    async def set(self, settings):
        """Set settings on Daikin device."""
        # start with current values
        current_val = await self.get_resource('ac.cgi?')

        # Merge current_val with mapped settings
        self.values.update(
            current_val
        )  # FIXME: make sure that the get_resource mappes correctly.
        self.values.update(
            {k: human_to_daikin(k, v, self._airbase) for k, v in settings.items()}
        )

        # we are using an extra mode "off" to power off the unit
        if settings.get('mode', '') == 'off':
            self.values['pow'] = '0'
        else:
            self.values['pow'] = '1'

        query_c = 'set.cgi?p={pow}&t={stemp}&f={f_rate}&m={mode}'.format(**self.values)

        _LOGGER.debug("Sending query_c: %s", query_c)
        await self.get_resource(query_c)

    # FIXME: Zones needs a rework.
    @property
    def zones(self):
        """Return list of zones."""
        if not self.values.get('zone_name'):
            return
        zone_onoff = self.represent('zone_onoff')[1]
        return [
            (name.strip(' +,'), zone_onoff[i])
            for i, name in enumerate(self.represent('zone_name')[1])
        ]

    async def set_zone(self, zone_id, status):
        """Set zone status."""
        from urllib.parse import quote

        current_state = await self.get_resource('aircon/get_zone_setting')
        self.values.update(current_state)
        zone_onoff = self.represent('zone_onoff')[1]
        zone_onoff[zone_id] = status
        self.values['zone_onoff'] = quote(';'.join(zone_onoff)).lower()

        query = 'aircon/set_zone_setting?zone_name={}&zone_onoff={}'.format(
            current_state['zone_name'], self.values['zone_onoff'],
        )

        _LOGGER.debug("Set zone:: %s", query)
        await self.get_resource(query)

    @property
    def outside_temperature(self):
        """Return current outside temperature."""
        return self._temperature(
            'otemp'
        )  # FIXME: the parsed data should be mapped to this..

    @property
    def inside_temperature(self):
        """Return current inside temperature."""
        return self._temperature(
            'htemp'
        )  # FIXME: the parsed data should be mapped to this..

    @property
    def target_temperature(self):
        """Return current target temperature."""
        return self._temperature(
            'stemp'
        )  # FIXME: the parsed data should be mapped to this..
