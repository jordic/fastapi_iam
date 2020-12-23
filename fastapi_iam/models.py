from fastapi_asyncpg import sql
from slugify import slugify
from typing import Optional

import asyncpg
import json
import typing
import datetime
import pydantic as pd


class Organization(pd.BaseModel):
    org_id: int
    pub_id: str
    name: str


class PublicUser(pd.BaseModel):
    user_id: int
    username: str
    email: str
    is_staff: bool
    is_active: bool
    is_admin: bool
    is_orgs_admin: typing.Optional[bool] = False
    date_joined: typing.Optional[datetime.datetime]
    last_login: typing.Optional[datetime.datetime]
    groups: typing.List[str] = []
    org: typing.Optional[Organization]


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
    user_id=0,
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
            principals.append("org:admin")
        if self.is_orgs_admin:
            principals.append("root")
        return principals

    def get_jwt_claims(self):
        return {
            "email": self.email,
            "email_verified": True,
            "principals": self.get_principals(),
            "org": self.org.dict(),
            "is_admin": self.is_admin,
            "is_orgs_admin": self.is_orgs_admin,
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


async def create_org(settings, db, name):
    repo = UserRepository(db, settings["db_schema"])
    return await repo.create_organization(name)


async def create_user(settings, db, user, org_id):
    hasher = settings["password_hasher"]()
    repo = UserRepository(db, settings["db_schema"])
    user["password"] = await hasher.hash_password(user["password"])
    us = UserCreate(**user)
    return await repo.create(us, org_id)


class BaseRepository:
    def __init__(self, db: asyncpg.Connection, schema: str = None):
        self.db = db
        self._schema = schema

    @property
    def schema(self):
        return f"{self._schema}." if self._schema else ""


class UserRepository(BaseRepository):
    async def create_organization(self, name):
        result = await sql.insert(
            self.db,
            f"{self.schema}organization",
            {"name": name, "pub_id": slugify(name)},
        )
        return Organization(**dict(result))

    async def create(self, user: UserCreate, org_id: int) -> User:
        data = user.dict(exclude_none=True)
        data.update({"org_id": org_id})
        result = await sql.insert(self.db, f"{self.schema}users", data)
        return await self.by_id(result["user_id"])

    async def by_email(self, email: str) -> Optional[User]:
        q = f"{self.base_query()} WHERE email=$1 GROUP BY u.user_id, o.org_id"
        row = await self.db.fetchrow(q, email)
        return self.to_model(row)

    async def by_id(self, user_id: int):
        row = await self.db.fetchrow(
            f"{self.base_query()} WHERE user_id=$1 GROUP BY u.user_id, o.org_id",
            user_id,
        )
        return self.to_model(row)

    def to_model(self, row) -> typing.Optional[User]:
        if not row:
            return None
        return User(**unflat(row, "org"))

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
            GROUP BY u.user_id, o.org_id
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
                json_build_object(
                    'org_id', o.org_id,
                    'pub_id', o.pub_id,
                    'name', o.name
                ) as org,
                array_remove(array_agg(o.pub_id || ':' || g.name), null) as groups
            FROM {self.schema}users u
            LEFT JOIN organization o using(org_id)
            LEFT JOIN LATERAL (
                SELECT gg.name from {self.schema}groups gg
                    inner join {self.schema}users_group ug using(group_id)
                    WHERE ug.user_id = u.user_id and gg.org_id = u.org_id
            ) g on true
        """


class GroupRepository(BaseRepository):
    async def add_group(self, name, org_id):
        return await sql.insert(
            self.db, f"{self.schema}groups", {"name": name, "org_id": org_id}
        )

    async def get_groups(self, org_id):
        return [
            r["name"]
            for r in await self.db.fetch(
                "SELECT name from groups where org_id=$1", org_id
            )
        ]


def unflat(row, *fields):
    res = dict(row)
    for f in fields:
        res[f] = json.loads(res[f])
    return res
