from ..interfaces import IUsersStorage
from typing import Optional

import datetime
import pydantic as pd
import typing


class PublicUser(pd.BaseModel):
    user_id: typing.Optional[int]
    username: str
    email: str
    is_staff: bool
    is_active: bool
    is_admin: bool
    date_joined: typing.Optional[datetime.datetime]
    last_login: typing.Optional[datetime.datetime]
    groups: typing.List[str] = []


root_user = PublicUser(
    user_id=0,
    username="root",
    email="root",
    is_staff=True,
    is_admin=True,
    is_orgs_admin=True,
    is_active=True,
    groups=["root"],
)

anonymous_user = PublicUser(
    user_id=None,
    username="anonymous",
    email="anonymous",
    is_staff=False,
    is_admin=False,
    is_orgs_admin=False,
    is_active=True,
    groups=[],
)


class User(PublicUser):
    password: str
    token: Optional[str]  # used to carry current auth token

    def get_principals(self):
        principals = self.groups[:]
        principals.append(f"user:{self.user_id}")
        if self.is_staff:
            principals.append("staff")
        if self.is_admin:
            principals.append("admin")
        return principals

    def get_jwt_claims(self):
        return {
            "email": self.email,
            "email_verified": True,
            "principals": self.get_principals(),
            "is_admin": self.is_admin,
        }


class UserCreate(pd.BaseModel):
    email: str
    username: str = "noname"
    password: typing.Optional[str]
    is_staff: typing.Optional[bool]
    is_active: typing.Optional[bool]
    is_admin: typing.Optional[bool]


class UserSession(pd.BaseModel):
    user_id: int
    token: str
    expires: datetime.datetime
    refresh_token: typing.Optional[str]
    refresh_token_expires: typing.Optional[datetime.datetime]
    data: typing.Optional[pd.Json]


async def create_user(iam, user):
    settings = iam.settings
    hasher = settings["password_hasher"]()
    repo = iam.get_service(IUsersStorage)
    user["password"] = await hasher.hash_password(user["password"])
    us = UserCreate(**user)
    return await repo.create(us)
