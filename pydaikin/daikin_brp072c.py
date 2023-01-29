"""Pydaikin appliance, represent a Daikin device."""

import logging
import ssl
from uuid import NAMESPACE_OID, uuid3

from .daikin_brp069 import DaikinBRP069

_LOGGER = logging.getLogger(__name__)


class DaikinBRP072C(DaikinBRP069):
    """Daikin class for BRP072Cxx units."""

    def __init__(self, device_id, session=None, key=None, uuid=None):
        """Init the pydaikin appliance, representing one Daikin AirBase
        (BRP15B61) device."""
        super().__init__(device_id, session)
        self._key = key
        if uuid is None:
            uuid = uuid3(NAMESPACE_OID, 'pydaikin')
        self._uuid = str(uuid).replace('-', '')
        self._headers = {"X-Daikin-uuid": self._uuid}
        self._ssl_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        # SSL_OP_LEGACY_SERVER_CONNECT, https://github.com/python/cpython/issues/89051
        self._ssl_context.options |= 0x4
        self._ssl_context.check_hostname = False
        self._ssl_context.verify_mode = ssl.CERT_NONE

    async def init(self):
        """Init status."""
        await self._get_resource(f'common/register_terminal?key={self._key}')
        await super().init()

    async def _run_get_resource(self, resource):
        """Make the http request."""
        async with self.session.get(
            f'https://{self._device_ip}/{resource}',
            headers=self._headers,
            ssl=self._ssl_context,
        ) as resp:
            return await self._handle_response(resp)
