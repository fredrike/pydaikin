"Models and enums for BRP069"
# pylint: disable=too-few-public-methods,relative-beyond-top-level
from enum import Enum

from pydantic import Field, computed_field

from .base import DaikinResponse
from .types import (
    Date,
    PowerUsageList1Wh,
    PowerUsageList100Wh,
    PowerUsageList1000Wh,
    PowerUsageSum1Wh,
    PowerUsageSum100Wh,
    PowerUsageSum1000Wh,
)


class AirconModeEnum(Enum):
    "Enum for mode field"
    AUTO = "0"
    AUTO_1 = "1"
    DRY = "2"
    COOL = "3"
    HOT = "4"
    FAN = "6"
    AUTO_7 = "7"
    OFF = "10"


class AirconModeHumanEnum(Enum):
    "Enum for human representation of mode field"
    AUTO = "auto"
    AUTO_1 = "auto-1"
    DRY = "dry"
    COOL = "cool"
    HOT = "hot"
    FAN = "fan"
    AUTO_7 = "auto_7"
    OFF = "off"


class FanRateEnum(Enum):
    "Enum for fan field"
    AUTO = "A"
    SILENCE = "B"
    S_1 = "3"
    S_2 = "4"
    S_3 = "5"
    S_4 = "6"
    S_5 = "7"


class FanRateHumanEnum(Enum):
    "Enum for human representation of fan field"
    AUTO = "auto"
    SILENCE = "silence"
    S_1 = "1"
    S_2 = "2"
    S_3 = "3"
    S_4 = "4"
    S_5 = "5"


class FanDirectionEnum(Enum):
    "Enum for fan direction field"
    OFF = "0"
    VERTICAL = "1"
    HORIZONTAL = "2"
    THREE_D = "3"


class FanDirectionHumanEnum(Enum):
    "Enum for human representation of fan direction field"
    OFF = "off"
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"
    THREE_D = "3d"


class AdvEnum(Enum):
    "Enum for advanced field"
    OFF = ''
    POWERFUL = '2'
    POWERFUL_STREAMER = '2/13'
    ECONO = '12'
    ECONO_STREAMER = '12/13'
    STREAMER = '13'


class AdvHumanEnum(Enum):
    "Enum for human representation of advanced field"
    OFF = 'off'
    POWERFUL = 'powerful'
    POWERFUL_STREAMER = 'powerful streamer'
    ECONO = 'econo'
    ECONO_STREAMER = 'econo_streamer'
    STREAMER = 'streamer'


class AirconGetSensorInfo(DaikinResponse):
    "Model for aircon/get_sensor_info"
    cmpfreq: int = Field(description="compressor frequency")
    err: int = Field(description="error code")
    htemp: float = Field(description="inside temp")
    otemp: float = Field(description="outside temp")

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_sensor_info"


class AirconGetControlInfo(DaikinResponse):
    "Model for aircon/get_control_info"
    adv: AdvEnum = Field(description="advanced mode")
    f_dir: FanDirectionEnum = Field(description="fan direction")
    f_rate: FanRateEnum = Field(description="fan rate")
    mode: AirconModeEnum
    stemp: float = Field(description="target temp")

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_control_info"


class AirconGetDayPowerEx(DaikinResponse):
    "Model for aircon/get_day_power_ex"
    curr_day_cool_kwh: PowerUsageSum100Wh = Field(validation_alias="curr_day_cool")
    curr_day_cool_list_kwh: PowerUsageList100Wh = Field(
        validation_alias="curr_day_cool"
    )
    curr_day_heat_kwh: PowerUsageSum100Wh = Field(validation_alias="curr_day_heat")
    curr_day_heat_list_kwh: PowerUsageList100Wh = Field(
        validation_alias="curr_day_heat"
    )
    prev_1day_cool_kwh: PowerUsageSum100Wh = Field(validation_alias="prev_1day_cool")
    prev_1day_cool_list_kwh: PowerUsageList100Wh = Field(
        validation_alias="prev_1day_cool"
    )
    prev_1day_heat_kwh: PowerUsageSum100Wh = Field(validation_alias="prev_1day_heat")
    prev_1day_heat_list_kwh: PowerUsageList100Wh = Field(
        validation_alias="prev_1day_heat"
    )

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_day_power_ex"


class AirconGetModelInfo(DaikinResponse):
    "Model for aircon/get_model_info"
    model: str

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_model_info"


class AirconGetPrice(DaikinResponse):
    "Model for aircon/get_price"
    price_dec: int
    price_int: int

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_price"


class AirconGetTarget(DaikinResponse):
    "Model for aircon/get_target"
    target: int

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_target"


class AirconGetWeekPower(DaikinResponse):
    "Model for aircon/get_week_power"
    datas_kwh: PowerUsageSum1Wh = Field(validation_alias="datas")
    datas_list_kwh: PowerUsageList1Wh = Field(validation_alias="datas")
    today_runtime: int

    @computed_field
    def today_kwh(self) -> float:
        "Return first element of list"
        return self.datas_list_kwh[0]  # pylint: disable=unsubscriptable-object

    @computed_field
    def yesterday_kwh(self) -> float:
        "Return second element of list"
        return self.datas_list_kwh[1]  # pylint: disable=unsubscriptable-object

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_week_power"


class AirconGetYearPower(DaikinResponse):
    "Model for aircon/get_year_power"
    previous_year_kwh: PowerUsageSum1000Wh = Field(validation_alias="previous_year")
    previous_year_list_kwh: PowerUsageList1000Wh = Field(
        validation_alias="previous_year"
    )
    this_year_kwh: PowerUsageSum1000Wh = Field(validation_alias="this_year")
    this_year_list_kwh: PowerUsageList1000Wh = Field(validation_alias="this_year")

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_year_power"


class CommonGetdatetime(DaikinResponse):
    "Model for aircon/get_datetime"
    cur: Date = Field(description="internal clock")

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_datetime"


class CommonGetHoliday(DaikinResponse):
    "Model for aircon/get_holiday"

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_holiday"


class CommonGetNotify(DaikinResponse):
    "Model for aircon/get_notify"

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_notify"


class CommonGetRemoteMethod(DaikinResponse):
    "Model for aircon/get_remote_method"

    @classmethod
    def get_url(cls):
        "Get url of this resource"
        return "aircon/get_remote_method"
