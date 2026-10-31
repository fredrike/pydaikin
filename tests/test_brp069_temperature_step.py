"""Test adaptive target temperature step detection on BRP069 (issue #168)."""

import asyncio

from aiohttp import ClientSession, ClientTimeout, web
import pytest
import pytest_asyncio

from pydaikin.daikin_airbase import DaikinAirBase
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.daikin_brp072c import DaikinBRP072C
from pydaikin.daikin_brp084 import DaikinBRP084
from pydaikin.exceptions import (
    DaikinCommandRejected,
    DaikinException,
    DaikinVerificationError,
)
from pydaikin.response import parse_response

# Real get_control_info of a Stylish (0FC1, adapter 4_2_303), unit off in heat mode
CONTROL = (
    "ret=OK,pow=0,mode=4,adv=13,stemp={stemp},shum=0,dt1=25.0,dt2=M,dt3=25.5,"
    "dt4={stemp},dt5={stemp},dt7=25.0,dh1=0,dh2=50,dh3=0,dh4=0,dh5=0,dh7=0,dhh=50,"
    "b_mode=4,b_stemp={stemp},b_shum=0,alert=255,f_rate=B,b_f_rate=B,dfr1=A,dfr2=A,"
    "dfr3=B,dfr4=B,dfr5=B,dfr6=A,dfr7=A,dfrh=A,f_dir=0,b_f_dir=0,dfd4=0"
)
# Alira X style: separate f_dir_ud / f_dir_lr instead of f_dir
CONTROL_ALIRA = (
    "ret=OK,pow=1,mode=4,stemp={stemp},shum=0,dt4={stemp},dh4=0,f_rate=B,dfr4=B,"
    "f_dir_ud=S,f_dir_lr=0"
)
SET = "/aircon/set_control_info"
GET = "/aircon/get_control_info"


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


def add_routes(aresponses, reads, writes, control=CONTROL):
    """Register get_control_info (by stemp) and set_control_info replies in order."""
    for stemp in reads:
        aresponses.add(path_pattern=GET, response=control.format(stemp=stemp))
    for ret in writes:
        aresponses.add(path_pattern=SET, response=ret)


def sent(aresponses, path=SET):
    """Return the query of every request sent to path."""
    return [dict(h.request.query) for h in aresponses.history if h.request.path == path]


