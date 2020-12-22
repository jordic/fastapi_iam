from __future__ import annotations

import datetime
import pydantic as pd
import typing


class User(pd.BaseModel):
    user_id: int
    password: str
    username: str
    email: str
    is_staff: bool
    is_active: bool
    is_admin: bool
    date_joined: datetime.datetime
    last_login: typing.Optional[datetime.datetime]
    groups: typing.List[str] = []
    props: pd.Json


class UserCreate(pd.BaseModel):
    email: str
    username: str = "noname"
    password: typing.Optional[str]
    is_staff: typing.Optional[bool]
    is_active: typing.Optional[bool]
    is_admin: typing.Optional[bool]


class AuthTicket(pd.BaseModel):
    user_id: int
    token: str
    expires: datetime.datetime
    resfresh_token: str
    refresh_token_expires: datetime.datetime
    token_type: str = "user_token"
