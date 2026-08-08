"""Test the DaikinFactory for proper device type detection."""

import json

from aiohttp import ClientSession
import pytest
import pytest_asyncio

from pydaikin.daikin_airbase import DaikinAirBase
from pydaikin.daikin_brp069 import DaikinBRP069
from pydaikin.daikin_brp072c import DaikinBRP072C
from pydaikin.daikin_brp084 import DaikinBRP084
from pydaikin.daikin_skyfi import DaikinSkyFi
from pydaikin.exceptions import DaikinException
from pydaikin.factory import DaikinFactory


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.asyncio
async def test_factory_detects_skyfi(aresponses, client_session):
    """Test that factory correctly detects SkyFi device when password is provided."""
    # Mock SkyFi responses
    aresponses.add(
        path_pattern="/ac.cgi",
        method_pattern="GET",
        response="opmode=0&units=.&settemp=24.0&fanspeed=3&fanflags=1&acmode=16&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1",
    )
    aresponses.add(
        path_pattern="/zones.cgi",
        method_pattern="GET",
        response="opmode=0&units=.&settemp=24.0&fanspeed=3&fanflags=1&acmode=16&tonact=0&toffact=0&prog=0&time=23:36&day=6&roomtemp=23&outsidetemp=0&louvre=1&zone=0&flt=0&test=0&errdata=146&sensors=1",
    )

    device = await DaikinFactory(
        "192.168.1.100", session=client_session, password="test"
    )

    assert isinstance(device, DaikinSkyFi)
    # opmode=0 means device is off, which translates to mode '16' (fan mode in acmode)
    assert device.values.get('mode', invalidate=False) == '16'
    assert device.values.get('pow', invalidate=False) == '0'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_detects_brp072c(aresponses, client_session):
    """Test that factory correctly detects BRP072C device when key is provided."""
    # Mock BRP072C registration and init responses
    aresponses.add(
        path_pattern="/common/register_terminal",
        method_pattern="GET",
        response="ret=OK",
    )
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
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

    device = await DaikinFactory(
        "192.168.1.100", session=client_session, key="testkey123"
    )

    assert isinstance(device, DaikinBRP072C)
    assert device.values.get('mode', invalidate=False) == '2'
    assert device.values.get('mac', invalidate=False) == '409F38D107AC'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_detects_brp084_firmware_280(aresponses, client_session):
    """Test that factory correctly detects BRP084 (firmware 2.8.0) device."""
    # Mock firmware 2.8.0 response
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
                                {"pn": "e_A002", "pch": [{"pn": "p_01", "pv": "01"}]},
                                {
                                    "pn": "e_3001",
                                    "pch": [
                                        {"pn": "p_01", "pv": "0200"},  # Mode (COOL)
                                        {"pn": "p_02", "pv": "32"},  # Cool temp (25°C)
                                        {"pn": "p_09", "pv": "0A00"},  # Cool fan speed
                                        {
                                            "pn": "p_05",
                                            "pv": "000000",
                                        },  # Vertical swing
                                        {
                                            "pn": "p_06",
                                            "pv": "000000",
                                        },  # Horizontal swing
                                    ],
                                },
                                {
                                    "pn": "e_A00B",
                                    "pch": [
                                        {"pn": "p_01", "pv": "18"},  # Room temp
                                        {"pn": "p_02", "pv": "3c"},  # Humidity
                                    ],
                                },
                            ],
                        }
                    ],
                },
                "rsc": 2000,
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
                                    "pch": [{"pn": "p_01", "pv": "22"}],  # Outside temp
                                }
                            ],
                        }
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge/adr_0100.i_power.week_power",
                "pc": {
                    "pn": "week_power",
                    "pch": [
                        {"pn": "today_runtime", "pv": "120"},
                        {"pn": "datas", "pv": [100, 200, 300, 400, 500, 600, 700]},
                    ],
                },
                "rsc": 2000,
            },
            {
                "fr": "/dsiot/edge.adp_i",
                "pc": {"pn": "adp_i", "pch": [{"pn": "mac", "pv": "112233445566"}]},
                "rsc": 2000,
            },
        ]
    }

    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(
            status=200,
            text=json.dumps(mock_response),
            headers={"Content-Type": "application/json"},
        ),
    )

    device = await DaikinFactory("192.168.1.100", session=client_session)

    assert isinstance(device, DaikinBRP084)
    assert device.values.get('mode', invalidate=False) == 'cool'
    assert device.values.get('mac', invalidate=False) == '112233445566'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_detects_brp069(aresponses, client_session):
    """Test that factory correctly detects BRP069 device (fallback from BRP084)."""
    # Mock 404 response for firmware 2.8.0 attempt (to force fallback)
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock BRP069 responses (detection phase)
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    # Mock BRP069 init responses (basic_info is skipped due to caching from detection)
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
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

    device = await DaikinFactory("192.168.1.100", session=client_session)

    assert isinstance(device, DaikinBRP069)
    assert device.values.get('mode', invalidate=False) == '2'
    assert device.values.get('mac', invalidate=False) == '409F38D107AC'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_unsupported_brp069c8x_firmware_230(aresponses, client_session):
    """BRP069C8x firmware 2.3.0 (type=aircon, subtype=qa) reports a clear error."""
    # Mock 404 response for firmware 2.8.0 attempt (to force fallback)
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # BRP069C8x answers /common/basic_info but all /aircon endpoints 404
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,subtype=qa,reg=eu,dst=1,ver=2_3_0,rev=F45236EA,pow=0,err=0,location=0,name=%44%61%69%6b%69%6e%20%52%45,icon=31,method=polling,port=30050,id=,lpw_flag=0,adp_kind=4,pv=0,cpv=0,led=1,en_setzone=1,mac=409F38D107AC,ssid=Daikin,adp_mode=ap_run,en_hol=0,grp_name=,en_grp=0,edid=0000000003708559,sw_id=19002959,pw=,ssid1=Daikin,radio1=-52",
    )
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2026/5/27 15:16:44,reg=eu,dst=1,zone=211",
    )
    for endpoint in (
        "/aircon/get_sensor_info",
        "/aircon/get_model_info",
        "/aircon/get_control_info",
        "/aircon/get_day_power_ex",
        "/aircon/get_week_power",
        "/aircon/get_year_power",
    ):
        aresponses.add(
            path_pattern=endpoint,
            method_pattern="GET",
            response=aresponses.Response(status=404, text="Page Not Found"),
        )

    with pytest.raises(
        DaikinException, match="BRP069C8x with firmware 2.3.0 is not supported"
    ):
        await DaikinFactory("192.168.1.100", session=client_session)

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_unsupported_unknown_device_reports_details(
    aresponses, client_session
):
    """An unsupported device without known fingerprint still reports detected info."""
    # Mock 404 response for firmware 2.8.0 attempt (to force fallback)
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    for endpoint in (
        "/aircon/get_sensor_info",
        "/aircon/get_model_info",
        "/aircon/get_control_info",
        "/aircon/get_day_power_ex",
        "/aircon/get_week_power",
        "/aircon/get_year_power",
    ):
        aresponses.add(
            path_pattern=endpoint,
            method_pattern="GET",
            response=aresponses.Response(status=404, text="Page Not Found"),
        )

    with pytest.raises(
        DaikinException,
        match="detected type=aircon, firmware 1.2.54, adp_kind=3.*not supported",
    ):
        await DaikinFactory("192.168.1.100", session=client_session)
    """Test that factory correctly detects AirBase device (fallback from BRP069)."""
    # Mock 404 response for firmware 2.8.0 attempt
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock 404 response for BRP069 attempt (to force fallback to AirBase)
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock AirBase responses (uses /skyfi/ prefix)
    aresponses.add(
        path_pattern="/skyfi/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/skyfi/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_zone_setting",
        method_pattern="GET",
        response="ret=OK",
    )

    device = await DaikinFactory("192.168.1.100", session=client_session)

    assert isinstance(device, DaikinAirBase)
    assert device.values.get('mode', invalidate=False) == '2'
    assert device.values.get('mac', invalidate=False) == '409F38D107AC'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_port_extraction_from_device_id(aresponses, client_session):
    """Test that factory correctly extracts port from device_id like '192.168.1.100:8080'."""
    # Mock 404 for firmware 2.8.0
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock BRP069 responses (detection phase)
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    # Mock BRP069 init responses (basic_info is skipped due to caching from detection)
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
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

    # Test with port in device_id
    device = await DaikinFactory("192.168.1.100:8080", session=client_session)

    assert isinstance(device, DaikinBRP069)
    assert "8080" in device.base_url

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_brp069_custom_port_80(aresponses, client_session):
    """Test that factory doesn't customize URL when port is 80 (default)."""
    # Mock 404 for firmware 2.8.0
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock BRP069 responses with port 80 in device_id
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,pow=1,mode=2,mac=409F38D107AC",
    )
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2",
    )
    aresponses.add(
        path_pattern="/aircon/get_day_power_ex",
        method_pattern="GET",
        response="ret=OK,curr_day_heat=0/0/0/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_week_power",
        method_pattern="GET",
        response="ret=OK,today_runtime=38",
    )
    aresponses.add(
        path_pattern="/aircon/get_year_power",
        method_pattern="GET",
        response="ret=OK,previous_year=7/0",
    )

    device = await DaikinFactory("192.168.1.100:80", session=client_session)

    assert isinstance(device, DaikinBRP069)
    # Port 80 is default, should not be in URL
    assert device.base_url == "http://192.168.1.100"

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


