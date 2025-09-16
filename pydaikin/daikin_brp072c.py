"""Pydaikin appliance, represent a Daikin device."""

import logging
import ssl
from uuid import NAMESPACE_OID, uuid3

from .daikin_brp069 import DaikinBRP069

_LOGGER = logging.getLogger(__name__)


class DaikinBRP072C(DaikinBRP069):
    """Daikin class for BRP072Cxx units."""

    def __init__(  # pylint: disable=[too-many-arguments]
        self,
        device_id,
        session=None,
        *,
        key=None,
        uuid=None,
        ssl_context=None,
    ) -> None:
        """Init the pydaikin appliance, representing one Daikin AirBase
        (BRP15B61) device."""
        super().__init__(device_id, session)
        self._key = key
        if uuid is None:
            uuid = uuid3(NAMESPACE_OID, 'pydaikin')
        self._uuid = str(uuid).replace('-', '')
        self.headers = {"X-Daikin-uuid": self._uuid}
        self.ssl_context = (
            ssl_context
            if ssl_context
            else ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        )
        self.ssl_context.options |= ssl.OP_LEGACY_SERVER_CONNECT
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        self.base_url = f"https://{self.device_ip}"

    async def init(self):
        """Init status."""
        await self._get_resource('common/register_terminal', {"key": self._key})
        await super().init()
