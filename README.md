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

* **BRP069Axx/BRP069Bxx/BRP072Axx** - Standard WiFi adapters
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

## About

PyDaikin was originally created by Yari Adan and is currently maintained by Fredrik Erlandsson.
