![PyPI - License](https://img.shields.io/pypi/l/pydaikin?color=green)
![PyPI - Downloads](https://img.shields.io/pypi/dw/pydaikin?label=downloads&logo=pypi&logoColor=white)
![PyPI - Version](https://img.shields.io/pypi/v/pydaikin?label=version&logo=pypi&logoColor=white)

[![Test Python package](https://github.com/fredrike/pydaikin/actions/workflows/pytest.yml/badge.svg)](https://github.com/fredrike/pydaikin/actions/workflows/pytest.yml)
[![Pylint](https://github.com/fredrike/pydaikin/actions/workflows/pylint.yml/badge.svg)](https://github.com/fredrike/pydaikin/actions/workflows/pylint.yml)
[![codecov](https://codecov.io/github/fredrike/pydaikin/graph/badge.svg?token=DFEYF4L0J2)](https://codecov.io/github/fredrike/pydaikin)
![GitHub Pull Requests](https://img.shields.io/github/issues-pr/fredrike/pydaikin?logo=github)
![GitHub Issues](https://img.shields.io/github/issues/fredrike/pydaikin?logo=github)

PyDaikin is a standalone program and a library that interface AirConditioners from Daikin.

Currently the following Daikin WiFi modules are supported:

* BRP069Axx/BRP069Bxx/BRP072Axx
* BRP15B61 aka. AirBase (similar protocol as BRP069Axx)
* BRP072B/Cxx (needs https access and a key)
* BRP084 devices with firmware version 2.8.0 (different API structure)
* SKYFi (different protocol, have a password)

The integration was initially built by Yari Adan, but lately have been taken over by Fredrik Erlandsson.

Here is a simple example code for connecting to a  "BRP069" style AC:
```python
import logging, asyncio
from pydaikin.daikin_base import Appliance
from pydaikin.factory import DaikinFactory

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

async def testDaikin():
    device: Appliance = await DaikinFactory("10.0.0.1")
    device.show_sensors()

asyncio.run(testDaikin())
```

## Firmware Version 2.8.0 Support

Firmware version 2.8.0 uses a different API structure compared to earlier firmware versions. The library now automatically detects the firmware version and uses the appropriate communication method. Confirmed working with:

* FTKM20YVMA with firmware version 2.8.0
* FTXM46WVMA with firmware version 2.8.0
* FTXV80WVMA with firmware version 2.8.0
* FTXA25C2V1BW with firmware version 2.8.0
* FTXA50C2V1BW with firmware version 2.8.0

If you have a device with firmware 2.8.0 that's not working correctly, please open an issue with the device model and provide logs when using the debug mode.

## Unsupported devices

At this moment, following firmware-devices combination aren't supported:

* BRP069C4x with firmware version 2.0.0