@pytest.mark.parametrize(
    ("stemp", "reads", "writes", "sent_stemps", "status", "error"),
    [
        # Adapter accepts 0.5 °C and reads it back
        ("23.5", ["22.0", "23.5"], ["ret=OK"], ["23.5"], "confirmed", None),
        # Whole-degree adapter on a half-degree indoor unit (maintainer's setup)
        (
            "23.5",
            ["22.0", "22.0", "24.0"],
            ["ret=PARAM NG", "ret=OK"],
            ["23.5", "24"],
            "inferred",
            None,
        ),
        # Halves round up, not to even
        (
            "22.5",
            ["22.0", "22.0", "23.0"],
            ["ret=PARAM NG", "ret=OK"],
            ["22.5", "23"],
            "inferred",
            None,
        ),
        # Retry rejected as well: no downgrade
        (
            "23.5",
            ["22.0", "22.0"],
            ["ret=PARAM NG", "ret=PARAM NG"],
            ["23.5", "24"],
            "unknown",
            DaikinCommandRejected,
        ),
        # Retry accepted but not read back as sent: no downgrade
        (
            "23.5",
            ["22.0", "22.0", "23.0"],
            ["ret=PARAM NG", "ret=OK"],
            ["23.5", "24"],
            "unknown",
            DaikinVerificationError,
        ),
        # Accepted but normalised to a whole degree: no false confirmation
        (
            "23.5",
            ["22.0", "24.0"],
            ["ret=OK"],
            ["23.5"],
            "unknown",
            DaikinVerificationError,
        ),
        # Device state changed after the rejection: no retry
        (
            "23.5",
            ["22.0", "21.0"],
            ["ret=PARAM NG"],
            ["23.5"],
            "unknown",
            DaikinCommandRejected,
        ),
        # Other rejections are not attributed to the resolution
        ("23.5", ["22.0"], ["ret=NG"], ["23.5"], "unknown", DaikinCommandRejected),
        # Whole degree or arbitrary precision: no fallback, no readback
        (
            "23.0",
            ["22.0"],
            ["ret=PARAM NG"],
            ["23.0"],
            "unknown",
            DaikinCommandRejected,
        ),
        (
            "23.2",
            ["22.0"],
            ["ret=PARAM NG"],
            ["23.2"],
            "unknown",
            DaikinCommandRejected,
        ),
        ("23.2", ["22.0"], ["ret=OK"], ["23.2"], "unknown", None),
    ],
)
@pytest.mark.asyncio
async def test_set_target_temperature(
    aresponses, client_session, stemp, reads, writes, sent_stemps, status, error
):
    """A half-degree setpoint confirms 0.5 °C or falls back once to 1 °C."""
    add_routes(aresponses, reads, writes)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    if error:
        with pytest.raises(error):
            await device.set({"stemp": stemp})
    else:
        await device.set({"stemp": stemp})

    requests = sent(aresponses)
    assert [r.pop("stemp") for r in requests] == sent_stemps
    # The retry differs in stemp only, and pow/mode are never touched
    assert all(r == requests[0] for r in requests)
    assert requests[0]["pow"] == "0" and requests[0]["mode"] == "4"
    assert device.target_temperature_step_status == status
    assert device.target_temperature_step == (1.0 if status == "inferred" else 0.5)
    # The cache holds what the device reported last, never a rejected request
    assert device.values.get("stemp", invalidate=False) == (
        reads[-1] if error or len(reads) > 1 else stemp
    )
    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.parametrize(
    ("status", "stemp", "falls_back"),
    [
        ("confirmed", "23.5", False),  # 0.5 °C proven: a rejection is not precision
        ("unknown", "17.5", False),  # may be below the range of the mode
        ("unknown", "30.5", False),  # may be above it
        ("unknown", "18.5", True),
        ("unknown", "29.5", True),
    ],
)
@pytest.mark.asyncio
async def test_fallback_only_when_precision_explains_rejection(
    aresponses, client_session, status, stemp, falls_back
):
    """Range errors or a confirmed 0.5 °C step never lead to a 1 °C inference."""
    reads, writes = ["22.0"], ["ret=PARAM NG"]
    if falls_back:
        rounded = str(int(float(stemp) + 0.5))
        reads, writes = ["22.0", "22.0", f"{rounded}.0"], ["ret=PARAM NG", "ret=OK"]
    add_routes(aresponses, reads, writes)
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.target_temperature_step_status = status

    if falls_back:
        await device.set({"stemp": stemp})
    else:
        with pytest.raises(DaikinCommandRejected):
            await device.set({"stemp": stemp})

    assert len(sent(aresponses)) == len(writes)
    assert device.target_temperature_step_status == (
        "inferred" if falls_back else status
    )
    aresponses.assert_no_unused_routes()


@pytest.mark.parametrize("control", [CONTROL, CONTROL_ALIRA], ids=["f_dir", "ud_lr"])
@pytest.mark.asyncio
async def test_fallback_preserves_swing_params(aresponses, client_session, control):
    """Both swing request schemes are sent unchanged in the retry."""
    add_routes(
        aresponses, ["22.0", "22.0", "24.0"], ["ret=PARAM NG", "ret=OK"], control
    )
    device = DaikinBRP069("192.168.1.100", session=client_session)

    await device.set({"stemp": "23.5"})

    first, retry = sent(aresponses)
    assert ("f_dir" in first) is (control is CONTROL)
    assert ("f_dir_ud" in first) is (control is CONTROL_ALIRA)
    assert {**first, "stemp": "24"} == retry
    assert device.target_temperature_step == 1.0


