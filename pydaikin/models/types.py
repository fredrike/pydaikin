"Custom type container for pydantic models"
from datetime import datetime
from typing import List

from pydantic import BeforeValidator
from typing_extensions import Annotated


def split_data(value: str) -> List[int]:
    """
    in: '1/2/3/4'
    out: [1,2,3,4]
    """
    return [int(x) for x in value.split("/")]


# Power consumpion is represented by 1Wh, 100Wh and 1kWh.
# These models convert it all to 1kWh increments
PowerUsageList1000Wh = Annotated[list, BeforeValidator(split_data)]
PowerUsageList100Wh = Annotated[
    list, BeforeValidator(lambda v: [x / 10 for x in split_data(v)])
]
PowerUsageList1Wh = Annotated[
    list, BeforeValidator(lambda v: [x / 1000 for x in split_data(v)])
]

PowerUsageSum1000Wh = Annotated[float, BeforeValidator(lambda v: sum(split_data(v)))]
PowerUsageSum100Wh = Annotated[
    float, BeforeValidator(lambda v: sum(split_data(v)) / 10)
]
PowerUsageSum1Wh = Annotated[
    float, BeforeValidator(lambda v: sum(split_data(v)) / 1000)
]

Date = Annotated[
    datetime, BeforeValidator(lambda v: datetime.strptime(v, "%Y/%m/%d %H:%M:%S"))
]
