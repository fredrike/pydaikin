from typing import List, Optional, Union

from pydantic import BaseModel, Field


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
    pch: List[Union["Pc", ItemWithValue]] = Field()


class Response(BaseModel):
    fr: str
    pc: Pc
    rsc: int


class BRP084cxxV28Response(BaseModel):
    responses: List[Response]
