"""Test BRP069 control writes: strict replies, pre-read, recovery, locking."""

import asyncio

from aiohttp import ClientSession, ClientTimeout
import pytest
import pytest_asyncio

from pydaikin.daikin_airbase import DaikinAirBase
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.exceptions import DaikinCommandRejected, DaikinException
from pydaikin.response import parse_response

from .brp069_helpers import (
    CONTROL,
    GET,
    SET,
    TIMED_OUT,
    add_routes,
    mock_reply,
    reset_connection,
    sent,
    slow_ok,
)


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.parametrize(
    ("body", "strict", "expected"),
    [
        ("ret=OK,stemp=23.5", False, {"stemp": "23.5"}),
        ("ret=OK,stemp=23.5", True, {"stemp": "23.5"}),
        ("ret=PARAM NG", False, {}),
        ("ret=PARAM NG", True, DaikinCommandRejected),
    ],
)
def test_parse_response_strict(body, strict, expected):
    """Reads keep returning {} on errors; strict writes raise with ret."""
    if expected is DaikinCommandRejected:
        with pytest.raises(DaikinCommandRejected, match="PARAM NG"):
            parse_response(body, strict=strict)
    else:
        assert parse_response(body, strict=strict) == expected


@pytest.mark.parametrize(
    ("reply", "error", "sends"),
    [
        (slow_ok, asyncio.TimeoutError, 1),
        # aiohttp itself resends an idempotent GET once when a reused keep-alive
        # connection drops without an answer (RFC 9112); it is the same request
        (reset_connection, Exception, 2),
        ((403, "Forbidden"), Exception, 1),
        ((404, "Not Found"), Exception, 1),
        ((500, "Error"), Exception, 1),
    ],
    ids=["timeout", "reset", "http403", "http404", "http500"],
)
@pytest.mark.parametrize("stemp", ["23.5", "23"])
@pytest.mark.asyncio
async def test_failed_write_is_sent_once(
    aresponses, client_session, reply, error, sends, stemp
):
    """pydaikin never repeats a write: the device may have applied it anyway."""
    add_routes(aresponses, ["22.0"], [])
    aresponses.add(path_pattern=SET, response=mock_reply(aresponses, reply))
    aresponses.add(path_pattern=GET, response="ret=NG")  # read-back fails too
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)
    TIMED_OUT.clear()

    with pytest.raises(error):
        await device.set({"stemp": stemp})

    assert [r["stemp"] for r in sent(aresponses) + TIMED_OUT] == [stemp] * sends
    # Outcome unknown: neither the old nor the requested setpoint is cached
    assert len(sent(aresponses, GET)) == 2
    assert "stemp" not in device.values
    assert device.values.get("mode", invalidate=False) == "4"
    assert device.values.should_resource_be_updated("aircon/get_control_info")


@pytest.mark.asyncio
async def test_cancelled_set_releases_lock(aresponses, client_session):
    """Cancelling set() mid-write forgets the setpoint and lets polling continue."""
    add_routes(aresponses, ["22.0", "22.0"], [])
    aresponses.add(path_pattern=SET, response=slow_ok)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    TIMED_OUT.clear()
    task = asyncio.create_task(device.set({"stemp": "23.5"}))
    async with asyncio.timeout(2):
        while not TIMED_OUT:  # the write has reached the device
            await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert "stemp" not in device.values
    async with asyncio.timeout(2):  # the lock was released
        await device.update_status(["aircon/get_control_info"])
    assert device.values.get("stemp", invalidate=False) == "22.0"


@pytest.mark.parametrize(
    "pre_read",
    [
        "ret=NG",
        (404, "Not Found"),
        "ret=OK,mode=4,stemp=22.0,shum=0",  # no pow
        "ret=OK,pow=0,stemp=22.0,shum=0",  # no mode
        "ret=OK,pow=0,mode=4,shum=0",  # no stemp
        "ret=OK,pow=0,mode=4,stemp=22.0",  # no shum
    ],
    ids=["ret_ng", "http404", "no_pow", "no_mode", "no_stemp", "no_shum"],
)
@pytest.mark.parametrize("cached", [False, True], ids=["empty_cache", "old_cache"])
@pytest.mark.parametrize("settings", [{"stemp": "23.5"}, {"mode": "cool"}])
@pytest.mark.asyncio
async def test_invalid_pre_read_sends_nothing(
    aresponses, client_session, pre_read, cached, settings
):
    """Without a valid device snapshot nothing is written and nothing cached."""
    reply = pre_read if isinstance(pre_read, str) else mock_reply(aresponses, pre_read)
    aresponses.add(path_pattern=GET, response=reply)
    device = DaikinBRP069("192.168.1.100", session=client_session)
    if cached:
        device.values.update_by_resource(
            "aircon/get_control_info", parse_response(CONTROL.format(stemp="22.0"))
        )
    before = dict(device.values)

    with pytest.raises(DaikinException):
        await device.set(settings)

    assert not sent(aresponses)
    assert dict(device.values) == before


