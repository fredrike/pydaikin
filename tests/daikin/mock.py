from urllib.parse import urlparse

from asyncmock import AsyncMock


def mock_brp069(url, *args, **kwargs):

    match urlparse(url).path:
        case "/aircon/get_control_info":
            response = "ret=OK,pow=1,mode=2,adv=,stemp=M,shum=50,dt1=25.0,dt2=M,dt3=25.0,dt4=25.0,dt5=25.0,dt7=25.0,dh1=AUTO,dh2=50,dh3=0,dh4=0,dh5=0,dh7=AUTO,dhh=50,b_mode=2,b_stemp=M,b_shum=50,alert=255,f_rate=A,f_dir=0,b_f_rate=5,b_f_dir=0,dfr1=5,dfr2=5,dfr3=A,dfr4=5,dfr5=5,dfr6=3,dfr7=5,dfrh=5,dfd1=0,dfd2=0,dfd3=2,dfd4=0,dfd5=0,dfd6=2,dfd7=0,dfdh=0,dmnd_run=0,en_demand=0"
        case "/aircon/get_day_power_ex":
            response = "ret=OK,curr_day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_heat=0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0/0,curr_day_cool=0/0/0/0/0/0/0/0/0/0/1/0/0/0/0/0/0/0/0/0/0/0/0/0,prev_1day_cool=0/1/0/1/0/1/0/1/0/2/3/2/3/1/0/0/0/0/5/1/0/1/1/0"
        case "/aircon/get_model_info":
            response = "ret=OK,model=0000,type=N,pv=3.20,cpv=3,cpv_minor=20,mid=NA,humd=0,s_humd=0,acled=0,land=0,elec=1,temp=1,temp_rng=0,m_dtct=1,ac_dst=--,disp_dry=0,dmnd=1,en_scdltmr=1,en_frate=1,en_fdir=1,s_fdir=3,en_rtemp_a=0,en_spmode=7,en_ipw_sep=1,en_mompow=0,hmlmt_l=10.0"
        case "/aircon/get_notify":
            response = "ret=OK,auto_off_flg=0,auto_off_tm=- -"
        case "/aircon/get_price":
            response = "ret=OK,price_int=27,price_dec=0"
        case "/aircon/get_sensor_info":
            response = "ret=OK,htemp=25.0,hhum=-,otemp=21.0,err=0,cmpfreq=40"
        case "/aircon/get_target":
            response = "ret=OK,target=0"
        case "/aircon/get_week_power":
            response = "ret=OK,today_runtime=38,datas=5700/4000/6100/3900/2200/3400/400"
        case "/aircon/get_year_power":
            response = "ret=OK,previous_year=7/0/1/0/1/21/57/24/2/0/0/2,this_year=4/0/0/0/1/18/40/53"
        case "/common/basic_info":
            response = "ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0"
        case "/common/get_datetime":
            response = "ret=OK,sta=2,cur=2023/8/27 21:54:1,reg=eu,dst=1,zone=313"
        case "/common/get_holiday":
            response = "ret=OK,en_hol=0"
        case "/common/get_remote_method":
            response = "ret=OK,method=home only,notice_ip_int=3600,notice_sync_int=60"
        case _:
            response = "ret=PARAM NG,msg=404 Not Found"

    mock = AsyncMock()
    mock.status = 200
    mock.text.return_value = response

    return mock
