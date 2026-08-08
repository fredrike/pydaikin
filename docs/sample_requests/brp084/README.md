# BRP084 (firmware version 2.8.0)

Sample request/response data for Daikin WiFi adapters running firmware version
2.8.0, which uses a very different API from the BRP069-family adapters.

Instead of the old `basic_info`/`get_control_info` CGI endpoints, firmware 2.8.0
exposes a single JSON endpoint:

```
POST /dsiot/multireq
Content-Type: application/json
```

Status reads send a batch of `op: 2` (read) requests; writes send a single
`op: 3` (write) request. The response always contains a `responses` array with
one entry per requested path, identified by the `fr` field.

The request/response bodies below match the mocked responses used in
`tests/test_daikin_brp084.py`.

## Files

- `update_status_request.json` - batch status read (POST body for `/dsiot/multireq`)
- `update_status_response.json` - status read response
- `set_request.json` - set mode to cool / 26 °C / fan auto / swing both (POST body)
- `set_response.json` - response to a write request
