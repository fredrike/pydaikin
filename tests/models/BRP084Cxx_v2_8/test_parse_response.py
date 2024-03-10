import json
import os
import unittest

from pydaikin.models.BRP084Cxx_v2_8.model import BRP084cxxV28Response, ItemWithValue, Pc


class TestParser(unittest.IsolatedAsyncioTestCase):
    def test_parse(self):
        with open(os.path.dirname(__file__) + "/fixtures/first_discovery.json", "r") as infile:
            responsedata = json.load(infile)

        response = BRP084cxxV28Response.model_validate(responsedata)
        assert response

    def test_small(self):
        responsedata = {
            "pn": "timz",
            "pt": 1,
            "pch": [
                {
                    "pn": "tmdf",
                    "pt": 2,
                    "pv": 600,
                    "md": {
                        "pt": "i"
                    }
                },
                {
                    "pn": "dst",
                    "pt": 2,
                    "pv": 1,
                    "md": {
                        "pt": "i"
                    }
                },
                {
                    "pn": "zone",
                    "pt": 2,
                    "pv": 234,
                    "md": {
                        "pt": "i"
                    }
                }
            ]
        }

        response = Pc.model_validate(responsedata)
        assert response

    def test_item_with_value(self):
        responsedata = {
            "pn": "tmdf",
            "pt": 2,
            "pv": 600,
            "md": {
                "pt": "i"
            }
        }

        response = ItemWithValue.model_validate(responsedata)
        assert response