@pytest.mark.parametrize(
    ("control", "settings"),
    [
        (CONTROL.replace("mode=4", "mode=2").replace("stemp={stemp}", "stemp=M"), {}),
        (CONTROL, {"mode": "fan"}),
        (CONTROL, {"mode": "dry"}),
    ],
    ids=["dry_stemp_M", "to_fan", "to_dry"],
)
@pytest.mark.asyncio
async def test_sentinel_setpoints_still_write(
    aresponses, client_session, control, settings
):
    """stemp=M or --, as in dry/fan mode, is a valid snapshot."""
    add_routes(aresponses, ["22.0"], ["ret=OK"], control)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    await device.set({**settings, "f_rate": "auto"})

    assert len(sent(aresponses)) == 1


APPLIED = CONTROL.replace("pow=0,mode=4", "pow=1,mode=3").format(stemp="23.5")


@pytest.mark.parametrize(
    ("resync", "mode", "stemp"),
    [
        (APPLIED, "3", "23.5"),  # read back: the device did apply the write
        ("ret=NG", "4", None),  # unreadable: last read state, refetched later
    ],
    ids=["resync_ok", "resync_failed"],
)
@pytest.mark.parametrize(
    "settings", [{"mode": "cool"}, {"mode": "cool", "stemp": "23.5"}]
)
@pytest.mark.asyncio
async def test_unknown_outcome_reads_state_back(
    aresponses, client_session, resync, mode, stemp, settings
):
    """After a lost answer the cache shows the device state, not the request."""
    add_routes(aresponses, ["22.0"], [])
    aresponses.add(path_pattern=SET, response=slow_ok)
    aresponses.add(path_pattern=GET, response=resync)
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)

    with pytest.raises(asyncio.TimeoutError):
        await device.set(settings)

    if stemp is None:  # resync failed: the last read state must be refetched
        assert device.values.should_resource_be_updated("aircon/get_control_info")
    assert device.values.get("mode", invalidate=False) == mode
    if stemp is None and "stemp" in settings:
        assert "stemp" not in device.values
    elif stemp is not None:
        assert device.values.get("stemp", invalidate=False) == stemp
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_resync_is_time_boxed(aresponses, client_session):
    """A hanging read-back does not delay the error beyond RESYNC_TIMEOUT."""
    add_routes(aresponses, ["22.0"], [])
    aresponses.add(path_pattern=SET, response=mock_reply(aresponses, (500, "Error")))
    aresponses.add(path_pattern=GET, response=slow_ok)
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.RESYNC_TIMEOUT = 0.1

    async with asyncio.timeout(0.8):
        with pytest.raises(Exception):  # the write error, not the resync timeout
            await device.set({"stemp": "23.5"})

    assert "stemp" not in device.values


@pytest.mark.asyncio
async def test_airbase_set_without_shum(aresponses, client_session):
    """AirBase units without shum still write, using the "--" default."""
    aresponses.add(
        path_pattern="/skyfi/aircon/get_control_info",
        response="ret=OK,pow=1,mode=2,stemp=22.0,f_rate=A,f_dir=0,f_auto=0",
    )
    aresponses.add(path_pattern="/skyfi/aircon/set_control_info", response="ret=OK")
    device = DaikinAirBase("192.168.1.100", session=client_session)
    device.values.update(device.DEFAULTS)

    await device.set({"stemp": "23"})

    assert sent(aresponses, "/skyfi/aircon/set_control_info")[0]["shum"] == "--"


@pytest.mark.parametrize(
    "settings",
    # 23.2 is not a half degree, so a later fallback layer leaves it alone too
    [{"stemp": "23"}, {"stemp": "23.2"}, {"mode": "cool"}, {"f_rate": "auto"}],
)
@pytest.mark.parametrize("ret", ["ret=PARAM NG", "ret=NG"])
@pytest.mark.asyncio
async def test_rejected_write_restores_cache(aresponses, client_session, settings, ret):
    """A rejected write is raised once; the cache shows the state read before."""
    add_routes(aresponses, ["22.0"], [ret])
    device = DaikinBRP069("192.168.1.100", session=client_session)

    with pytest.raises(DaikinCommandRejected) as err:
        await device.set(settings)

    assert err.value.ret == ret.removeprefix("ret=")
    assert len(sent(aresponses)) == 1
    assert device.values.should_resource_be_updated("aircon/get_control_info")
    assert device.values.get("stemp", invalidate=False) == "22.0"
    assert device.values.get("mode", invalidate=False) == "4"
    aresponses.assert_no_unused_routes()


@pytest.mark.parametrize(
    ("second", "writes", "tail"),
    [
        ("set", ["ret=OK", "ret=OK"], [(GET, None), (SET, "24")]),
        ("poll", ["ret=OK"], [(GET, None)]),
    ],
)
@pytest.mark.asyncio
async def test_concurrent_writes_and_polls_are_serialised(
    aresponses, client_session, second, writes, tail
):
    """A set() or poll waits until a running set() has written."""
    add_routes(aresponses, ["22.0", "23.0"], writes)
    device = DaikinBRP069("192.168.1.100", session=client_session)
    other = (
        device.set({"stemp": "24"})
        if second == "set"
        else device.update_status(["aircon/get_control_info"], force_refresh=True)
    )

    await asyncio.gather(device.set({"stemp": "23"}), other)

    order = [(h.request.path, h.request.query.get("stemp")) for h in aresponses.history]
    assert order == [(GET, None), (SET, "23"), *tail]
    aresponses.assert_no_unused_routes()
