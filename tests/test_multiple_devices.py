import logging
import asyncio
import pytest
import json
import aiohttp
from aiohttp import web
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from pydaikin.factory import DaikinFactory
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.daikin_airbase import DaikinAirBase
from pydaikin.daikin_brp_280 import DaikinBRP280
from pydaikin.daikin_skyfi import DaikinSkyFi

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

class FakeDaikinServer:
    """Simulate different types of Daikin devices."""
    
    def __init__(self, device_type="brp069"):
        self.device_type = device_type
        self.app = web.Application()
        self.runner = None
        self.site = None
        
        # Set up routes based on device type
        if device_type == "brp069":
            self._setup_brp069_routes()
        elif device_type == "airbase":
            self._setup_airbase_routes()
        elif device_type == "firmware280":
            self._setup_firmware280_routes()
        elif device_type == "skyfi":
            self._setup_skyfi_routes()
    
    def _setup_brp069_routes(self):
        """Set up routes for BRP069 device."""
        self.app.router.add_get('/common/basic_info', self._handle_brp069_basic_info)
        self.app.router.add_get('/aircon/get_sensor_info', self._handle_brp069_sensor_info)
        self.app.router.add_get('/aircon/get_control_info', self._handle_brp069_control_info)
    
    def _setup_airbase_routes(self):
        """Set up routes for AirBase device."""
        self.app.router.add_get('/skyfi/common/basic_info', self._handle_airbase_basic_info)
        self.app.router.add_get('/skyfi/aircon/get_control_info', self._handle_airbase_control_info)
        self.app.router.add_get('/skyfi/aircon/get_model_info', self._handle_airbase_model_info)
        self.app.router.add_get('/skyfi/aircon/get_sensor_info', self._handle_airbase_sensor_info)
        self.app.router.add_get('/skyfi/aircon/get_zone_setting', self._handle_airbase_zone_setting)
        # For BRP069 routes, return 404
        self.app.router.add_get('/common/basic_info', self._handle_not_found)
    
    def _setup_firmware280_routes(self):
        """Set up routes for firmware 2.8.0 device."""
        self.app.router.add_post('/dsiot/multireq', self._handle_firmware280_multireq)
        # For BRP069 routes, return 404
        self.app.router.add_get('/common/basic_info', self._handle_not_found)
    
    def _setup_skyfi_routes(self):
        """Set up routes for SkyFi device."""
        self.app.router.add_get('/ac.cgi', self._handle_skyfi_ac_cgi)
        self.app.router.add_get('/zones.cgi', self._handle_skyfi_zones_cgi)
        # For BRP069 routes, return 404
        self.app.router.add_get('/common/basic_info', self._handle_not_found)
    
    async def _handle_brp069_basic_info(self, request):
        """Handle BRP069 basic_info request."""
        return web.Response(text="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Mock Device,radio1=-35,grp_name=,en_grp=0")
    
    async def _handle_brp069_sensor_info(self, request):
        """Handle BRP069 sensor_info request."""
        return web.Response(text="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40")
    
    async def _handle_brp069_control_info(self, request):
        """Handle BRP069 control_info request."""
        return web.Response(text="ret=OK,pow=1,mode=3,stemp=25.0,shum=0,f_rate=A,f_dir=0")
    
    async def _handle_airbase_basic_info(self, request):
        """Handle AirBase basic_info request."""
        return web.Response(text="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Mock Device,radio1=-35,grp_name=,en_grp=0")
    
    async def _handle_airbase_control_info(self, request):
        """Handle AirBase control_info request."""
        return web.Response(text="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,f_rate=A,f_dir=0,f_auto=1")
    
    async def _handle_airbase_model_info(self, request):
        """Handle AirBase model_info request."""
        return web.Response(text="ret=OK,model=NOTSUPPORT,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0")
    
    async def _handle_airbase_sensor_info(self, request):
        """Handle AirBase sensor_info request."""
        return web.Response(text="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40")
    
    async def _handle_airbase_zone_setting(self, request):
        """Handle AirBase zone_setting request."""
        return web.Response(text="ret=OK,zone_name=Zone%201;Zone%202,zone_onoff=1;0")
    
    async def _handle_firmware280_multireq(self, request):
        """Handle firmware 2.8.0 multireq request."""
        mock_response = {
            "responses": [
                {
                    "fr": "/dsiot/edge/adr_0100.dgc_status",
                    "pc": {
                        "pn": "dgc_status",
                        "pch": [
                            {
                                "pn": "e_1002",
                                "pch": [
                                    {
                                        "pn": "e_A002",
                                        "pch": [{"pn": "p_01", "pv": "01"}]
                                    },
                                    {
                                        "pn": "e_3001",
                                        "pch": [
                                            {"pn": "p_01", "pv": "0300"},  # Mode (AUTO)
                                            {"pn": "p_1D", "pv": "32"},     # Auto temp (25°C)
                                            {"pn": "p_26", "pv": "0A00"},   # Auto fan speed (AUTO)
                                            {"pn": "p_20", "pv": "0F0000"}, # Vertical swing ON
                                            {"pn": "p_21", "pv": "0F0000"}  # Horizontal swing ON
                                        ]
                                    },
                                    {
                                        "pn": "e_A00B",
                                        "pch": [
                                            {"pn": "p_01", "pv": "19"},  # Room temp (25°C)
                                            {"pn": "p_02", "pv": "37"}   # Humidity (55%)
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    "rsc": 2000
                },
                {
                    "fr": "/dsiot/edge/adr_0200.dgc_status",
                    "pc": {
                        "pn": "dgc_status",
                        "pch": [
                            {
                                "pn": "e_1003",
                                "pch": [
                                    {
                                        "pn": "e_A00D",
                                        "pch": [{"pn": "p_01", "pv": "18"}]  # Outside temp (24°C)
                                    }
                                ]
                            }
                        ]
                    },
                    "rsc": 2000
                },
                {
                    "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                    "pc": {
                        "pn": "week_power",
                        "pch": [
                            {"pn": "today_runtime", "pv": "0"},
                            {"pn": "datas", "pv": [0, 0, 0, 0, 0, 0, 0]}
                        ]
                    },
                    "rsc": 2000
                },
                {
                    "fr": "/dsiot/edge.adp_i",
                    "pc": {
                        "pn": "adp_i",
                        "pch": [{"pn": "mac", "pv": "112233445566"}]
                    },
                    "rsc": 2000
                }
            ]
        }
        return web.json_response(mock_response)
    
    async def _handle_skyfi_ac_cgi(self, request):
        """Handle SkyFi ac.cgi request."""
        return web.Response(text="opmode=1&units=.&settemp=24.0&fanspeed=3&fanflags=1&acmode=8&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1")
    
    async def _handle_skyfi_zones_cgi(self, request):
        """Handle SkyFi zones.cgi request."""
        return web.Response(text="nz=8&zone1=Zone%201&zone2=Zone%202&zone3=Zone%203&zone4=Zone%204&zone5=Zone%205&zone6=Zone%206&zone7=Zone%207&zone8=Zone%208")
    
    async def _handle_not_found(self, request):
        """Handle 404 response."""
        return web.Response(status=404)
    
    async def start(self, host="127.0.0.1", port=8080):
        """Start the fake server."""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, host, port)
        await self.site.start()
        return f"http://{host}:{port}"
    
    async def stop(self):
        """Stop the fake server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()


async def test_device_factory():
    """Test that the factory correctly identifies different device types."""
    results = []
    
    # Test each device type
    for device_type in ["firmware280", "brp069", "airbase", "skyfi"]:
        server = FakeDaikinServer(device_type)
        base_url = await server.start()
        
        try:
            device = None
            # SkyFi needs a password
            if device_type == "skyfi":
                device = await DaikinFactory(base_url.replace("http://", ""), password="password")
            else:
                device = await DaikinFactory(base_url.replace("http://", ""))
            
            # Check that the correct device type was created
            device_class_name = type(device).__name__
            print(f"Device type '{device_type}' was identified as: {device_class_name}")
            
            expected_class = None
            if device_type == "firmware280":
                expected_class = DaikinBRP280
            elif device_type == "brp069":
                expected_class = DaikinBRP069
            elif device_type == "airbase":
                expected_class = DaikinAirBase
            elif device_type == "skyfi":
                expected_class = DaikinSkyFi
            
            assert isinstance(device, expected_class), f"Expected {expected_class.__name__}, got {device_class_name}"
            
            # Check that we can read basic info
            print(f"Device values: {list(device.values.keys())}")
            assert "mode" in device.values, "Basic mode value not found"
            
            results.append({
                "device_type": device_type,
                "identified_as": device_class_name,
                "success": isinstance(device, expected_class),
            })
            
        except Exception as e:
            print(f"Error testing {device_type}: {e}")
            results.append({
                "device_type": device_type,
                "error": str(e),
                "success": False,
            })
        finally:
            await server.stop()
    
    # Print summary
    print("\n=== Factory Test Results ===")
    for result in results:
        status = "✅ SUCCESS" if result.get("success") else "❌ FAILED"
        if "error" in result:
            print(f"{status} - {result['device_type']}: {result['error']}")
        else:
            print(f"{status} - {result['device_type']}: Identified as {result['identified_as']}")
    
    # Overall success
    overall_success = all(result.get("success", False) for result in results)
    print(f"\nOverall Test {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    return overall_success

if __name__ == "__main__":
    asyncio.run(test_device_factory())