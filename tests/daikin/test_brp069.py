import unittest
from unittest.mock import patch

from pydaikin.daikin_brp069 import DaikinBRP069

from .mock import mock_brp069


class TestDaikinBRP069(unittest.IsolatedAsyncioTestCase):

    @patch("pydaikin.daikin_base.ClientSession.get")
    async def test_connect(self, mock_get):
        mock_get.side_effect = mock_brp069

        pydaikin = await DaikinBRP069("1.1.1.1")
        await pydaikin.connect()

        self.assertIn("aircon/get_model_info", pydaikin.values)
