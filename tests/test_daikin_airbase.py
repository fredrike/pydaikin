"""Verify that init() calls the expected set of endpoints for each Daikin device."""

from unittest.mock import MagicMock

import pytest

from pydaikin.daikin_airbase import DaikinAirBase

from .test_init import client_session

assert client_session


@pytest.mark.asyncio
async def test_daikinAirBase(aresponses, client_session):
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
        response="ret=OK,pow=1,mode=0,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=5,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=NOTSUPPORT,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=25.0,stemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/get_zone_setting",
        method_pattern="GET",
        response="ret=OK,zone_name=Zone%201;Zone%202;Zone%203;Zone%204;Zone%205;Zone%206;Zone%207;Zone%208,zone_onoff=0;0;0;0;0;0;0;0",
    )

    device = DaikinAirBase('ip', session=client_session)

    await device.init()

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()

    assert device['mode'] == '0'
    assert device.represent('mode') == ('mode', 'fan')
    assert device['model'] == 'Airbase BRP15B61'
    assert device.support_away_mode is False
    assert device.support_fan_rate is True
    assert device.fan_rate == [
        'Auto',
        'Low',
        'Mid',
        'High',
        'Low/Auto',
        'Mid/Auto',
        'High/Auto',
    ]
    assert device.represent('f_rate')[1].title() == 'High'
    assert device.support_swing_mode is False
    assert device.inside_temperature == 25.0
    assert device.target_temperature == 25.0
    assert device.outside_temperature == 21.0
    assert device.zones == [
        ('Zone 1', '0', 0),
        ('Zone 2', '0', 0),
        ('Zone 3', '0', 0),
        ('Zone 4', '0', 0),
        ('Zone 5', '0', 0),
        ('Zone 6', '0', 0),
        ('Zone 7', '0', 0),
        ('Zone 8', '0', 0),
    ]

    # test setting fan to mid
    fan_mode = 'Mid'
    aresponses.add(
        path_pattern="/skyfi/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=0,adv=,stemp=25.0,shum=50,f_rate=A,f_dir=0,f_auto=0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK,f_airside=0,f_auto=0,f_dir=0,f_rate=3,lpw=,mode=2,pow=1,shum=50,stemp=M",
    )
    await device.set({'fan rate': fan_mode})
    aresponses.assert_all_requests_matched()
    assert device.represent('fan rate')[1].title() == fan_mode

    # test setting fan to low/auto
    fan_mode = 'Low/Auto'
    aresponses.add(
        path_pattern="/skyfi/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=0,adv=,stemp=25.0,shum=50,f_rate=A,f_dir=0,f_auto=0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK,f_airside=0,f_auto=1,f_dir=0,f_rate=1a,lpw=,mode=2,pow=1,shum=50,stemp=M",
    )
    await device.set({'fan rate': fan_mode})
    aresponses.assert_all_requests_matched()
    assert device.represent('fan rate')[1].title() == fan_mode

    # test setting mode to cool
    mode = 'cool'
    aresponses.add(
        path_pattern="/skyfi/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=0,adv=,stemp=25.0,shum=50,f_rate=A,f_dir=0,f_auto=1",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK,f_airside=0,f_auto=1,f_dir=0,f_rate=A,lpw=,mode=2,pow=1,shum=50,stemp=M",
    )
    await device.set({'mode': mode})
    aresponses.assert_all_requests_matched()
    assert device.represent("mode") == ('mode', mode)

    # test setting mode to off
    mode = 'off'
    aresponses.add(
        path_pattern="/skyfi/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=2,adv=,stemp=20.0,shum=50,f_rate=A,f_dir=0,f_auto=1",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK,f_airside=0,f_auto=1,f_dir=0,f_rate=A,lpw=,mode=2,pow=0,shum=50,stemp=M",
    )
    await device.set({'mode': mode})
    aresponses.assert_all_requests_matched()
    assert device.represent("mode") == ('mode', mode)

    # test setting zone
    aresponses.add(
        path_pattern="/skyfi/aircon/get_zone_setting",
        method_pattern="GET",
        response="ret=OK,zone_name=Zone%201;Zone%202;Zone%203;Zone%204;Zone%205;Zone%206;Zone%207;Zone%208,zone_onoff=0;0;0;0;0;0;0;0",
    )
    aresponses.add(
        path_pattern="/skyfi/aircon/set_zone_setting",
        method_pattern="GET",
        response="ret=OK,zone_name=Zone%201;Zone%202;Zone%203;Zone%204;Zone%205;Zone%206;Zone%207;Zone%208,zone_onoff=1;0;0;0;0;0;0;0",
    )
    await device.set_zone(0, 'zone_onoff', '1')
    aresponses.assert_all_requests_matched()


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'otemp': '40'}, True),  # outside temperature is supported
        ({'otemp': '25.5'}, True),  # outside temperature is supported (float value)
        ({'otemp': '-6.9'}, True),  # outside temperature is supported (negative value)
        ({'otemp': '-'}, False),  # outside temperature is not supported (non-numeric)
        ({}, False),  # 'otemp' key not present
    ],
)
def test_support_outside_temperature(values, expected):
    """Test the support_outside_temperature property."""
    mock_session = MagicMock()
    device = DaikinAirBase('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.support_outside_temperature is expected


@pytest.mark.parametrize(
    'values, expected',
    [
        ({'otemp': '40'}, 40.0),
        ({'otemp': '25.5'}, 25.5),
        ({'otemp': '-6.9'}, -6.9),
        ({'otemp': '-'}, None),
        ({}, None),  # 'otemp' key not present
    ],
)
def test_outside_temperature(values, expected):
    """Test the outside_temperature property."""
    mock_session = MagicMock()
    device = DaikinAirBase('127.0.0.1', session=mock_session)
    device.values.update(values)
    assert device.outside_temperature == expected
