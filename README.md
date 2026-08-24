![PyPI - License](https://img.shields.io/pypi/l/pydaikin?color=green)
![PyPI - Downloads](https://img.shields.io/pypi/dw/pydaikin?label=downloads&logo=pypi&logoColor=white)
![PyPI - Version](https://img.shields.io/pypi/v/pydaikin?label=version&logo=pypi&logoColor=white)

[![Test Python package](https://github.com/fredrike/pydaikin/actions/workflows/pytest.yml/badge.svg)](https://github.com/fredrike/pydaikin/actions/workflows/pytest.yml)
[![Pylint](https://github.com/fredrike/pydaikin/actions/workflows/pylint.yml/badge.svg)](https://github.com/fredrike/pydaikin/actions/workflows/pylint.yml)
[![codecov](https://codecov.io/github/fredrike/pydaikin/graph/badge.svg?token=DFEYF4L0J2)](https://codecov.io/github/fredrike/pydaikin)
![GitHub Pull Requests](https://img.shields.io/github/issues-pr/fredrike/pydaikin?logo=github)
![GitHub Issues](https://img.shields.io/github/issues/fredrike/pydaikin?logo=github)

# PyDaikin

PyDaikin is a Python library for controlling Daikin air conditioners. It provides both a standalone command-line interface and a Python API for integrating Daikin AC control into your applications.

## Supported Devices

The following Daikin WiFi modules are currently supported:

* **BRP069Axx/BRP069Bxx/BRP069B4x/BRP072Axx** - Standard WiFi adapters
* **BRP15B61 (AirBase)** - Uses a similar protocol to BRP069Axx
* **BRP072B/Cxx** - Requires HTTPS access and an authentication key
* **BRP084** - Devices with firmware version 2.8.0 (uses a different API structure)
* **SKYFi** - Uses a different protocol and requires a password

## Quick Start

Here's a simple example for connecting to a Daikin air conditioner:

```python
import asyncio
import logging

import aiohttp
from pydaikin.daikin_base import Appliance
from pydaikin.factory import DaikinFactory

HOST = "10.1.1.21"

logging.basicConfig(level=logging.INFO)
_LOGGER = logging.getLogger(__name__)

async def main():
    async with await DaikinFactory(HOST) as device:
        await device.update_status()
        device.show_sensors()

if __name__ == "__main__":
    asyncio.run(main())
```

The `DaikinFactory` automatically detects your device type and firmware version, creating the appropriate device instance.

## Firmware Version 2.8.0 Support

Firmware version 2.8.0 introduces a different API structure compared to earlier versions. PyDaikin automatically detects and handles this firmware version.

### API structure

Unlike the older CGI-based adapters (BRP069 family), firmware 2.8.0 exposes a single JSON endpoint, `POST /dsiot/multireq`:

* **Status reads** are batch requests containing four `op: 2` entries (indoor unit, outdoor unit, weekly energy and adapter info).
* **Writes** are `op: 3` entries that walk the `dgc_status` tree down to the parameter to change.

Full request/response examples are in [`docs/sample_requests/brp084/`](docs/sample_requests/brp084/README.md).

### Power semantics

The behaviour of `device.set(...)` was validated against the unit's behaviour (see `tests/test_daikin_brp084.py`):

* `device.set({})` turns the unit **on** (the Home Assistant toggle-switch path)
* `device.set({'mode': 'off'})` turns the unit **off**
* `device.set({'mode': 'cool'})` turns the unit **on** and switches mode
* `device.set({'stemp': 25.0})` sets the temperature only; a powered-off unit stays off

### Supported features

* **Comfort airflow, Econo, Outdoor-quiet and Powerful toggles** - Powerful and the trio (Comfort/Econo/Outdoor-quiet) are mutually exclusive, matching the remote's last-button-pressed-wins behaviour
* **Discrete vertical vane control** - `off`, `down` (floor) and `swing`
* **Swing** on the vertical and horizontal axes, per mode
* **Sensors** - indoor/outdoor temperature, humidity, compressor temperature, decoded indoor/outdoor model strings and adapter firmware/API version
* **Energy data** - daily runtime and weekly consumption
* **Sub-zero outdoor temperatures** - sensor values are decoded as little-endian signed hex, so negative readings are handled correctly
* **Auto mode without a setpoint** - some units (e.g. the Urusara X, model `W-SRTA322F`) only expose cool/hot setpoints and report no auto setpoint (`e_3001/p_1D`); the target temperature then degrades to `--` instead of failing `init()` (issue [#72](https://github.com/fredrike/pydaikin/issues/72))

**Confirmed working with:**

* FTKM20YVMA
* FTXM46WVMA
* FTXV80WVMA
* FTXA25C2V1BW
* FTXA50C2V1BW

If you have a device with firmware 2.8.0 that is not working correctly, please open an issue with your device model and debug logs.

## Unsupported Devices

The following device and firmware combinations are not currently supported:

* BRP069C4x with firmware version 2.0.0
* Adapters with Onecta firmware below 2.8.0 (e.g. the built-in WiFi adapter of
  newer Stylish units such as FTXA20C2V1BW, and BRP069C4x/C8x gateways running
  2.3.x-2.6.x). These answer UDP discovery with `type=GPF,protocol=DGC` but
  return 404 for every local HTTP endpoint - there is no local control API.
  Local control requires adapter firmware 2.8.0 or later; until then use a
  cloud-based integration ([#153](https://github.com/fredrike/pydaikin/issues/153),
  [#83](https://github.com/fredrike/pydaikin/issues/83))

## About

PyDaikin was originally created by Yari Adan and is currently maintained by Fredrik Erlandsson.