# ---------------------------------------------------------------------------
# Tests for _try_brp072c fallback behavior
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_brp072c_success(aresponses, client_session):
    """Key provided and BRP072C init succeeds -> returns BRP072C."""
    aresponses.add(
        path_pattern="/common/register_terminal",
        method_pattern="GET",
        response="ret=OK",
    )
    aresponses.add(
        path_pattern="/common/register_terminal",
        method_pattern="GET",
        response="ret=OK",
    )
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
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

    device = await DaikinFactory("192.168.1.100", session=client_session, key="testkey")

    assert isinstance(device, DaikinBRP072C)
    assert device.values.get("mode", invalidate=False) == "2"
    assert device.values.get("mac", invalidate=False) == "409F38D107AC"


# ---------------------------------------------------------------------------
# Tests for ClientSession lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factory_owns_and_closes_created_session(aresponses):
    """A session created by the factory is owned and closed by aclose()."""
    # Mock 404 for firmware 2.8.0 attempt (to force fallback)
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock BRP069 responses (detection phase)
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    # Mock BRP069 init responses (basic_info is skipped due to caching from detection)
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
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

    device = await DaikinFactory("192.168.1.100")

    assert isinstance(device, DaikinBRP069)
    assert device._own_session is True
    session = device.session
    assert not session.closed

    await device.aclose()

    assert session.closed

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_does_not_close_external_session(aresponses, client_session):
    """A caller-provided session is not closed by aclose()."""
    # Mock 404 for firmware 2.8.0 attempt (to force fallback)
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock BRP069 responses (detection phase)
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0",
    )
    # Mock BRP069 init responses (basic_info is skipped due to caching from detection)
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
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

    device = await DaikinFactory("192.168.1.100", session=client_session)

    assert isinstance(device, DaikinBRP069)
    assert device.session is client_session
    assert device._own_session is False

    await device.aclose()

    assert not client_session.closed

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_factory_closes_session_on_unsupported_device(aresponses, monkeypatch):
    """The factory closes the session it created when device creation fails."""
    closed_sessions = []
    original_close = ClientSession.close

    async def recording_close(self):
        closed_sessions.append(self)
        await original_close(self)

    monkeypatch.setattr(ClientSession, "close", recording_close)

    # Mock 404 for firmware 2.8.0 attempt (to force fallback)
    aresponses.add(
        path_pattern="/dsiot/multireq",
        method_pattern="POST",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock 404 for BRP069 attempt (to force fallback to AirBase)
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response=aresponses.Response(status=404, text="Not Found"),
    )

    # Mock AirBase responses that report no mode -> device is unsupported
    aresponses.add(
        path_pattern="/skyfi/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/skyfi/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=0000",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_zone_setting",
        method_pattern="GET",
        response="ret=OK",
    )

    with pytest.raises(DaikinException, match="not supported"):
        await DaikinFactory("192.168.1.100")

    assert len(closed_sessions) == 1
    assert closed_sessions[0].closed


