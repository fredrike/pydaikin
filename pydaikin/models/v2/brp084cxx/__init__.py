
"""Base models common to all Daikin devices"""
from pydantic import BaseModel


class ResponseObject(BaseModel):
    pn: str


class Response(BaseModel):
    fr: str
    pc: ResponseObject


class CloudDaikinBaseResponse(BaseModel):
    """model to represent all responses from Daikin controller

    Checks that ret == "OK" and parses data automatically
    if provided as _response param
    """

    responses: list[Response]


a = CloudDaikinBaseResponse.model_validate_json(
    """{
        "responses": [
            {
                "pn": "ciao"
            },
            {
                "pf": 4
            }
        ]
    }"""
)
