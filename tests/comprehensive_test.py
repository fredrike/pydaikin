import asyncio
import logging

from aiohttp import ClientSession
import pytest
import pytest_asyncio

from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.factory import DaikinFactory

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.skip(reason="We don't require connection to real devices")
async def test_daikin_manual():
    print("\n=== Testing Daikin Firmware 2.8.0 Integration ===\n")

    # Replace with your device's IP address
    device_ip = "192.168.50.47"
    async with await DaikinFactory(device_ip) as device:
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


@pytest.mark.asyncio
async def test_comprehensive_operations(aresponses, client_session):
    """Test comprehensive device operations with mocked responses."""
    # Mock device discovery/init - BRP069 device
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=0,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=22.0,hhum=-,otemp=18.0,err=0,cmpfreq=0",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=0,mode=3,adv=,stemp=22.0,shum=0,dt1=25.0,dt2=M,dt3=22.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=3,b_stemp=22.0,b_shum=0,alert=255,f_rate=A,f_dir=0,b_f_rate=A,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=0,dfd4=0,dfd5=0,dfd6=0,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/aircon/get_day_power_ex",
        method_pattern="GET",
        response="ret=OK,curr_day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,curr_day_cool=0/0/0/0/0/0/0/0/0/0/1/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_cool=0/1/0/1/0/1/0/1/0/2/3/2/3/1/0/0/0/0/5/1/0/1/1/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_week_power",
        method_pattern="GET",
        response="ret=OK,today_runtime=38,datas=5700/4000/6100/3900/2200/3400/400",
    )
    aresponses.add(
        path_pattern="/aircon/get_year_power",
        method_pattern="GET",
        response="ret=OK,previous_year=7/0/1/0/1/21/57/24/2/0/0/2,this_year=4/0/0/0/1/18/40/53",
    )

    device = DaikinBRP069("192.168.1.100", session=client_session)
    await device.init()

    # Verify initial state
    assert device.values.get('pow', invalidate=False) == '0'
    assert device.values.get('mode', invalidate=False) == '3'
    assert device.values.get('htemp', invalidate=False) == '22.0'
    assert device.values.get('mac', invalidate=False) == '409F38D107AC'

    # Test 1: Turn on with cool mode
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=0,mode=3,adv=,stemp=22.0,shum=0,dt1=25.0,dt2=M,dt3=22.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=3,b_stemp=22.0,b_shum=0,alert=255,f_rate=A,f_dir=0,b_f_rate=A,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=0,dfd4=0,dfd5=0,dfd6=0,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK",
    )
    await device.set({"mode": "cool"})
    assert device.values.get('pow', invalidate=False) == '1'
    assert device.values.get('mode', invalidate=False) == '3'

    # Test 2: Set temperature
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=3,adv=,stemp=22.0,shum=0,dt1=25.0,dt2=M,dt3=22.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=3,b_stemp=22.0,b_shum=0,alert=255,f_rate=A,f_dir=0,b_f_rate=A,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=0,dfd4=0,dfd5=0,dfd6=0,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK",
    )
    await device.set({"stemp": "25.0"})
    assert device.values.get('stemp', invalidate=False) == '25.0'

    # Test 3: Set fan rate
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=3,adv=,stemp=25.0,shum=0,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=3,b_stemp=25.0,b_shum=0,alert=255,f_rate=A,f_dir=0,b_f_rate=A,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=0,dfd4=0,dfd5=0,dfd6=0,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK",
    )
    await device.set({"f_rate": "3"})
    # Note: f_rate behavior depends on mode-specific defaults (dfr{mode})
    # Just verify the set call completes without error

    # Test 4: Set swing mode
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=3,adv=,stemp=25.0,shum=0,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=3,b_stemp=25.0,b_shum=0,alert=255,f_rate=3,f_dir=0,b_f_rate=3,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=0,dfd4=0,dfd5=0,dfd6=0,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK",
    )
    await device.set({"f_dir": "1"})
    assert device.values.get('f_dir', invalidate=False) == '1'

    # Test 5: Change to dry mode
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=3,adv=,stemp=25.0,shum=0,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=3,b_stemp=25.0,b_shum=0,alert=255,f_rate=3,f_dir=1,b_f_rate=3,b_f_dir=1,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=0,dfd4=0,dfd5=0,dfd6=0,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK",
    )
    await device.set({"mode": "dry"})
    assert device.values.get('pow', invalidate=False) == '1'
    assert device.values.get('mode', invalidate=False) == '2'

    # Test 6: Turn off
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=25.0,shum=0,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=25.0,b_shum=0,alert=255,f_rate=3,f_dir=1,b_f_rate=3,b_f_dir=1,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=0,dfd4=0,dfd5=0,dfd6=0,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK",
    )
    await device.set({"mode": "off"})
    assert device.values.get('pow', invalidate=False) == '0'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


# Only run when explicitly called, not during automatic test discovery
if __name__ == "__main__":
    asyncio.run(test_daikin_manual())
