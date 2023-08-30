import unittest
from unittest.mock import patch

from aiohttp.web_exceptions import HTTPForbidden
from asyncmock import AsyncMock

from pydaikin.daikin_base import Appliance
from pydaikin.models.base import CommonBasicInfo, DaikinResponse

from .mock import mock_brp069


class TestAppliance(unittest.IsolatedAsyncioTestCase):

    @patch("pydaikin.daikin_base.ClientSession.get")
    async def test_get_resource(self, mock_get):
        mockresponse = AsyncMock()
        mockresponse.text.return_value = "ret=OK,type=aircon,reg=eu,dst=1,ver=1_2_54,rev=203DE8C,pow=1,err=0,location=0,name=%4e%6f%74%74%65,icon=3,method=home only,port=30050,id=,pw=,lpw_flag=0,adp_kind=3,pv=3.20,cpv=3,cpv_minor=20,led=1,en_setzone=1,mac=409F38D107AC,adp_mode=run,en_hol=0,ssid1=Pinguino Curioso,radio1=-35,grp_name=,en_grp=0"
        mockresponse.status = 200
        mock_get.return_value.__aenter__.return_value = mockresponse

        appliance = await Appliance("192.168.1.181")

        response = await appliance._get_resource(CommonBasicInfo)

        self.assertIsInstance(response, DaikinResponse)

    @patch("pydaikin.daikin_base.ClientSession.get")
    async def test_fail_on_403(self, mock_get):
        mockresponse = AsyncMock()
        mockresponse.text.return_value = ""
        mockresponse.status = 403
        mock_get.return_value.__aenter__.return_value = mockresponse

        appliance = await Appliance("192.168.1.181")

        with self.assertRaises(HTTPForbidden):
            await appliance._get_resource(CommonBasicInfo)

    @patch("pydaikin.daikin_base.ClientSession.get")
    async def test_fail_on_invalid_input(self, mock_get):
        mockresponse = AsyncMock()
        mockresponse.text.return_value = "asganaway"
        mockresponse.status = 200
        mock_get.return_value.__aenter__.return_value = mockresponse

        appliance = await Appliance("192.168.1.181")

        with self.assertRaises(ValueError):
            await appliance._get_resource(CommonBasicInfo)

    @patch("pydaikin.daikin_base.ClientSession.get")
    async def test_connect(self, mock_get):
        mock_get.side_effect = mock_brp069

        appliance = await Appliance("192.168.1.181")
        appliance.http_resources = {
            "common/basic_info": CommonBasicInfo
        }

        await appliance.connect()

        self.assertIsInstance(appliance.values["common/basic_info"], CommonBasicInfo)
