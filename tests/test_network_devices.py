import asyncio
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import logging
import socket
import sys
import time

from pydaikin.discovery import get_devices
from pydaikin.factory import DaikinFactory

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_single_device(device_info):
    """Test a single device."""
    if isinstance(device_info, dict):
        ip_address = device_info['ip']
        port = device_info.get('port')
        mac = device_info.get('mac', 'Unknown')
        name = device_info.get('name', 'Unknown')
        device_id = f"{ip_address}:{port}" if port and port != 80 else ip_address
    else:
        # Just an IP address string
        ip_address = device_info
        device_id = ip_address
        mac = "Unknown"
        name = "Unknown"
        port = None

    print(
        f"\n=== Testing device at {ip_address}{f':{port}' if port and port != 80 else ''} ==="
    )
    print(f"Device Name: {name}")
    print(f"Device MAC: {mac}")

    try:
        # Try to create device with factory
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
        if device.values._data.get('pow') == '1':
            # If on, try turning off
            print("\nTesting control - turning device OFF...")
            await device.set({"mode": "off"})
            print(
                f"Power after OFF command: {'On' if device.values._data.get('pow') == '1' else 'Off'}"
            )
            # Wait a moment and turn back on with previous settings
            await asyncio.sleep(2)
            prev_mode = device.values._data.get('mode')
            if prev_mode and prev_mode != 'off':
                print(f"Turning back ON to {prev_mode} mode...")
                await device.set({"mode": prev_mode})
                print(
                    f"Power after ON command: {'On' if device.values._data.get('pow') == '1' else 'Off'}"
                )
        else:
            # If off, try turning on to cool mode
            print("\nTesting control - turning device ON...")
            await device.set({"mode": "cool"})
            print(
                f"Power after ON command: {'On' if device.values._data.get('pow') == '1' else 'Off'}"
            )
            # Wait a moment and turn back off
            await asyncio.sleep(2)
            print("Turning back OFF...")
            await device.set({"mode": "off"})
            print(
                f"Power after OFF command: {'On' if device.values._data.get('pow') == '1' else 'Off'}"
            )

        return True, device_id, device_class
    except Exception as e:
        print(f"Error testing device at {device_id}: {e}")
        return False, device_id, str(e)


async def main():
    """Main function to test Daikin devices on the network."""
    print("=== Daikin Device Network Test ===")

    # First try to discover devices using discovery
    print("\nAttempting to discover Daikin devices automatically...")
    discovered_devices = list(get_devices())

    if discovered_devices:
        print(f"Discovered {len(discovered_devices)} Daikin devices:")
        for device in discovered_devices:
            port_info = (
                f":{device['port']}"
                if 'port' in device and device['port'] != 80
                else ""
            )
            print(
                f"  {device['ip']}{port_info} ({device.get('mac', 'Unknown')}) - {device.get('name', 'Unknown')}"
            )
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

        devices_to_test = discovered_devices

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
            with ThreadPoolExecutor(max_workers=50):
                # Check common Daikin ports: 80 (default), 30050 (BRP devices)
                for port in [80, 30050]:
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
                        except Exception:
                            pass
                        # Show progress
                        if i % 20 == 0 and i > 0:
                            sys.stdout.write(
                                f"\rScanned {i}/{len(hosts)} IPs on port {port}..."
                            )
                            sys.stdout.flush()
                    print(f"\nCompleted scan on port {port}")

            if live_hosts:
                print(
                    f"\nFound {len(live_hosts)} potential devices with open ports. Testing each one..."
                )
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

    # Print summary
    print("\n=== Test Results Summary ===")
    success_count = 0

    for success, device_id, info in results:
        if success:
            print(f"✅ {device_id}: Successfully detected as {info}")
            success_count += 1
        else:
            print(f"❌ {device_id}: Failed - {info}")

    print(
        f"\nTested {len(results)} devices: {success_count} successful, {len(results) - success_count} failed"
    )


if __name__ == "__main__":
    asyncio.run(main())
