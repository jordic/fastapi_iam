from ... import models
from .base import BaseRepository
from fastapi_asyncpg import sql
from typing import Optional

import typing


class UserStorage(BaseRepository):
    async def create(self, user: models.UserCreate) -> models.User:
        data = user.dict(exclude_none=True)
        result = await sql.insert(self.db, f"{self.schema}users", data)
        return await self.by_id(result["user_id"])

    async def by_email(self, email: str) -> Optional[models.User]:
        q = f"{self.base_query()} WHERE email=$1 GROUP BY u.user_id"
        row = await self.db.fetchrow(q, email)
        return self.to_model(row)

    async def by_id(self, user_id: int):
        row = await self.db.fetchrow(
            f"{self.base_query()} WHERE user_id=$1 GROUP BY u.user_id",
            user_id,
        )
        return self.to_model(row)

    def to_model(self, row) -> Optional[models.User]:
        if not row:
            return None
        return models.User(**dict(row))

    async def by_token(
        self, *, token: str = None, refresh_token: str = None
    ) -> Optional[models.User]:
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

    async def search(
        self,
        *,
        q=None,
        page=0,
        limit=100,
        is_staff=None,
        is_active=None,
        is_admin=None,
    ):
        conds = []
        args = []
        if q:
            conds.append("u.email ilike $1")
            args.append(q)
        if is_staff is not None:
            conds.append(f"u.is_staff = {to_str(is_staff)}")
        if is_active is not None:
            conds.append(f"u.is_active = {to_str(is_active)}")
        if is_admin is not None:
            conds.append(f"u.is_admin = {to_str(is_admin)}")

        qs = f"""
            {self.base_query()}
            {'WHERE ' + ' AND '.join(conds) if len(conds) > 0 else ''}
            GROUP BY u.user_id
        """
        pag = f"LIMIT {limit} OFFSET {page*limit}"
        total = await self.db.fetchval(
            f"""SELECT count(*) FROM (
                {qs}
            ) as foo""",
            *args,
        )
        results = await self.db.fetch(
            f"""
            {qs} {pag}
        """,
            *args,
        )
        return {
            "total": total,
            "page": page,
            "limit": limit,
            "items": [self.to_model(res) for res in results],
        }

    async def update_user(self, user_id: int, data):
        pass

    async def update_groups(
        self, user: models.User, groups: typing.List[str]
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


def to_str(item: bool):
    if item is True:
        return "true"
    return "false"
