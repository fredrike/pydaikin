import logging
import asyncio
import ipaddress
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote

from pydaikin.discovery import get_devices
from pydaikin.factory import DaikinFactory

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Pre-defined device keys for convenience. Add as many as you would like here.
DEVICE_KEYS = {
    "ID": "key",
}

async def test_single_device(device_info):
    """Test a single device."""
    if isinstance(device_info, dict):
        ip_address = device_info['ip']
        port = device_info.get('port')
        mac = device_info.get('mac', 'Unknown')
        name = device_info.get('name', 'Unknown')
        device_id = f"{ip_address}:{port}" if port and port != 80 else ip_address
        device_type = device_info.get('type', '')
        adp_kind = device_info.get('adp_kind', '')
    else:
        # Just an IP address string
        ip_address = device_info
        device_id = ip_address
        mac = "Unknown"
        name = "Unknown"
        port = None
        device_type = ''
        adp_kind = ''
    
    # Clean up URL encoded names
    if isinstance(name, str) and "%" in name:
        name = unquote(name)
    
    print(f"\n=== Testing device at {ip_address}{f':{port}' if port and port != 80 else ''} ===")
    print(f"Device Name: {name}")
    print(f"Device MAC: {mac}")
    
    # Check if this might be a BRP072C device (adp_kind=3 often indicates this)
    key = None
    need_key = False
    
    if adp_kind == '3' or adp_kind == 3:
        need_key = True
        print(f"Device appears to be a BRP072C device which requires an authentication key.")
        
        # Check if we have a pre-defined key for this device
        for device_name, device_key in DEVICE_KEYS.items():
            if device_name in name:
                key = device_key
                print(f"Using pre-defined authentication key: {key}")
                break
        
        # If no pre-defined key, prompt the user
        if not key:
            key_input = input(f"Enter authentication key for {name} (or press Enter to skip): ")
            if key_input.strip():
                key = key_input
            else:
                print("No key provided, attempting connection without key...")
    
    try:
        # Try to create device with factory
        if key:
            print(f"Connecting with authentication key...")
            device = await DaikinFactory(device_id, key=key)
        else:
            device = await DaikinFactory(device_id)
        
        # Print device information
        device_class = type(device).__name__
        print(f"Device type: {device_class}")
        print(f"MAC: {device.values._data.get('mac', 'Unknown')}")
        print(f"Power: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
        print(f"Mode: {device.values._data.get('mode', 'Unknown')}")
        
        # Print additional information
        print("\nDevice Values:")
        for key, value in sorted(device.values._data.items()):
            print(f"  {key}: {value}")
        
        print("\nDevice successfully detected and tested!")
        
        # Test control ability
        should_test_control = input("\nWould you like to test control capability? (y/n): ").lower() == 'y'
        if should_test_control:
            if device.values._data.get('pow') == '1':
                # If on, try adjusting temperature
                if device.values._data.get('stemp') and device.values._data.get('stemp') != '--':
                    curr_temp = float(device.values._data.get('stemp'))
                    new_temp = str(curr_temp + 0.5)
                    print(f"Setting temperature from {curr_temp} to {new_temp}...")
                    await device.set({"stemp": new_temp})
                    print(f"New temperature: {device.values._data.get('stemp')}")
                    
                    # Restore original temperature
                    await asyncio.sleep(2)
                    print(f"Restoring temperature to {curr_temp}...")
                    await device.set({"stemp": str(curr_temp)})
                    print(f"Temperature restored: {device.values._data.get('stemp')}")
                else:
                    # Try turning off
                    print("Testing power off...")
                    await device.set({"mode": "off"})
                    print(f"Power after OFF command: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
                    
                    # Turn back on if requested
                    if input("Turn device back on? (y/n): ").lower() == 'y':
                        prev_mode = device.values._data.get('mode')
                        mode_to_set = prev_mode if prev_mode and prev_mode != 'off' else 'cool'
                        print(f"Turning back ON to {mode_to_set} mode...")
                        await device.set({"mode": mode_to_set})
                        print(f"Power after ON command: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
            else:
                # If off, ask if we should turn on
                if input("Device is OFF. Turn it ON? (y/n): ").lower() == 'y':
                    print("Testing power on to cool mode...")
                    await device.set({"mode": "cool"})
                    print(f"Power after ON command: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
                    
                    # Turn back off if requested
                    if input("Test complete. Turn device back OFF? (y/n): ").lower() == 'y':
                        print("Turning back OFF...")
                        await device.set({"mode": "off"})
                        print(f"Power after OFF command: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
        
        return True, device_id, device_class
    except Exception as e:
        print(f"Error testing device at {device_id}: {e}")
        
        # If this was not a BRP072C device but failed, check if it might need a key
        if not need_key and "forbidden" in str(e).lower():
            print("The device returned a Forbidden error. It might require an authentication key.")
            if input("Would you like to try connecting with a key? (y/n): ").lower() == 'y':
                key = input("Enter authentication key: ")
                if key.strip():
                    try:
                        print(f"Attempting connection with key...")
                        device = await DaikinFactory(device_id, key=key)
                        print("Connection successful!")
                        
                        device_class = type(device).__name__
                        print(f"Device type: {device_class}")
                        print(f"MAC: {device.values._data.get('mac', 'Unknown')}")
                        print(f"Power: {'On' if device.values._data.get('pow') == '1' else 'Off'}")
                        
                        return True, device_id, device_class
                    except Exception as inner_e:
                        print(f"Still failed with key: {inner_e}")
        
        return False, device_id, str(e)

async def main():
    """Main function to test Daikin devices on the network."""
    print("=== Daikin Device Network Test ===")
    
    # First try to discover devices using discovery
    print("\nAttempting to discover Daikin devices automatically...")
    discovered_devices = list(get_devices())
    
    if discovered_devices:
        print(f"Discovered {len(discovered_devices)} Daikin devices:")
        for i, device in enumerate(discovered_devices, 1):
            port_info = f":{device['port']}" if 'port' in device and device['port'] != 80 else ""
            device_name = unquote(device.get('name', 'Unknown')) if '%' in device.get('name', '') else device.get('name', 'Unknown')
            print(f"{i}. {device_name} ({device['ip']}{port_info}) [MAC: {device.get('mac', 'Unknown')}]")
            
            # Print firmware version and adapter kind if available
            if 'ver' in device:
                print(f"   Firmware: {device.get('ver', 'Unknown')}")
            if 'adp_kind' in device:
                print(f"   Adapter Type: {device.get('adp_kind', 'Unknown')}")
            
            # Identify if this device might need a key
            if device.get('adp_kind') == '3' or device.get('adp_kind') == 3:
                print(f"   ⚠️ This device likely requires an authentication key")
                
                # Check if we have a pre-defined key
                for key_name, _ in DEVICE_KEYS.items():
                    if key_name in device_name:
                        print(f"   ✓ Pre-defined key available for this device")
                        break
    else:
        print("No devices discovered automatically.")
    
    # Ask for subnet or specific IP
    print("\nOptions:")
    print("1. Test discovered devices")
    print("2. Test specific IP address")
    print("3. Scan network subnet")
    
    choice = input("\nEnter your choice (1-3): ")
    
    devices_to_test = []
    
    if choice == "1":
        if not discovered_devices:
            print("No devices were discovered automatically.")
            return
        
        # Ask user which device to test
        device_choice = input(f"Enter device number to test (1-{len(discovered_devices)}) or 'all': ")
        if device_choice.lower() == 'all':
            devices_to_test = discovered_devices
        else:
            try:
                idx = int(device_choice) - 1
                if 0 <= idx < len(discovered_devices):
                    devices_to_test = [discovered_devices[idx]]
                else:
                    print(f"Invalid device number. Must be between 1 and {len(discovered_devices)}.")
                    return
            except ValueError:
                print("Invalid input. Please enter a number or 'all'.")
                return
    
    elif choice == "2":
        ip = input("Enter IP address to test: ")
        port = input("Enter port (optional, press Enter for default): ")
        if port.strip():
            ip = f"{ip}:{port}"
        if ":" in ip or ipaddress.ip_address(ip.split(":")[0]):
            devices_to_test.append(ip)
        else:
            print(f"Invalid IP address: {ip}")
            return
    
    elif choice == "3":
        subnet = input("Enter subnet to scan (e.g., 192.168.1.0/24): ")
        try:
            # Scan for potential Daikin devices
            network = ipaddress.ip_network(subnet, strict=False)
            hosts = list(network.hosts())
            print(f"Scanning {len(hosts)} IP addresses...")
            
            # Use ThreadPoolExecutor for parallel port scanning
            live_hosts = []
            with ThreadPoolExecutor(max_workers=50) as executor:
                # Check common Daikin ports: 80 (default), 30050 (BRP devices), 49155 (BRP072C)
                for port in [80, 30050, 49155]:
                    for i, ip in enumerate(hosts):
                        ip_str = str(ip)
                        # Try to connect to the port
                        try:
                            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                            s.settimeout(0.5)
                            result = s.connect_ex((ip_str, port))
                            s.close()
                            if result == 0:  # Port is open
                                device_id = f"{ip_str}:{port}" if port != 80 else ip_str
                                if device_id not in live_hosts:
                                    live_hosts.append(device_id)
                                    print(f"Found device at: {device_id}")
                        except:
                            pass
                        # Show progress
                        if i % 20 == 0 and i > 0:
                            sys.stdout.write(f"\rScanned {i}/{len(hosts)} IPs on port {port}...")
                            sys.stdout.flush()
                    print(f"\nCompleted scan on port {port}")
            
            if live_hosts:
                print(f"\nFound {len(live_hosts)} potential devices with open ports. Testing each one...")
                devices_to_test = live_hosts
            else:
                print("No live hosts found on the specified subnet.")
                return
        except Exception as e:
            print(f"Error scanning network: {e}")
            return
    else:
        print("Invalid choice.")
        return
    
    # Test each device
    results = []
    for device in devices_to_test:
        result = await test_single_device(device)
        results.append(result)
        
        # Ask if user wants to continue after each device
        if device != devices_to_test[-1]:
            if input("\nContinue testing next device? (y/n): ").lower() != 'y':
                break
    
    # Print summary
    print("\n=== Test Results Summary ===")
    success_count = 0
    
    for success, device_id, info in results:
        if success:
            print(f"✅ {device_id}: Successfully detected as {info}")
            success_count += 1
        else:
            print(f"❌ {device_id}: Failed - {info}")
    
    print(f"\nTested {len(results)} devices: {success_count} successful, {len(results) - success_count} failed")

if __name__ == "__main__":
    asyncio.run(main())