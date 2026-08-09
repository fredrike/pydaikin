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
- `update_status_response.json` - status read response (cool mode)
- `update_status_response_auto_mode.json` - status read response while the unit is
  in **auto** mode (Urusara X, model `W-SRTA322F`; captured for issue #72)
- `set_request.json` - set mode to cool / 26 °C / fan auto / swing both (POST body)
- `set_response.json` - response to a write request

## Insights

### Auto mode does not always expose a target temperature

The `adr_0100.dgc_status` payload in `update_status_response_auto_mode.json` shows
a unit running in **auto** mode (`e_3001/p_01 = "0300"`). It reports cool and hot
setpoints (`p_02` = `"34"` = 26 °C, `p_03` = `"32"` = 25 °C) but **no auto setpoint**
(`p_1D`), which is what the parser looks for via `temp_settings["auto"]`.

Heat-pump-only units such as the Urusara X (model `W-SRTA322F`) therefore never
report `p_1D`. This used to abort `init()` with `"Error extracting values: Key p_1D
not found"` (see [issue #72](https://github.com/fredrike/pydaikin/issues/72)).
`update_status()` now falls back to `stemp = "--"` (the same value Drying mode
produces) instead of failing, and `target_temperature` returns `None`. The behaviour
is covered by
`tests/test_daikin_brp084.py::test_update_status_auto_mode_missing_temp_setpoint`.
