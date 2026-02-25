from aiohttp import ClientSession
import pytest
import pytest_asyncio

from pydaikin.daikin_brp069 import DaikinBRP069


@pytest_asyncio.fixture
async def client_session():
    client_session = ClientSession()
    yield client_session
    await client_session.close()


@pytest.mark.parametrize(
    'body,values',
    [
        (
            'ret=KO,type=aircon,reg=eu,dst=1',
            dict(),
        ),
        # Response for all fan swing modes http://192.168.3.84/aircon/get_control_info
        (
            'ret=OK,pow=1,mode=4,stemp=20.0,f_rate=B,f_dir_ud=0,f_dir_lr=0',
            dict(
                pow='1',
                mode='4',
                stemp='20.0',
                f_rate='B',
                f_dir_ud='0',
                f_dir_lr='0',
                f_dir='0',
            ),
        ),
        (
            'ret=OK,pow=1,mode=4,stemp=20.0,f_rate=B,f_dir_ud=S,f_dir_lr=0',
            dict(
                pow='1',
                mode='4',
                stemp='20.0',
                f_rate='B',
                f_dir_ud='S',
                f_dir_lr='0',
                f_dir='1',
            ),
        ),
        (
            'ret=OK,pow=1,mode=4,stemp=20.0,f_rate=B,f_dir_ud=0,f_dir_lr=S',
            dict(
                pow='1',
                mode='4',
                stemp='20.0',
                f_rate='B',
                f_dir_ud='0',
                f_dir_lr='S',
                f_dir='2',
            ),
        ),
        (
            'ret=OK,pow=1,mode=4,stemp=20.0,f_rate=B,f_dir_ud=S,f_dir_lr=S',
            dict(
                pow='1',
                mode='4',
                stemp='20.0',
                f_rate='B',
                f_dir_ud='S',
                f_dir_lr='S',
                f_dir='3',
            ),
        ),
        # Test for BRP069
        (
            'ret=OK,pow=1,mode=4,stemp=20.0,f_rate=B,f_dir=2',
            dict(
                pow='1',
                mode='4',
                stemp='20.0',
                f_rate='B',
                f_dir='2',
            ),
        ),
    ],
)
def test_parse_response(body: str, values: dict):
    assert DaikinBRP069.parse_response(body) == values


