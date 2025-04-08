import asyncio
import logging
import time

from pydaikin.factory import DaikinFactory

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


async def test_daikin():
    print("\n=== Testing Daikin Firmware 2.8.0 Integration ===\n")

    # Replace with your device's IP address
    device_ip = "192.168.50.47"
    device = await DaikinFactory(device_ip)

    print(f"Device type: {type(device).__name__}")
    print(f"Device IP: {device_ip}")
    print(f"Device MAC: {device.values._data.get('mac', 'unknown')}")

    # Get initial state
    print("\n=== Initial State ===")
    print(f"Power: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
    print(f"Mode: {device.values._data.get('mode', 'unknown')}")
    print(f"Target temperature: {device.values._data.get('stemp', 'unknown')}")
    print(f"Fan rate: {device.values._data.get('f_rate', 'unknown')}")
    print(f"Fan direction: {device.values._data.get('f_dir', 'unknown')}")
    print(f"Inside temperature: {device.values._data.get('htemp', 'unknown')}")
    print(f"Outside temperature: {device.values._data.get('otemp', 'unknown')}")
    print(f"Humidity: {device.values._data.get('hhum', 'unknown')}")

    # Get all values for reference
    print("\n=== All Values ===")
    for key, value in device.values._data.items():
        print(f"  {key}: {value}")

    # Test 1: Turn On
    print("\n=== Test 1: Turn On ===")
    try:
        print("Turning on...")
        await device.set({"mode": "cool"})  # This should also power on
        print("Device turned on.")
        print(f"Power: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
        print(f"Mode: {device.values._data.get('mode', 'unknown')}")
        await asyncio.sleep(2)  # Wait for the command to take effect
    except Exception as e:
        print(f"Error turning on: {e}")

    # Test 2: Set Temperature
    print("\n=== Test 2: Set Temperature ===")
    try:
        temp = "25.0"
        print(f"Setting temperature to {temp}...")
        await device.set({"stemp": temp})
        print("Temperature set.")
        print(f"Target temperature: {device.values._data.get('stemp', 'unknown')}")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"Error setting temperature: {e}")

    # Test 3: Set Fan Mode
    print("\n=== Test 3: Set Fan Mode ===")
    try:
        fan_mode = "3"  # Medium speed
        print(f"Setting fan speed to {fan_mode}...")
        await device.set({"f_rate": fan_mode})
        print("Fan speed set.")
        print(f"Fan rate: {device.values._data.get('f_rate', 'unknown')}")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"Error setting fan mode: {e}")

    # Test 4: Set Swing Mode
    print("\n=== Test 4: Set Swing Mode ===")
    try:
        swing_mode = "vertical"
        print(f"Setting swing mode to {swing_mode}...")
        await device.set({"f_dir": swing_mode})
        print("Swing mode set.")
        print(f"Fan direction: {device.values._data.get('f_dir', 'unknown')}")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"Error setting swing mode: {e}")

    # Test 5: Change Mode
    print("\n=== Test 5: Change Mode ===")
    try:
        mode = "dry"
        print(f"Setting mode to {mode}...")
        await device.set({"mode": mode})
        print("Mode changed.")
        print(f"Mode: {device.values._data.get('mode', 'unknown')}")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"Error changing mode: {e}")

    # Test 6: Turn Off
    print("\n=== Test 6: Turn Off ===")
    try:
        print("Turning off...")
        await device.set({"mode": "off"})
        print("Device turned off.")
        print(f"Power: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
        print(f"Mode: {device.values._data.get('mode', 'unknown')}")
    except Exception as e:
        print(f"Error turning off: {e}")

    # Final state
    print("\n=== Final State ===")
    print(f"Power: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
    print(f"Mode: {device.values._data.get('mode', 'unknown')}")
    print(f"Target temperature: {device.values._data.get('stemp', 'unknown')}")
    print(f"Fan rate: {device.values._data.get('f_rate', 'unknown')}")
    print(f"Fan direction: {device.values._data.get('f_dir', 'unknown')}")
    print(f"Inside temperature: {device.values._data.get('htemp', 'unknown')}")
    print(f"Outside temperature: {device.values._data.get('otemp', 'unknown')}")
    print(f"Humidity: {device.values._data.get('hhum', 'unknown')}")

    print("\n=== Test Complete ===")


asyncio.run(test_daikin())
