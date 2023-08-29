import unittest

from pydaikin.daikin_base import Appliance
from pydaikin.models.base import CommonBasicInfo, DaikinResponse


class TestAppliance(unittest.IsolatedAsyncioTestCase):
    async def test_get_resource(self):
        appliance = Appliance("192.168.1.181")

        response = await appliance._get_resource(CommonBasicInfo)

        self.assertIsInstance(response, DaikinResponse)
