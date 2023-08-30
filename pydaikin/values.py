"""Smart container for appliance's data"""
from collections import UserDict
from typing import Any


class ApplianceValues(UserDict):
    """Special dict calling .expire_now() on every object read from it
    Only meant to be used with instances of DaikinResponse as values"""

    def __getitem__(self, __key: Any) -> Any:
        item = super().__getitem__(__key)
        if item is not None:
            item.expire_now()
        return item