@pytest.mark.asyncio
async def test_alira_x_init(aresponses, client_session):
    """Test Alira X device initialization with actual sample data."""
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=th,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=th,adp_kind=4,ver=1_19_0,rev=17330723,pv=3.40,cpv=3,cpv_minor=40,pow=0,err=0,location=0,name=%44%61%69%6b%69%6e%41%50%39%36%31%36%32,icon=0,instform=0,method=home only,port=0,id=,pw=,lpw_flag=0,led=1,dst=1,en_setzone=1,mac=9C50D1BD7812,ssid=DaikinAP96162,adp_mode=ap_run,grp_name=,en_grp=0,en_hol=0,edid=0000000003708558,sw_id=1900292A",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=28.0,hhum=-,otemp=32.0,err=0,cmpfreq=0",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=FTXM25QVMA,type=N,pv=3.40,cpv=3,cpv_minor=40,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=0,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=0,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=0,en_mompow=0,hmlmt_l=16.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=0,mode=4,stemp=22.0,shum=0,adv=13,dt1=25.0,dt2=M,dt3=25.0,dt4=22.0,dh1=0,dh2=0,dh3=0,dh4=0,dhh=0,alert=16,f_rate=A,dfr1=A,dfr2=A,dfr3=A,dfr4=A,dfr6=A,dfrh=0,f_dir_ud=0,f_dir_lr=S,ndfd1=00,ndfd2=00,ndfd3=00,ndfd4=0S,ndfd6=00,ndfdh=00",
    )
    aresponses.add(
        path_pattern="/aircon/get_day_power_ex",
        method_pattern="GET",
        response="ret=OK,curr_day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,curr_day_cool=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_cool=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_week_power",
        method_pattern="GET",
        response="ret=OK,today_runtime=0,datas=0/0/0/0/0/0/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_year_power",
        method_pattern="GET",
        response="ret=OK,previous_year=0/0/0/0/0/0/0/0/0/0/0/0,this_year=0/0/0/0/0/0/0/0",
    )

    device = DaikinBRP069('192.168.1.100', session=client_session)
    await device.init()

    # Verify basic device info
    assert device.values.get('mac', invalidate=False) == '9C50D1BD7812'
    assert device.values.get('model', invalidate=False) == 'FTXM25QVMA'
    assert device.values.get('pow', invalidate=False) == '0'
    assert device.values.get('mode', invalidate=False) == '4'

    # Verify Alira X specific swing parameters
    assert device.values.get('f_dir_ud', invalidate=False) == '0'
    assert device.values.get('f_dir_lr', invalidate=False) == 'S'
    # Should compute f_dir as '2' (lr swing only)
    assert device.values.get('f_dir', invalidate=False) == '2'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_alira_x_3d_swing(aresponses, client_session):
    """Test Alira X 3D swing mode (both UD and LR swing)."""
    aresponses.add(
        path_pattern="/common/get_datetime",
        method_pattern="GET",
        response="ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=th,dst=1,zone=313",
    )
    aresponses.add(
        path_pattern="/common/basic_info",
        method_pattern="GET",
        response="ret=OK,type=aircon,reg=th,adp_kind=4,ver=1_19_0,rev=17330723,pv=3.40,cpv=3,cpv_minor=40,pow=1,err=0,location=0,name=%44%61%69%6b%69%6e%41%50%39%36%31%36%32,icon=0,instform=0,method=home only,port=0,id=,pw=,lpw_flag=0,led=1,dst=1,en_setzone=1,mac=9C50D1BD7812,ssid=DaikinAP96162,adp_mode=ap_run,grp_name=,en_grp=0,en_hol=0,edid=0000000003708558,sw_id=1900292A",
    )
    aresponses.add(
        path_pattern="/aircon/get_sensor_info",
        method_pattern="GET",
        response="ret=OK,htemp=28.0,hhum=-,otemp=32.0,err=0,cmpfreq=40",
    )
    aresponses.add(
        path_pattern="/aircon/get_model_info",
        method_pattern="GET",
        response="ret=OK,model=FTXM25QVMA,type=N,pv=3.40,cpv=3,cpv_minor=40,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=0,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=0,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=0,en_mompow=0,hmlmt_l=16.0",
    )
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=4,stemp=20.0,shum=0,adv=13,dt1=25.0,dt2=M,dt3=25.0,dt4=20.0,dh1=0,dh2=0,dh3=0,dh4=0,dhh=0,alert=16,f_rate=B,dfr1=A,dfr2=A,dfr3=A,dfr4=B,dfr6=A,dfrh=0,f_dir_ud=S,f_dir_lr=S,ndfd1=00,ndfd2=00,ndfd3=00,ndfd4=SS,ndfd6=00,ndfdh=00",
    )
    aresponses.add(
        path_pattern="/aircon/get_day_power_ex",
        method_pattern="GET",
        response="ret=OK,curr_day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,curr_day_cool=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_cool=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_week_power",
        method_pattern="GET",
        response="ret=OK,today_runtime=0,datas=0/0/0/0/0/0/0",
    )
    aresponses.add(
        path_pattern="/aircon/get_year_power",
        method_pattern="GET",
        response="ret=OK,previous_year=0/0/0/0/0/0/0/0/0/0/0/0,this_year=0/0/0/0/0/0/0/0",
    )

    device = DaikinBRP069('192.168.1.100', session=client_session)
    await device.init()

    # Verify 3D swing (both UD and LR)
    assert device.values.get('f_dir_ud', invalidate=False) == 'S'
    assert device.values.get('f_dir_lr', invalidate=False) == 'S'
    # Should compute f_dir as '3' (3D swing)
    assert device.values.get('f_dir', invalidate=False) == '3'

    # Test setting swing mode
    aresponses.add(
        path_pattern="/aircon/get_control_info",
        method_pattern="GET",
        response="ret=OK,pow=1,mode=4,stemp=20.0,shum=0,adv=13,dt1=25.0,dt2=M,dt3=25.0,dt4=20.0,dh1=0,dh2=0,dh3=0,dh4=0,dhh=0,alert=16,f_rate=B,dfr1=A,dfr2=A,dfr3=A,dfr4=B,dfr6=A,dfrh=0,f_dir_ud=S,f_dir_lr=S,ndfd1=00,ndfd2=00,ndfd3=00,ndfd4=SS,ndfd6=00,ndfdh=00",
    )
    aresponses.add(
        path_pattern="/aircon/set_control_info",
        method_pattern="GET",
        response="ret=OK",
    )

    # Set to vertical swing only (f_dir='1')
    await device.set({"f_dir": "1"})
    assert device.values.get('f_dir', invalidate=False) == '1'

    aresponses.assert_all_requests_matched()
    aresponses.assert_no_unused_routes()
