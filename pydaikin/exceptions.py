"""Daikin exceptions."""


class DaikinException(Exception):
    """Daikin base exception class."""


class DaikinCommandRejected(DaikinException):
    """The adapter answered a write request with a non-OK ``ret``."""

    def __init__(self, ret: str) -> None:
        super().__init__(f"Daikin rejected the request: ret={ret}")
        self.ret = ret
