import logging
import asyncio
from pydaikin.factory import DaikinFactory

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

async def test_daikin():
    # Replace with your device's IP address
    device = await DaikinFactory("192.168.50.47")
    print(f"Device type: {type(device).__name__}")
    
    # Access values directly to avoid using the get() method that's causing issues
    print(f"Current mode: {device.values._data.get('mode', 'unknown')}")
    print(f"Current temperature: {device.values._data.get('stemp', 'unknown')}")
    print(f"Inside temperature: {device.values._data.get('htemp', 'unknown')}")
    
    # For safety, let's add this function that won't use values.get()
    print("\nAll values:")
    for key, value in device.values._data.items():
        print(f"  {key}: {value}")
    
    # Try to set a temperature
    try:
        print("\nAttempting to set temperature to 25.0...")
        await device.set({"stemp": "25.0"})
        print("Temperature set successfully!")
        print(f"New temperature: {device.values._data.get('stemp', 'unknown')}")
    except Exception as e:
        print(f"Error setting temperature: {e}")

asyncio.run(test_daikin())