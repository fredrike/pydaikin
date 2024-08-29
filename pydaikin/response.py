"Function to parse responses coming in, used by multiple classes"
import re
from urllib.parse import unquote


def parse_response(response_body):
    """Parse response from Daikin."""
    response = dict(
        (match.group(1), match.group(2))
        for match in re.finditer(r'(\w+)=([^=]*)(?:,|$)', response_body)
    )
    if 'ret' not in response:
        raise ValueError("missing 'ret' field in response")
    if response.pop('ret') != 'OK':
        return {}
    if 'name' in response:
        response['name'] = unquote(response['name'])
    return response
