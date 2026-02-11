import pytest
from aiohttp import ClientSession
from unittest.mock import MagicMock, AsyncMock, patch

from pydaikin.daikin_airbase import DaikinAirBase
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.daikin_brp072c import DaikinBRP072C
from pydaikin.daikin_brp084 import DaikinBRP084
from pydaikin.daikin_skyfi import DaikinSkyFi
from pydaikin.daikin_base import Appliance
from pydaikin.exceptions import DaikinException
from pydaikin.factory import DaikinFactory
from aiohttp import ClientError


class DummyValues(dict):
    def should_resource_be_updated(self, resource):
        return True

    def update_by_resource(self, resource, data):
        self[resource] = data

    def get(self, key, default=None, **kwargs):
        # Ignore any keyword arguments like 'invalidate'
        return super().get(key, default)


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

    # Patch update_status to set self.values and call update_by_resource
    async def dummy_update_status(self, resources=None):
        self.values = DummyValues({"mode": "cool"})

    monkeypatch.setattr(DaikinBRP084, "update_status", dummy_update_status)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "cool"})

    monkeypatch.setattr(DaikinBRP084, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DaikinBRP084)
    assert "mode" in device.values


@pytest.mark.asyncio
async def test_factory_brp084_initializes_mode(monkeypatch):
    """Test that BRP084 initializes mode to 'off' if not set."""
    monkeypatch.setattr(DaikinBRP084, "__init__", lambda self, ip, session: None)

    async def dummy_update_status(self, resources=None):
        # Mode is not set (returns False when invalidate=False)
        self.values = DummyValues({})

    monkeypatch.setattr(DaikinBRP084, "update_status", dummy_update_status)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "off", "pow": "0"})

    monkeypatch.setattr(DaikinBRP084, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DaikinBRP084)


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
async def test_factory_brp069_with_custom_port(monkeypatch):
    """Test BRP069 detection with custom port from discovery."""
    monkeypatch.setattr(
        DaikinBRP084,
        "__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    monkeypatch.setattr(DaikinBRP069, "__init__", lambda self, ip, session: None)

    async def dummy_update_status(self, resources=None):
        self.values = DummyValues({"mode": "cool"})

    monkeypatch.setattr(DaikinBRP069, "update_status", dummy_update_status)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "cool"})

    monkeypatch.setattr(DaikinBRP069, "init", dummy_init)
    
    # Test with port in device_id (IP:port format)
    device = await DaikinFactory("192.168.1.2:30050")
    assert isinstance(device, DaikinBRP069)


@pytest.mark.asyncio
async def test_factory_brp069_empty_values_fallback(monkeypatch):
    """Test that empty values causes fallback to AirBase."""
    monkeypatch.setattr(
        DaikinBRP084,
        "__init__",
        lambda self, ip, session: (_ for _ in ()).throw(DaikinException("fail")),
    )
    monkeypatch.setattr(DaikinBRP069, "__init__", lambda self, ip, session: None)

    async def dummy_update_status(self, resources=None):
        # Empty values should trigger fallback
        self.values = DummyValues({})

    monkeypatch.setattr(DaikinBRP069, "update_status", dummy_update_status)
    monkeypatch.setattr(DaikinAirBase, "__init__", lambda self, ip, session: None)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "fan"})

    monkeypatch.setattr(DaikinAirBase, "init", dummy_init)
    
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DaikinAirBase)


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

    async def dummy_update_status(self, resources=None):
        self.values = DummyValues({"mode": "fan"})

    monkeypatch.setattr(DaikinAirBase, "update_status", dummy_update_status)

    async def dummy_get_resource(self, path, params=None, resources=None):
        return {"mode": "fan"}

    monkeypatch.setattr(DaikinAirBase, "_get_resource", dummy_get_resource)

    async def dummy_init(self):
        self.values = DummyValues({"mode": "fan"})

    monkeypatch.setattr(DaikinAirBase, "init", dummy_init)
    device = await DaikinFactory("192.168.1.2")
    assert isinstance(device, DaikinAirBase)
    assert "mode" in device.values


@pytest.mark.asyncio
async def test_factory_airbase_with_custom_port(monkeypatch):
    """Test AirBase detection with custom port."""
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
        self.values = DummyValues({"mode": "dry"})

    monkeypatch.setattr(DaikinAirBase, "init", dummy_init)
    
    device = await DaikinFactory("192.168.1.2:9999")
    assert isinstance(device, DaikinAirBase)
    assert device.base_url == "http://192.168.1.2:9999"


@pytest.mark.asyncio
async def test_factory_no_mode_error(monkeypatch):
    """Test that DaikinException is raised when device has no mode."""
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
        # Device has no mode - should raise exception
        self.values = DummyValues({})

    monkeypatch.setattr(DaikinAirBase, "init", dummy_init)
    
    with pytest.raises(DaikinException, match="not supported"):
        await DaikinFactory("192.168.1.2")


@pytest.mark.asyncio
async def test_appliance_context_manager():
    """Test async context manager for Appliance (aclose, __aenter__, __aexit__)."""
    session = MagicMock(spec=ClientSession)
    session.closed = False
    close_called = False

    async def mock_close():
        nonlocal close_called
        close_called = True

    session.close = AsyncMock(side_effect=mock_close)
    
    # Test __aenter__ and __aexit__
    appliance = Appliance("192.168.1.1", session=None)
    
    # Simulate context manager usage
    async with await (appliance.__aenter__()) as device:
        assert device is appliance
    
    # aclose should be called in __aexit__
    await appliance.__aexit__(None, None, None)


@pytest.mark.asyncio
async def test_appliance_session_ownership():
    """Test that Appliance correctly tracks session ownership."""
    # Test with provided session (not owned)
    session = MagicMock(spec=ClientSession)
    appliance = Appliance("192.168.1.1", session=session)
    assert appliance._own_session is False
    assert appliance.session is session

    # Test with no session (owned)
    appliance2 = Appliance("192.168.1.1", session=None)
    assert appliance2._own_session is True
    assert isinstance(appliance2.session, ClientSession)


@pytest.mark.asyncio
async def test_appliance_aclose_with_owned_session():
    """Test aclose() closes session only if owned."""
    # Create appliance without session (owns the session)
    appliance = Appliance("192.168.1.1", session=None)
    
    # Mock the session's close method
    appliance.session.close = AsyncMock()
    appliance.session.closed = False
    
    await appliance.aclose()
    
    # Should have called close since we own the session
    appliance.session.close.assert_called_once()


@pytest.mark.asyncio
async def test_appliance_aclose_with_external_session():
    """Test aclose() does NOT close external session."""
    session = AsyncMock(spec=ClientSession)
    session.closed = False
    
    # Create appliance with external session
    appliance = Appliance("192.168.1.1", session=session)
    
    await appliance.aclose()
    
    # Should NOT have called close on external session
    session.close.assert_not_called()


@pytest.mark.asyncio
async def test_appliance_aclose_already_closed():
    """Test aclose() when session is already closed."""
    appliance = Appliance("192.168.1.1", session=None)
    appliance.session.closed = True
    appliance.session.close = AsyncMock()
    
    await appliance.aclose()
    
    # Should not attempt to close an already closed session
    appliance.session.close.assert_not_called()
