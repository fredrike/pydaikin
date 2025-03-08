"""Smart container for appliance's data"""

from collections.abc import MutableMapping
from datetime import datetime, timedelta, timezone


class ApplianceValues(MutableMapping):
    """Appliance's values dict container keeping track of which values have been actually useful."""

    # If a none of one resource's key are used, the resource will be updated every 15 minutes
    TTL = timedelta(minutes=15)

    def __init__(self):
        self._data = {}
        self._last_update_by_resource = {}
        self._resource_by_key = {}

    # --- Implementation of abstract methods ---

    def __getitem__(self, key):
        # Everytime a value is read, the associated resource is deprecated and should be updated
        resource = self._resource_by_key.get(key)
        if resource is not None:
            self._last_update_by_resource.pop(resource, None)
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]
        del self._resource_by_key[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return f"{self._data}"

    # --- Custom methods to use smart updates ---
    def get(
        self, key: str, default=None, *, invalidate: bool = True
    ):  # pylint: disable=arguments-differ
        """Get a value and invalidate it so that the associated resource will soon be updated."""
        if key not in self._data:
            return default
        if invalidate:
            self._last_update_by_resource.pop(self._resource_by_key[key], None)
        return self._data[key]

    def keys(self):
        """Return values' keys"""
        return self._data.keys()

    def should_resource_be_updated(self, resource: str) -> bool:
        """Returns whether a resource should be updated, considering recent use of values
        it returns."""
        # Keep only resources which have been updated recently
        self._last_update_by_resource = {
            resource: last_update
            for resource, last_update in self._last_update_by_resource.items()
            if datetime.now(timezone.utc) - last_update < self.TTL
        }
        return resource not in self._last_update_by_resource

    def update_by_resource(self, resource: str, data: dict):
        """Update the values and keep track of which resource provided them."""
        self._data.update(data)
        self._last_update_by_resource[resource] = datetime.now(timezone.utc)
        for k in data.keys():
            self._resource_by_key[k] = resource
