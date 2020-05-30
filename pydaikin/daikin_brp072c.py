"""Pydaikin appliance, represent a Daikin device."""

import logging
from uuid import NAMESPACE_OID, uuid3

from aiohttp.web_exceptions import HTTPForbidden

from .daikin_brp069 import DaikinBRP069

_LOGGER = logging.getLogger(__name__)


class DaikinBRP072C(DaikinBRP069):
    """Daikin class for BRP072Cxx units."""

    def __init__(self, device_id, session=None, key=None, uuid=None):
        """Init the pydaikin appliance, representing one Daikin AirBase (BRP15B61) device."""
        super().__init__(device_id, session)
        self._key = key
        if uuid is None:
            uuid = uuid3(NAMESPACE_OID, 'pydaikin')
        self._uuid = str(uuid).replace('-', '')
        self._headers = {"X-Daikin-uuid": self._uuid}

    async def init(self):
        """Init status."""
        await self._get_resource(f'common/register_terminal?key={self._key}')
        await super().init()

    async def _run_get_resource(self, resource):
        """Make the http request."""
        async with self.session.get(
            f'https://{self._device_ip}/{resource}', headers=self._headers, ssl=False,
        ) as resp:
            if resp.status == 200:
                return self.parse_response(await resp.text())
            elif resp.status == 403:
                raise HTTPForbidden
        return {}
