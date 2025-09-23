import pytest

from pydaikin.daikin_brp072c import DaikinBRP072C
from pydaikin.daikin_skyfi import DaikinSkyFi
from pydaikin.exceptions import DaikinException
from pydaikin.factory import DaikinFactory


@pytest.mark.asyncio
async def test_factory_with_password(monkeypatch):
    monkeypatch.setattr(
        "pydaikin.daikin_skyfi.DaikinSkyFi.__init__",
        lambda self, ip, session, password: None,
    )
    device = await DaikinFactory("192.168.1.2", password="testpw")
    assert isinstance(device, DaikinSkyFi)


@pytest.mark.asyncio
async def test_factory_with_key(monkeypatch):
    monkeypatch.setattr(
        "pydaikin.daikin_brp072c.DaikinBRP072C.__init__",
        lambda self, ip, session, key, uuid, ssl_context: None,
    )
    device = await DaikinFactory("192.168.1.2", key="testkey", uuid="uuid")
    assert isinstance(device, DaikinBRP072C)


@pytest.mark.asyncio
async def test_factory_brp084(monkeypatch):
    class DummyBRP084:
        def __init__(self, ip, session):
            pass

        async def update_status(self):
            pass

        values = {"mode": "cool"}

    monkeypatch.setattr("pydaikin.daikin_brp084.DaikinBRP084", DummyBRP084)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DummyBRP084)


@pytest.mark.asyncio
async def test_factory_brp069(monkeypatch):
    class DummyBRP069:
        def __init__(self, ip, session):
            pass

        values = {"mode": "heat"}

    monkeypatch.setattr("pydaikin.daikin_brp069.DaikinBRP069", DummyBRP069)
    # Patch BRP084 to fail
    monkeypatch.setattr(
        "pydaikin.daikin_brp084.DaikinBRP084.__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DummyBRP069)


@pytest.mark.asyncio
async def test_factory_airbase(monkeypatch):
    class DummyAirBase:
        def __init__(self, ip, session):
            pass

        values = {"mode": "fan"}

    # Patch BRP084 and BRP069 to fail
    monkeypatch.setattr(
        "pydaikin.daikin_brp084.DaikinBRP084.__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    monkeypatch.setattr(
        "pydaikin.daikin_brp069.DaikinBRP069.__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    monkeypatch.setattr("pydaikin.daikin_airbase.DaikinAirBase", DummyAirBase)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DummyAirBase)
