from typing import List, Optional, Union

from pydantic import BaseModel, model_validator
from pydantic.fields import FieldInfo


class Md(BaseModel):
    pt: str
    st: Optional[int] = None
    mi: Optional[str] = None
    mx: Optional[str] = None


class ItemWithValue(BaseModel):
    pn: str
    pt: int
    pv: Optional[int | str] = None
    md: Md


class Pc(BaseModel):
    pn: str
    pt: int
    pch: List[Union["Pc", ItemWithValue]]

    @model_validator(mode="before")
    def to_dict(self):
        for x in self['pch']:
            if "pv" in x:
                newfield = FieldInfo(annotation=str, required=False)
                self.model_fields[x['pn']] = newfield
                self.__annotations__[x['pn']] = newfield
                setattr(self, x['pn'], x['pv'])
            else:
                newfield = FieldInfo(annotation=List[Pc], required=False)
                self.model_fields[x['pn']] = newfield
                self.__annotations__[x['pn']] = newfield
                setattr(self, x['pn'], x['pch'])


class Response(BaseModel):
    fr: str
    pc: Pc
    rsc: int


class BRP084cxxV28Response(BaseModel):
    responses: List[Response]