@pytest.mark.parametrize(
    "settings",
    [
        {"f_rate": "auto"},
        {"mode": "cool"},
        {"f_dir": "3d"},
        {"mode": "cool", "stemp": "23.5"},  # not a pure setpoint change
    ],
)
@pytest.mark.parametrize("ret", ["ret=OK", "ret=PARAM NG"])
@pytest.mark.asyncio
async def test_no_probe_without_pure_half_degree_request(
    aresponses, client_session, settings, ret
):
    """Other changes never trigger a fallback retry or a readback probe."""
    # An accepted half-degree setpoint is read back (no write) to confirm it
    readback = ret == "ret=OK" and "stemp" in settings
    add_routes(aresponses, ["22.0", "23.5"] if readback else ["22.0"], [ret])
    device = DaikinBRP069("192.168.1.100", session=client_session)

    if ret == "ret=OK":
        await device.set(settings)
    else:
        with pytest.raises(DaikinCommandRejected):
            await device.set(settings)
        assert device.values.get("mode", invalidate=False) == "4"

    assert len(sent(aresponses)) == 1
    assert len(sent(aresponses, GET)) == 1 + readback
    assert device.target_temperature_step_status == (
        "confirmed" if readback else "unknown"
    )
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_fallback_can_be_disabled(aresponses, client_session):
    """With the fallback off a rejection is raised for the caller to decide."""
    add_routes(aresponses, ["22.0"], ["ret=PARAM NG"])
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.whole_degree_fallback = False

    with pytest.raises(DaikinCommandRejected) as err:
        await device.set({"stemp": "23.5"})

    assert err.value.ret == "PARAM NG"
    assert len(sent(aresponses)) == 1
    assert device.target_temperature_step == 0.5


TIMED_OUT = []


async def _slow_ok(request):
    TIMED_OUT.append(dict(request.query))
    await asyncio.sleep(1)
    return web.Response(text="ret=OK")


async def _reset(request):
    request.transport.close()
    return web.Response(text="ret=OK")


def _reply(aresponses, reply):
    """Turn a handler or a (status, text) pair into an aresponses response."""
    if callable(reply):
        return reply
    return aresponses.Response(status=reply[0], text=reply[1])


@pytest.mark.parametrize(
    ("reply", "error", "sends"),
    [
        (_slow_ok, asyncio.TimeoutError, 1),
        # aiohttp itself resends an idempotent GET once when a reused keep-alive
        # connection drops without an answer (RFC 9112); it is the same request
        (_reset, Exception, 2),
        ((403, "Forbidden"), Exception, 1),
        ((404, "Not Found"), Exception, 1),
        ((500, "Error"), Exception, 1),
    ],
    ids=["timeout", "reset", "http403", "http404", "http500"],
)
@pytest.mark.parametrize("stemp", ["23.5", "23"])
@pytest.mark.asyncio
async def test_failed_write_is_sent_once_and_learns_nothing(
    aresponses, client_session, reply, error, sends, stemp
):
    """pydaikin never repeats a write: the device may have applied it anyway."""
    add_routes(aresponses, ["22.0"], [])
    aresponses.add(path_pattern=SET, response=_reply(aresponses, reply))
    aresponses.add(path_pattern=GET, response="ret=NG")  # read-back fails too
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)
    TIMED_OUT.clear()

    with pytest.raises(error):
        await device.set({"stemp": stemp})

    assert [r["stemp"] for r in sent(aresponses) + TIMED_OUT] == [stemp] * sends
    assert device.target_temperature_step_status == "unknown"
    # Outcome unknown: neither the old nor the requested setpoint is cached
    assert len(sent(aresponses, GET)) == 2
    assert "stemp" not in device.values
    assert device.values.get("mode", invalidate=False) == "4"
    assert device.values.should_resource_be_updated("aircon/get_control_info")


@pytest.mark.parametrize(
    ("reply", "error"),
    [
        (_slow_ok, asyncio.TimeoutError),
        ((200, "ret=NG"), DaikinException),
        ((404, "Not Found"), DaikinException),
        ((200, "ret=OK,pow=0,mode=4"), DaikinException),  # no stemp
        ((200, "ret=OK,stemp=23.5"), DaikinException),  # no pow, mode, shum
    ],
    ids=["timeout", "ret_ng", "http404", "no_stemp", "no_mode"],
)
@pytest.mark.asyncio
async def test_failed_readback_confirms_nothing(
    aresponses, client_session, reply, error
):
    """An accepted half degree that cannot be read back is reported, not cached."""
    add_routes(aresponses, ["22.0"], ["ret=OK"])
    aresponses.add(path_pattern=GET, response=_reply(aresponses, reply))
    aresponses.add(path_pattern=GET, response="ret=NG")  # resync fails too
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)

    with pytest.raises(error):
        await device.set({"stemp": "23.5"})

    assert len(sent(aresponses)) == 1
    assert device.target_temperature_step_status == "unknown"
    assert "stemp" not in device.values
    assert device.values.should_resource_be_updated("aircon/get_control_info")


