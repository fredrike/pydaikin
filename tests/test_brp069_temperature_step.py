"""Test adaptive target temperature step detection on BRP069 (issue #168)."""

import asyncio

from aiohttp import ClientSession, ClientTimeout
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

from .brp069_helpers import (
    CONTROL,
    CONTROL_ALIRA,
    GET,
    SET,
    TIMED_OUT,
    add_routes,
    mock_reply,
    sent,
    slow_ok,
)


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


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
    add_routes(aresponses, ["22.0"], [ret])
    if readback:  # read back in the requested mode (cool)
        aresponses.add(path_pattern=GET, response=ctrl("3", "23.5"))
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


@pytest.mark.parametrize(
    ("reply", "error"),
    [
        (slow_ok, asyncio.TimeoutError),
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
    aresponses.add(path_pattern=GET, response=mock_reply(aresponses, reply))
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
async def test_retry_timeout_learns_nothing(aresponses, client_session):
    """A timeout on the whole-degree retry neither downgrades nor trusts the cache."""
    add_routes(aresponses, ["22.0", "22.0"], ["ret=PARAM NG"])
    aresponses.add(path_pattern=SET, response=slow_ok)
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


FAN = CONTROL.replace("mode=4", "mode=6").replace("stemp={stemp}", "stemp=--")


def ctrl(mode, stemp):
    """Return a get_control_info reply in the given mode with the given stemp."""
    return CONTROL.replace(",mode=4,", f",mode={mode},").format(stemp=stemp)


@pytest.mark.parametrize(
    ("mode", "back_mode", "back", "error", "status"),
    [
        ("4", "4", "22.5", None, "confirmed"),  # heat
        ("3", "3", "22.5", None, "confirmed"),  # cool
        ("6", "6", "22.5", None, "unknown"),  # fan: a number proves nothing
        ("2", "2", "22.5", None, "unknown"),  # dry: neither
        ("6", "6", "--", None, "unknown"),  # fan accepts and ignores stemp
        ("2", "2", "M", None, "unknown"),
        ("4", "4", "--", DaikinVerificationError, "unknown"),
        ("3", "3", "M", DaikinVerificationError, "unknown"),
        ("0", "0", "--", DaikinVerificationError, "unknown"),  # auto
        ("6", "6", "24.0", DaikinVerificationError, "unknown"),  # a number is checked
        ("2", "2", "24.0", DaikinVerificationError, "unknown"),
        ("4", "3", "22.5", None, "unknown"),  # mode changed during verification
        ("4", "6", "--", None, "unknown"),
        ("6", "4", "22.5", None, "unknown"),
    ],
)
@pytest.mark.asyncio
async def test_readback_confirms_only_in_setpoint_modes(
    aresponses, client_session, mode, back_mode, back, error, status
):
    """Only heat/cool/auto with an unchanged mode can confirm the 0.5 °C step."""
    aresponses.add(path_pattern=GET, response=ctrl(mode, "22.0"))
    aresponses.add(path_pattern=SET, response="ret=OK")
    aresponses.add(path_pattern=GET, response=ctrl(back_mode, back))
    device = DaikinBRP069("192.168.1.100", session=client_session)

    if error:
        with pytest.raises(error):
            await device.set({"stemp": "22.5"})
    else:
        await device.set({"stemp": "22.5"})

    assert sent(aresponses)[0]["mode"] == mode
    assert device.target_temperature_step_status == status
    assert device.values.get("stemp", invalidate=False) == back
    aresponses.assert_no_unused_routes()


@pytest.mark.parametrize("mode", ["2", "6"], ids=["dry", "fan"])
@pytest.mark.asyncio
async def test_no_fallback_in_no_setpoint_modes(aresponses, client_session, mode):
    """PARAM NG in dry/fan mode is no precision evidence, even with a numeric stemp."""
    aresponses.add(path_pattern=GET, response=ctrl(mode, "22.0"))
    aresponses.add(path_pattern=SET, response="ret=PARAM NG")
    device = DaikinBRP069("192.168.1.100", session=client_session)

    with pytest.raises(DaikinCommandRejected):
        await device.set({"stemp": "23.5"})

    assert len(sent(aresponses)) == 1
    assert device.target_temperature_step_status == "unknown"
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


@pytest.mark.parametrize(
    ("reply", "error"),
    [(slow_ok, asyncio.TimeoutError), ((500, "Error"), Exception)],
    ids=["timeout", "http500"],
)
@pytest.mark.asyncio
async def test_failed_write_learns_nothing(aresponses, client_session, reply, error):
    """A write without a device answer neither confirms nor infers a step."""
    add_routes(aresponses, ["22.0"], [])
    aresponses.add(path_pattern=SET, response=mock_reply(aresponses, reply))
    aresponses.add(path_pattern=GET, response="ret=NG")  # read-back fails too
    device = DaikinBRP069("192.168.1.100", session=client_session)
    device.HTTP_TIMEOUT = ClientTimeout(total=0.1)

    with pytest.raises(error):
        await device.set({"stemp": "23.5"})

    assert device.target_temperature_step_status == "unknown"
    assert device.target_temperature_step == 0.5
