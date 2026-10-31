"Function to parse responses coming in, used by multiple classes"

import logging
import re
from urllib.parse import unquote

from .exceptions import DaikinCommandRejected

_LOGGER = logging.getLogger(__name__)


def parse_response(response_body, *, strict=False):
    """Parse response from Daikin.

    A non-OK ``ret`` yields an empty dict, or raises DaikinCommandRejected
    (carrying e.g. ``PARAM NG``) when ``strict`` is set.
    """
    _LOGGER.debug("Parsing response: %s", response_body)
    response = dict(
        (match.group(1), match.group(2))
        for match in re.finditer(r'(\w+)=([^=]*)(?:,|$)', response_body)
    )
    if 'ret' not in response:
        raise ValueError("missing 'ret' field in response")
    ret = response.pop('ret')
    if ret != 'OK':
        if strict:
            raise DaikinCommandRejected(ret)
        return {}
    if 'name' in response:
        response['name'] = unquote(response['name'])
    return response