@pytest.mark.parametrize(
    ("reads", "writes", "requested", "actual"),
    [
        (["22.0", "24.0"], ["ret=OK"], "23.5", "24.0"),
        (["22.0", "22.0", "23.0"], ["ret=PARAM NG", "ret=OK"], "24", "23.0"),
    ],
    ids=["accepted_normalised", "retry_differs"],
)
@pytest.mark.asyncio
async def test_verification_error_reports_values(
    aresponses, client_session, reads, writes, requested, actual
):
    """A differing read-back raises with both values; the cache shows the device."""
    add_routes(aresponses, reads, writes)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    with pytest.raises(DaikinVerificationError) as err:
        await device.set({"stemp": "23.5"})

    assert (err.value.requested, err.value.actual) == (requested, actual)
    assert device.values.get("stemp", invalidate=False) == actual
    assert device.target_temperature_step_status == "unknown"


@pytest.mark.asyncio
async def test_cancelled_set_releases_lock(aresponses, client_session):
    """Cancelling set() mid-write forgets the setpoint and lets polling continue."""
    add_routes(aresponses, ["22.0", "22.0"], [])
    aresponses.add(path_pattern=SET, response=_slow_ok)
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


@pytest.mark.asyncio
async def test_retry_timeout_learns_nothing(aresponses, client_session):
    """A timeout on the whole-degree retry neither downgrades nor trusts the cache."""
    add_routes(aresponses, ["22.0", "22.0"], ["ret=PARAM NG"])
    aresponses.add(path_pattern=SET, response=_slow_ok)
    aresponses.add(path_pattern=GET, response="ret=NG")  # resync fails too
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)

    TIMED_OUT.clear()

    with pytest.raises(asyncio.TimeoutError):
        await device.set({"stemp": "23.5"})

    assert [r["stemp"] for r in sent(aresponses) + TIMED_OUT] == ["23.5", "24"]
    assert device.target_temperature_step_status == "unknown"
    assert "stemp" not in device.values
    assert device.values.should_resource_be_updated("aircon/get_control_info")


@pytest.mark.parametrize(
    ("second", "writes", "tail"),
    [
        ("set", ["ret=OK", "ret=OK"], [(GET, None), (SET, "24")]),
        ("poll", ["ret=OK"], [(GET, None)]),
    ],
)
@pytest.mark.asyncio
async def test_concurrent_access_is_serialised(
    aresponses, client_session, second, writes, tail
):
    """A set() or poll waits until a running set() has read back its result."""
    add_routes(aresponses, ["22.0", "23.5", "23.5"], writes)
    device = DaikinBRP069("192.168.1.100", session=client_session)
    other = (
        device.set({"stemp": "24"})
        if second == "set"
        else device.update_status(["aircon/get_control_info"], force_refresh=True)
    )

    await asyncio.gather(device.set({"stemp": "23.5"}), other)

    order = [(h.request.path, h.request.query.get("stemp")) for h in aresponses.history]
    # pre-read, write and readback of the first set() stay together
    assert order == [(GET, None), (SET, "23.5"), (GET, None), *tail]
    assert device.target_temperature_step_status == "confirmed"
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_init_does_not_probe(aresponses, client_session):
    """init() only reads; the optimistic step is reported without any write."""
    aresponses.add(path_pattern="/common/get_datetime", response="ret=OK,sta=2")
    aresponses.add(path_pattern="/common/basic_info", response="ret=OK,mac=00")
    aresponses.add(path_pattern="/aircon/get_sensor_info", response="ret=OK")
    aresponses.add(path_pattern="/aircon/get_model_info", response="ret=OK,model=0FC1")
    aresponses.add(path_pattern=GET, response=CONTROL.format(stemp="22.0"))
    for path in ("get_day_power_ex", "get_week_power", "get_year_power"):
        aresponses.add(path_pattern=f"/aircon/{path}", response="ret=OK")
    device = DaikinBRP069("192.168.1.100", session=client_session)

    await device.init()

    assert not sent(aresponses)
    assert device.target_temperature_step == 0.5
    assert device.target_temperature_step_status == "unknown"


@pytest.mark.parametrize(
    ("cls", "step"),
    [
        (DaikinBRP069, 0.5),
        (DaikinBRP072C, 0.5),
        (DaikinAirBase, 1.0),  # own set() without learning
        (DaikinBRP084, 1.0),
    ],
)
@pytest.mark.asyncio
async def test_default_step(client_session, cls, step):
    """Only adapters using the learning BRP069 set() are optimistic."""
    assert cls("192.168.1.100", session=client_session).target_temperature_step == step


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


