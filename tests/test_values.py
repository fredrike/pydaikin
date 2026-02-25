"""Test ApplianceValues smart container."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from pydaikin.values import ApplianceValues


def test_appliance_values_basic_operations():
    """Test basic dict-like operations."""
    values = ApplianceValues()

    # Test setitem and getitem
    values['mode'] = '2'
    assert values['mode'] == '2'

    # Test len
    assert len(values) == 1

    # Test iter
    assert 'mode' in values

    # Test delitem
    values['temp'] = '25'
    del values['temp']
    assert 'temp' not in values


def test_appliance_values_get_with_default():
    """Test get method with default value."""
    values = ApplianceValues()

    # Get non-existent key should return default
    assert values.get('nonexistent') is None
    assert values.get('nonexistent', 'default') == 'default'

    # Get existing key
    values['mode'] = '2'
    assert values.get('mode') == '2'


def test_appliance_values_get_invalidate():
    """Test get method with invalidate parameter."""
    values = ApplianceValues()

    # Update by resource
    values.update_by_resource('resource1', {'mode': '2', 'temp': '25'})

    # Get with invalidate=True (default) should clear last_update
    val = values.get('mode', invalidate=True)
    assert val == '2'
    assert values.should_resource_be_updated('resource1') is True

    # Update again
    values.update_by_resource('resource1', {'mode': '2', 'temp': '25'})

    # Get with invalidate=False should not clear last_update
    val = values.get('mode', invalidate=False)
    assert val == '2'
    assert values.should_resource_be_updated('resource1') is False


def test_appliance_values_getitem_invalidates():
    """Test that __getitem__ invalidates resource."""
    values = ApplianceValues()

    # Update by resource
    values.update_by_resource('resource1', {'mode': '2'})

    # Access via __getitem__ should invalidate
    _ = values['mode']
    assert values.should_resource_be_updated('resource1') is True


def test_appliance_values_update_by_resource():
    """Test update_by_resource method."""
    values = ApplianceValues()

    # First update
    data1 = {'mode': '2', 'temp': '25'}
    values.update_by_resource('resource1', data1)

    # Use get with invalidate=False to not clear the resource tracking
    assert values.get('mode', invalidate=False) == '2'
    assert values.get('temp', invalidate=False) == '25'
    # Resource should not need update right after being updated
    assert 'resource1' in values._last_update_by_resource

    # Update with different resource
    data2 = {'fan': 'A'}
    values.update_by_resource('resource2', data2)

    assert values.get('fan', invalidate=False) == 'A'
    assert 'resource2' in values._last_update_by_resource


def test_appliance_values_should_resource_be_updated():
    """Test should_resource_be_updated with TTL."""
    values = ApplianceValues()

    # New resource should need update
    assert values.should_resource_be_updated('resource1') is True

    # After update, should not need update
    values.update_by_resource('resource1', {'mode': '2'})
    assert values.should_resource_be_updated('resource1') is False

    # After TTL expires, should need update
    with patch('pydaikin.values.datetime') as mock_datetime:
        # Set current time to TTL + 1 minute in the future
        future_time = datetime.now(timezone.utc) + timedelta(minutes=16)
        mock_datetime.now.return_value = future_time

        result = values.should_resource_be_updated('resource1')
        assert result is True


def test_appliance_values_invalidate_resource():
    """Test invalidate_resource method."""
    values = ApplianceValues()

    # Update resource
    values.update_by_resource('resource1', {'mode': '2'})
    assert values.should_resource_be_updated('resource1') is False

    # Manually invalidate
    values.invalidate_resource('resource1')
    assert values.should_resource_be_updated('resource1') is True

    # Invalidating non-existent resource should not error
    values.invalidate_resource('nonexistent')


def test_appliance_values_keys():
    """Test keys method."""
    values = ApplianceValues()

    values.update_by_resource('resource1', {'mode': '2', 'temp': '25', 'fan': 'A'})

    keys = values.keys()
    assert 'mode' in keys
    assert 'temp' in keys
    assert 'fan' in keys
    assert len(list(keys)) == 3


def test_appliance_values_str():
    """Test __str__ method."""
    values = ApplianceValues()
    values['mode'] = '2'
    values['temp'] = '25'

    string_repr = str(values)
    assert 'mode' in string_repr
    assert '2' in string_repr


def test_appliance_values_delitem_with_resource():
    """Test __delitem__ removes resource tracking."""
    values = ApplianceValues()

    values.update_by_resource('resource1', {'mode': '2', 'temp': '25'})

    # Delete a key
    del values['mode']

    # Key should be gone
    assert 'mode' not in values

    # Resource should still be tracked for remaining keys
    assert values.should_resource_be_updated('resource1') is False


def test_appliance_values_multiple_resources():
    """Test tracking multiple resources."""
    values = ApplianceValues()

    # Update from different resources
    values.update_by_resource('basic_info', {'mode': '2', 'pow': '1'})
    values.update_by_resource('sensor_info', {'htemp': '25', 'otemp': '21'})

    # Both resources should not need update initially
    assert values.should_resource_be_updated('basic_info') is False
    assert values.should_resource_be_updated('sensor_info') is False

    # Accessing a value from basic_info should invalidate only that resource
    _ = values['mode']
    assert values.should_resource_be_updated('basic_info') is True
    assert values.should_resource_be_updated('sensor_info') is False
