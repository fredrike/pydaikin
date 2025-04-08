import logging
import asyncio
import ipaddress
import socket
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from pydaikin.discovery import get_devices
from pydaikin.factory import DaikinFactory

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

async def test_single_device(ip_address):
    """Test a single device by IP address."""
    print(f"\n=== Testing device at {ip_address} ===")
    
    try:
        # Try to create device with factory
        device = await DaikinFactory(ip_address)
        
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
        return True, ip_address, device_class
    except Exception as e:
        print(f"Error testing device at {ip_address}: {e}")
        return False, ip_address, str(e)

def is_valid_ip(ip):
    """Check if an IP address is valid."""
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

def ping_host(ip):
    """Check if host is reachable with a ping."""
    try:
        # Create a socket and try to connect with a timeout
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((ip, 80))
        s.close()
        return True
    except:
        return False

async def scan_network(subnet):
    """Scan a subnet for potential Daikin devices."""
    print(f"Scanning subnet {subnet} for devices...")
    
    # Parse subnet to get network address
    network = ipaddress.ip_network(subnet, strict=False)
    
    # Use ThreadPoolExecutor for parallel pinging
    hosts = list(network.hosts())
    print(f"Checking {len(hosts)} IP addresses...")
    
    live_hosts = []
    with ThreadPoolExecutor(max_workers=50) as executor:
        for i, ip in enumerate(hosts):
            ip_str = str(ip)
            if ping_host(ip_str):
                live_hosts.append(ip_str)
                print(f"Found live host: {ip_str}")
            
            # Show progress
            if i % 20 == 0:
                sys.stdout.write(f"\rProgress: {i}/{len(hosts)} IPs checked...")
                sys.stdout.flush()
    
    print(f"\nFound {len(live_hosts)} live hosts on port 80")
    return live_hosts

async def main():
    """Main function to test Daikin devices on the network."""
    print("=== Daikin Device Network Test ===")
    
    # First try to discover devices using discovery
    print("\nAttempting to discover Daikin devices automatically...")
    discovered_devices = get_devices()
    
    if discovered_devices:
        print(f"Discovered {len(discovered_devices)} Daikin devices:")
        for device in discovered_devices:
            print(f"  {device['ip']} ({device['mac']}) - {device['name']}")
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
        
        for device in discovered_devices:
            devices_to_test.append(device['ip'])
    
    elif choice == "2":
        ip = input("Enter IP address to test: ")
        if is_valid_ip(ip):
            devices_to_test.append(ip)
        else:
            print(f"Invalid IP address: {ip}")
            return
    
    elif choice == "3":
        subnet = input("Enter subnet to scan (e.g., 192.168.1.0/24): ")
        try:
            live_hosts = await scan_network(subnet)
            if live_hosts:
                print(f"\nFound {len(live_hosts)} potential devices. Testing each one...")
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
    for ip in devices_to_test:
        result = await test_single_device(ip)
        results.append(result)
    
    # Print summary
    print("\n=== Test Results Summary ===")
    success_count = 0
    
    for success, ip, info in results:
        if success:
            print(f"✅ {ip}: Successfully detected as {info}")
            success_count += 1
        else:
            print(f"❌ {ip}: Failed - {info}")
    
    print(f"\nTested {len(results)} devices: {success_count} successful, {len(results) - success_count} failed")

if __name__ == "__main__":
    asyncio.run(main())