@pytest.mark.parametrize(("restored", "step"), [("inferred", 1.0), ("confirmed", 0.5)])
@pytest.mark.asyncio
async def test_restored_status(aresponses, client_session, restored, step):
    """A restored status sets the step and never changes what is sent."""
    add_routes(aresponses, ["22.0", "23.5"], ["ret=OK"])
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.target_temperature_step_status = restored
    assert device.target_temperature_step == step

    await device.set({"stemp": "23.5"})

    # Sent as requested; a stale "inferred" heals on the next accepted half degree
    assert [r["stemp"] for r in sent(aresponses)] == ["23.5"]
    assert device.target_temperature_step_status == "confirmed"
    assert device.target_temperature_step == 0.5


@pytest.mark.parametrize("status", ["bogus", "", None, 1.0])
def test_invalid_status_is_rejected(status):
    """Only the documented statuses can be restored."""
    device = DaikinBRP069("192.168.1.100", session=object())
    with pytest.raises(ValueError):
        device.target_temperature_step_status = status
    assert device.target_temperature_step_status == "unknown"


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
    reply = pre_read if isinstance(pre_read, str) else _reply(aresponses, pre_read)
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
    aresponses.add(path_pattern=SET, response=_slow_ok)
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
    assert device.target_temperature_step_status == "unknown"
    aresponses.assert_no_unused_routes()


@pytest.mark.parametrize(
    "changed", [("pow=0", "pow=1"), ("mode=4", "mode=3"), ("f_rate=B", "f_rate=A")]
)
@pytest.mark.asyncio
async def test_no_retry_when_state_changed(aresponses, client_session, changed):
    """A remote or app change after the rejection stops the fallback retry."""
    aresponses.add(path_pattern=GET, response=CONTROL.format(stemp="22.0"))
    aresponses.add(
        path_pattern=GET, response=CONTROL.format(stemp="22.0").replace(*changed, 1)
    )
    aresponses.add(path_pattern=SET, response="ret=PARAM NG")
    device = DaikinBRP069("192.168.1.100", session=client_session)

    with pytest.raises(DaikinCommandRejected):
        await device.set({"stemp": "23.5"})

    assert len(sent(aresponses)) == 1
    assert device.target_temperature_step_status == "unknown"
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_no_fallback_without_numeric_setpoint(aresponses, client_session):
    """In dry mode (stemp=M) a rejected half degree is not a precision issue."""
    dry = CONTROL.replace("mode=4", "mode=2").replace("stemp={stemp}", "stemp=M")
    add_routes(aresponses, ["22.0"], ["ret=PARAM NG"], dry)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    with pytest.raises(DaikinCommandRejected):
        await device.set({"stemp": "23.5"})

    assert len(sent(aresponses)) == 1


@pytest.mark.asyncio
async def test_resync_is_time_boxed(aresponses, client_session):
    """A hanging read-back does not delay the error beyond RESYNC_TIMEOUT."""
    add_routes(aresponses, ["22.0"], [])
    aresponses.add(path_pattern=SET, response=_reply(aresponses, (500, "Error")))
    aresponses.add(path_pattern=GET, response=_slow_ok)
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


FAN = CONTROL.replace("mode=4", "mode=6").replace("stemp={stemp}", "stemp=--")


@pytest.mark.asyncio
async def test_setpoint_ignored_in_fan_mode(aresponses, client_session):
    """Fan mode accepts but ignores stemp (seen on a real adapter): no error."""
    add_routes(aresponses, [], ["ret=OK"])
    aresponses.add(path_pattern=GET, response=FAN)
    aresponses.add(path_pattern=GET, response=FAN)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    await device.set({"stemp": "22.5"})

    assert device.target_temperature_step_status == "unknown"
    assert device.values.get("stemp", invalidate=False) == "--"
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_no_inference_when_retry_reads_back_no_setpoint(
    aresponses, client_session
):
    """A retry read back as M/-- (mode changed meanwhile) infers nothing."""
    add_routes(aresponses, ["22.0", "22.0"], ["ret=PARAM NG", "ret=OK"])
    aresponses.add(path_pattern=GET, response=FAN)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    with pytest.raises(DaikinCommandRejected):
        await device.set({"stemp": "23.5"})

    assert device.target_temperature_step_status == "unknown"
    aresponses.assert_no_unused_routes()
