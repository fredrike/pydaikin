"""Base models common to all Daikin devices"""
from datetime import datetime, timedelta
import re
from typing import Optional
from urllib.parse import unquote

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator


def calculate_expiration_date() -> datetime:
    """Return a datetime 15 minutes into the future.
    Used as default value for _expiration_date unless otherwise set
    """
    return datetime.now() + timedelta(minutes=15)


class DaikinResponse(BaseModel):
    """model to represent all responses from Daikin controller

    Checks that ret == "OK" and parses data automatically
    if provided as _response param
    """

    ret: str = Field(exclude=True)
    expiration_date: datetime = Field(
        default_factory=calculate_expiration_date, exclude=True
    )

    @field_validator("ret", mode="after")
    @classmethod
    def validate_ret(cls, value):
        "Validate field ret contains 'OK'"
        assert value == "OK"
        return value

    @model_validator(mode="before")
    @staticmethod
    def responseparser(value: dict):
        "Split incoming request string into fields"
        if "_response" not in value:
            return value

        # Regex because fields are not escaped, and we want to match fields
        # containing a comma inside it
        # https://github.com/home-assistant/core/issues/76238

        response = dict(
            (match.group(1), match.group(2))
            for match in re.finditer(r'(\w+)=([^=]*)(?:,|$)', value['_response'])
        )
        value.pop("_response")

        value.update(response)
        return value

    @computed_field
    @property
    def is_stale(self) -> bool:
        "Return whether the object should be refreshed or not"
        return datetime.now() > self.expiration_date

    def expire_now(self) -> None:
        "Set immediately as stale"
        self.expiration_date = datetime.now()

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        raise NotImplementedError


class CommonBasicInfo(DaikinResponse):
    "Model for common/basic_info"
    dst: bool
    en_hol: Optional[bool] = Field(description="awayMode")
    mac: str
    name: str
    pow: bool = Field(description="power")
    reg: str
    rev: str
    type: str
    ver: str = Field(description="firmware adapter")

    @field_validator("name", mode="before")
    @classmethod
    def validate_name(cls, value):
        "Convert name from URL-quoted to plain string"
        return unquote(value)

    @field_validator("mac", mode="before")
    @classmethod
    def validate_mac(cls, value: str):
        "Convert mac into EUI object"
        mac = ':'.join(value[i : i + 2] for i in range(0, len(value), 2))
        return unquote(mac).split(';', maxsplit=1)[0]

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "common/basic_info"

    @property
    def support_away_mode(self) -> bool:
        return self.en_hol is not None
