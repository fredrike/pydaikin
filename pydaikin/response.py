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

    # Translate swing mode from 2 parameters to 1 (Special case for certain models e.g Alira X)
    if response.get("f_dir_ud") == "0" and response.get("f_dir_lr") == "0":
        response["f_dir"] = '0'
    if response.get("f_dir_ud") == "S" and response.get("f_dir_lr") == "0":
        response["f_dir"] = '1'
    if response.get("f_dir_ud") == "0" and response.get("f_dir_lr") == "S":
        response["f_dir"] = '2'
    if response.get("f_dir_ud") == "S" and response.get("f_dir_lr") == "S":
        response["f_dir"] = '3'

    return response
