from ..interfaces import IUsersStorage
from typing import Optional

import datetime
import pydantic as pd
import typing


class BaseUser(pd.BaseModel):
    username: str
    email: str
    is_staff: bool
    is_active: bool
    is_admin: bool
    date_joined: typing.Optional[datetime.datetime]
    last_login: typing.Optional[datetime.datetime]
    groups: typing.List[str] = []


class PublicUser(BaseUser):
    user_id: typing.Optional[int]


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


class User(BaseUser):
    user_id: int
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


class UserUpdate(pd.BaseModel):
    email: Optional[str]
    username: Optional[str]
    groups: Optional[typing.List[str]]
    props: Optional[typing.Dict[str, typing.Any]]
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


class Group(pd.BaseModel):
    name: str


async def create_user(iam, user):
    if isinstance(user, dict):
        user = UserCreate(**user)
    security_policy = iam.get_security_policy()
    hasher = security_policy.hasher
    repo = iam.get_service(IUsersStorage)
    user.password = await hasher.hash_password(user.password)
    return await repo.create(user)
