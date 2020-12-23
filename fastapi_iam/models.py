from fastapi_asyncpg import sql
from typing import Optional

import asyncpg
import json
import typing
import datetime
import pydantic as pd


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
    refresh_token: str
    refresh_token_expires: datetime.datetime
    token_type: str = "user_token"


async def create_user(settings, db, user):
    hasher = settings["password_hasher"]()
    repo = UserRepository(db, settings["db_schema"])
    user["password"] = await hasher.hash_password(user["password"])
    us = UserCreate(**user)
    return await repo.create(us)


class BaseRepository:
    def __init__(self, db: asyncpg.Connection, schema: str = None):
        self.db = db
        self._schema = schema

    @property
    def schema(self):
        return f"{self._schema}." if self._schema else ""


class UserRepository(BaseRepository):
    async def create(self, user: UserCreate) -> User:
        data = user.dict(exclude_none=True)
        result = await sql.insert(self.db, f"{self.schema}users", data)
        return await self.by_id(result["user_id"])

    async def by_email(
        self, email: str, *, client_id: str = None
    ) -> Optional[User]:
        q = f"{self.base_query()} WHERE email=$1 GROUP BY u.user_id"
        row = await self.db.fetchrow(q, email)
        return self.to_model(row)

    async def by_id(self, user_id: int):
        row = await self.db.fetchrow(
            f"{self.base_query()} WHERE user_id=$1 GROUP BY u.user_id",
            user_id,
        )
        return self.to_model(row)

    def to_model(self, row) -> typing.Optional[User]:
        if not row:
            return None
        return User(**dict(row))

    async def by_token(
        self, *, token: str = None, refresh_token: str = None
    ) -> Optional[User]:
        assert token or refresh_token, "at least one required"
        field = "token" if token else "refresh_token"
        refresh_field = "expires" if token else "refresh_token_expires"
        value = token if token else refresh_token
        row = await self.db.fetchrow(
            f"""
            {self.base_query()}
            LEFT JOIN {self.schema}users_session t using(user_id)
            WHERE {field}=$1 and {refresh_field}>now()
            GROUP BY u.user_id
            """,
            value,
        )
        return self.to_model(row)

    async def update_user(self, data):
        pass

    async def update_groups(self, user: User, groups: list[str]) -> User:
        await self.db.fetch(
            "select FROM update_groups($1, $2)", groups, user.user_id
        )
        return await self.by_id(user.user_id)

    def base_query(self) -> str:
        return f"""
            SELECT
                u.*,
                array_remove(array_agg(g.name), null) as groups
            FROM {self.schema}users u
            LEFT JOIN LATERAL (
                SELECT gg.name from {self.schema}groups gg
                    inner join {self.schema}users_group ug using(group_id)
                    WHERE ug.user_id = u.user_id
            ) g on true
        """


class GroupRepository(BaseRepository):
    async def add_group(self, name):
        return await sql.insert(self.db, f"{self.schema}groups", {"name": name})

    async def get_groups(self):
        return [
            r["name"] for r in await self.db.fetch("SELECT name from groups")
        ]


def unflat(row, *fields):
    res = dict(row)
    for f in fields:
        res[f] = json.loads(res[f])
    return res