@pytest.mark.asyncio
async def test_factory_brp084_without_mode_initializes_off(monkeypatch, client_session):
    """A BRP084 that reports no mode value is initialized to 'off'."""
    from pydaikin.daikin_brp084 import DaikinBRP084

    async def fake_update_status(self, *args, **kwargs):
        self.values["mac"] = "112233445566"

    monkeypatch.setattr(DaikinBRP084, "update_status", fake_update_status)

    device = await DaikinFactory("192.168.1.100", session=client_session)

    assert isinstance(device, DaikinBRP084)
    assert device.values.get("mode", invalidate=False) == "off"
    assert device.values.get("pow", invalidate=False) == "0"


@pytest.mark.asyncio
async def test_factory_brp072c_init_fails_falls_back(monkeypatch, client_session):
    """Factory falls back to the next device type when BRP072C init fails."""
    from pydaikin.daikin_brp072c import DaikinBRP072C
    from pydaikin.daikin_brp084 import DaikinBRP084

    async def fail_init(self):
        raise TimeoutError("connection timeout")

    async def brp084_success(self, *args, **kwargs):
        self.values["mac"] = "112233445566"
        self.values["mode"] = "cool"

    monkeypatch.setattr(DaikinBRP072C, "init", fail_init)
    monkeypatch.setattr(DaikinBRP084, "update_status", brp084_success)

    device = await DaikinFactory("192.168.1.100", session=client_session, key="testkey")

    assert isinstance(device, DaikinBRP084)


def test_extract_ip_port_from_discovery(monkeypatch):
    """Port is taken from the discovery lookup when no port is in the id."""
    monkeypatch.setattr(
        "pydaikin.factory.get_name",
        lambda name: {"ip": "10.0.0.5", "port": "30050", "name": name},
    )

    device_ip, port = DaikinFactory._extract_ip_port("livingroom")

    assert device_ip == "10.0.0.5"
    assert port == 30050


def test_extract_ip_port_discovery_error(monkeypatch):
    """A failing discovery lookup falls back to the raw device id."""

    def raise_keyerror(name):
        raise KeyError("not found")

    monkeypatch.setattr("pydaikin.factory.get_name", raise_keyerror)

    device_ip, port = DaikinFactory._extract_ip_port("livingroom")

    assert device_ip == "livingroom"
    assert port is None
