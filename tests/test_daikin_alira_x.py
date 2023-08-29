import pytest

from pydaikin.daikin_brp069 import DaikinBRP069


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
