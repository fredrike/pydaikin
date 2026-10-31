"""Test adaptive target temperature step detection on BRP069 (issue #168)."""

import asyncio

from aiohttp import ClientSession, ClientTimeout, web
import pytest
import pytest_asyncio

from pydaikin.daikin_airbase import DaikinAirBase
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.daikin_brp072c import DaikinBRP072C
from pydaikin.daikin_brp084 import DaikinBRP084
from pydaikin.exceptions import DaikinCommandRejected
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
    ("stemp", "reads", "writes", "sent_stemps", "status", "rejected"),
    [
        # Adapter accepts 0.5 °C and reads it back
        ("23.5", ["22.0", "23.5"], ["ret=OK"], ["23.5"], "confirmed", False),
        # Whole-degree adapter on a half-degree indoor unit (maintainer's setup)
        (
            "23.5",
            ["22.0", "22.0", "24.0"],
            ["ret=PARAM NG", "ret=OK"],
            ["23.5", "24"],
            "inferred",
            False,
        ),
        # Halves round up, not to even
        (
            "22.5",
            ["22.0", "22.0", "23.0"],
            ["ret=PARAM NG", "ret=OK"],
            ["22.5", "23"],
            "inferred",
            False,
        ),
        # Retry rejected as well: no downgrade
        (
            "23.5",
            ["22.0", "22.0"],
            ["ret=PARAM NG", "ret=PARAM NG"],
            ["23.5", "24"],
            "unknown",
            True,
        ),
        # Retry accepted but not read back as sent: no downgrade
        (
            "23.5",
            ["22.0", "22.0", "23.0"],
            ["ret=PARAM NG", "ret=OK"],
            ["23.5", "24"],
            "unknown",
            True,
        ),
        # Accepted but normalised to a whole degree: no false confirmation
        ("23.5", ["22.0", "24.0"], ["ret=OK"], ["23.5"], "unknown", False),
        # Device state changed after the rejection: no retry
        ("23.5", ["22.0", "21.0"], ["ret=PARAM NG"], ["23.5"], "unknown", True),
        # Other rejections are not attributed to the resolution
        ("23.5", ["22.0"], ["ret=NG"], ["23.5"], "unknown", True),
        # Whole degree or arbitrary precision: no fallback, no readback
        ("23.0", ["22.0"], ["ret=PARAM NG"], ["23.0"], "unknown", True),
        ("23.2", ["22.0"], ["ret=PARAM NG"], ["23.2"], "unknown", True),
        ("23.2", ["22.0"], ["ret=OK"], ["23.2"], "unknown", False),
    ],
)
@pytest.mark.asyncio
async def test_set_target_temperature(
    aresponses, client_session, stemp, reads, writes, sent_stemps, status, rejected
):
    """A half-degree setpoint confirms 0.5 °C or falls back once to 1 °C."""
    add_routes(aresponses, reads, writes)
    device = DaikinBRP069("192.168.1.100", session=client_session)

    if rejected:
        with pytest.raises(DaikinCommandRejected):
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
        reads[-1] if rejected or len(reads) > 1 else stemp
    )
    aresponses.assert_all_requests_matched()
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


@pytest.mark.parametrize(
    ("replies", "error"),
    [
        ([_slow_ok], asyncio.TimeoutError),
        ([(403, "Forbidden")], Exception),
        ([(500, "Error")] * 3, Exception),  # transport retries, no fallback
    ],
    ids=["timeout", "http403", "http500"],
)
@pytest.mark.asyncio
async def test_transport_error_learns_nothing(
    aresponses, client_session, replies, error
):
    """Errors without a device answer neither fall back nor keep the request."""
    add_routes(aresponses, ["22.0"], [])
    for reply in replies:
        if callable(reply):
            aresponses.add(path_pattern=SET, response=reply)
        else:
            aresponses.add(
                path_pattern=SET,
                response=aresponses.Response(status=reply[0], text=reply[1]),
            )
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)
    TIMED_OUT.clear()

    with pytest.raises(error):
        await device.set({"stemp": "23.5"})

    stemps = [r["stemp"] for r in sent(aresponses) + TIMED_OUT]
    assert stemps == ["23.5"] * len(replies)
    assert device.target_temperature_step_status == "unknown"
    assert device.values.get("stemp", invalidate=False) == "22.0"
    assert device.values.should_resource_be_updated("aircon/get_control_info")


@pytest.mark.asyncio
async def test_retry_timeout_learns_nothing(aresponses, client_session):
    """A timeout on the whole-degree retry neither downgrades nor trusts the cache."""
    add_routes(aresponses, ["22.0", "22.0"], ["ret=PARAM NG"])
    aresponses.add(path_pattern=SET, response=_slow_ok)
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)

    TIMED_OUT.clear()

    with pytest.raises(asyncio.TimeoutError):
        await device.set({"stemp": "23.5"})

    assert [r["stemp"] for r in sent(aresponses) + TIMED_OUT] == ["23.5", "24"]
    assert device.target_temperature_step_status == "unknown"
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


@pytest.mark.parametrize(
    ("restored", "step"), [("inferred", 1.0), ("confirmed", 0.5), ("bogus", 0.5)]
)
@pytest.mark.asyncio
async def test_restored_status_only_affects_reported_step(
    aresponses, client_session, restored, step
):
    """A status restored by the consumer never changes what is sent."""
    add_routes(aresponses, ["22.0", "23.5"], ["ret=OK"])
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.target_temperature_step_status = restored
    assert device.target_temperature_step == step

    await device.set({"stemp": "23.5"})

    # Sent as requested; a stale "inferred" heals on the next accepted half degree
    assert [r["stemp"] for r in sent(aresponses)] == ["23.5"]
    assert device.target_temperature_step_status == "confirmed"
    assert device.target_temperature_step == 0.5
