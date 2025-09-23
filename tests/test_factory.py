import pytest

from pydaikin.daikin_airbase import DaikinAirBase
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.daikin_brp072c import DaikinBRP072C
from pydaikin.daikin_brp084 import DaikinBRP084
from pydaikin.daikin_skyfi import DaikinSkyFi
from pydaikin.exceptions import DaikinException
from pydaikin.factory import DaikinFactory


class DummyValues(dict):
    def should_resource_be_updated(self, resource):
        return True


@pytest.mark.asyncio
async def test_factory_with_password(monkeypatch):
    monkeypatch.setattr(
        DaikinSkyFi, "__init__", lambda self, ip, session, password: None
    )

    async def dummy_init(self):
        self.values = DummyValues({"mode": "dummy"})

    monkeypatch.setattr(DaikinSkyFi, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2", password="testpw")
    assert isinstance(device, DaikinSkyFi)
    assert "mode" in device.values


@pytest.mark.asyncio
async def test_factory_with_key(monkeypatch):
    monkeypatch.setattr(
        DaikinBRP072C,
        "__init__",
        lambda self, ip, session, key, uuid, ssl_context: None,
    )

    async def dummy_init(self):
        self.values = DummyValues({"mode": "dummy"})

    monkeypatch.setattr(DaikinBRP072C, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2", key="testkey", uuid="uuid")
    assert isinstance(device, DaikinBRP072C)
    assert "mode" in device.values


@pytest.mark.asyncio
async def test_factory_brp084(monkeypatch):
    monkeypatch.setattr(DaikinBRP084, "__init__", lambda self, ip, session: None)

    async def dummy_update_status(self):
        self.values = DummyValues({"mode": "cool"})

    monkeypatch.setattr(DaikinBRP084, "update_status", dummy_update_status)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "cool"})

    monkeypatch.setattr(DaikinBRP084, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DaikinBRP084)
    assert "mode" in device.values


@pytest.mark.asyncio
async def test_factory_brp069(monkeypatch):
    monkeypatch.setattr(
        DaikinBRP084,
        "__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    monkeypatch.setattr(DaikinBRP069, "__init__", lambda self, ip, session: None)

    async def dummy_update_status(self, resources=None):
        self.values = DummyValues({"mode": "heat"})

    monkeypatch.setattr(DaikinBRP069, "update_status", dummy_update_status)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "heat"})

    monkeypatch.setattr(DaikinBRP069, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DaikinBRP069)
    assert "mode" in device.values


@pytest.mark.asyncio
async def test_factory_airbase(monkeypatch):
    # Patch BRP084 and BRP069 to raise so factory falls through to AirBase
    monkeypatch.setattr(
        DaikinBRP084,
        "__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    monkeypatch.setattr(
        DaikinBRP069,
        "__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    monkeypatch.setattr(DaikinAirBase, "__init__", lambda self, ip, session: None)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "fan"})

    monkeypatch.setattr(DaikinAirBase, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DaikinAirBase)
    assert "mode" in device.values
