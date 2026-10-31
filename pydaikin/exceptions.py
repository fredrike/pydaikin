"""Daikin exceptions."""


class DaikinException(Exception):
    """Daikin base exception class."""


class DaikinCommandRejected(DaikinException):
    """The adapter answered a write request with a non-OK ``ret``."""

    def __init__(self, ret: str) -> None:
        super().__init__(f"Daikin rejected the request: ret={ret}")
        self.ret = ret


class DaikinVerificationError(DaikinException):
    """The adapter accepted a setpoint, but reads back a different one."""

    def __init__(self, requested: str, actual: str) -> None:
        super().__init__(f"Daikin accepted stemp={requested} but reports {actual}")
        self.requested = requested
        self.actual = actual
