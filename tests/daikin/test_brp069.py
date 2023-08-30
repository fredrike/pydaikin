import unittest
from unittest.mock import patch

from pydaikin.daikin_brp069 import DaikinBRP069

from .mock import mock_brp069


class TestDaikinBRP069(unittest.IsolatedAsyncioTestCase):

    @patch("pydaikin.daikin_base.ClientSession.get")
    async def test_connect(self, mock_get):
        mock_get.side_effect = mock_brp069

        pydaikin = await DaikinBRP069("1.1.1.1")
        await pydaikin.refresh_data()

        self.assertIn("aircon/get_model_info", pydaikin.values)

    @patch("pydaikin.daikin_base.ClientSession.get")
    async def test_getters(self, mock_get):
        mock_get.side_effect = mock_brp069

        pydaikin = await DaikinBRP069("1.1.1.1")
        await pydaikin.refresh_data()

        self.assertEqual(pydaikin.mac, "40:9F:38:D1:07:AC")
        self.assertEqual(pydaikin.support_away_mode, True)
        self.assertEqual(pydaikin.support_fan_rate, True)
        self.assertEqual(pydaikin.support_swing_mode, True)
        self.assertEqual(pydaikin.support_outside_temperature, True)
        self.assertEqual(pydaikin.support_humidity, False)
        self.assertEqual(pydaikin.support_advanced_modes, True)
        self.assertEqual(pydaikin.support_compressor_frequency, True)
        self.assertEqual(pydaikin.outside_temperature, 21.0)
        self.assertEqual(pydaikin.inside_temperature, 25.0)
        self.assertEqual(pydaikin.target_temperature, None)
        self.assertEqual(pydaikin.compressor_frequency, 40)
        self.assertEqual(pydaikin.humidity, None)
        self.assertEqual(pydaikin.target_humidity, None)
