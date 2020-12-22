from . import models
from fastapi_asyncpg import sql
from typing import Optional

import asyncpg
import typing


class BaseRepository:
    def __init__(self, db: asyncpg.Connection, *, schema: str = None):
        self.db = db
        self._schema = schema

    @property
    def schema(self):
        return f"{self._schema}." if self._schema else ""


class UserRepository(BaseRepository):
    async def create(self, user: models.UserCreate) -> models.User:
        result = await sql.insert(
            self.db, f"{self.schema}users", user.dict(exclude_none=True)
        )
        return await self.by_id(result["user_id"])

    async def by_email(self, email: str) -> Optional[models.User]:
        q = f"{self.base_query()} WHERE email=$1 GROUP BY u.user_id"
        row = await self.db.fetchrow(q, email)
        return models.User(**dict(row))

    async def by_id(self, user_id: int):
        row = await self.db.fetchrow(
            f"{self.base_query()} WHERE user_id=$1 GROUP BY u.user_id", user_id
        )
        return models.User(**dict(row))

    async def by_ticket(
        self, *, token: str = None, refresh_token: str = None
    ) -> Optional[models.User]:
        assert token or refresh_token, "at least one required"
        field = "token" if token else "refresh_token"
        refresh_field = "expires" if token else "refresh_token_expires"
        value = token if token else refresh_token
        row = await self.db.fetchrow(
            f"""
            {self.base_query()}
            LEFT JOIN {self.schema}user_tickets t using(user_id)
            WHERE {field}=$1 and {refresh_field}>now()
            GROUP BY u.user_id
            """,
            value,
        )
        return models.User(**dict(row))

    async def update_user(self, data):
        pass

    async def update_groups(
        self, user: models.User, groups: list[str]
    ) -> models.User:
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


class AuthTicketRepository(BaseRepository):
    async def store_ticket(self, ticket: models.AuthTicket):
        return await sql.insert(self.db, self.table, ticket.dict())

    async def expire_ticket(self, token: str):
        await sql.delete(self.db, self.table, "token = $1", token)

    async def update_ticket(
        self, ticket: models.AuthTicket, data: dict[str, typing.Any]
    ):
        await sql.update(self.db, self.table, {"token": ticket.token}, data)

    @property
    def table(self):
        return f"{self.schema}users_authticket"
