from ... import models
from .base import BaseRepository
from fastapi_asyncpg import sql

import datetime


class SessionStorage(BaseRepository):
    async def create(self, us: models.UserSession):
        result = await sql.insert(
            self.db,
            f"{self.schema}users_session",
            us.dict(),
        )
        return models.UserSession(**dict(result))

    async def is_expired(self, refresh_token: str) -> bool:
        expiration = await self.db.fetchval(
            f"""
            SELECT refresh_token_expires
                FROM {self.schema}users_session
            WHERE refresh_token=$1
        """,
            refresh_token,
        )
        return expiration < datetime.datetime.utcnow()

    async def delete(self, token):
        await sql.delete(
            self.db,
            f"{self.schema}users_session",
            "token=$1",
            args=[token],
        )

    async def update_token(
        self,
        refresh_token: str,
        token: str,
        expires: datetime.datetime,
        *,
        new_rt: str = None,  # set it to rotate the refresh token
        new_rte: str = None,
    ):
        extra = ""
        args = [token, expires, refresh_token]
        if new_rt:
            assert (
                new_rt and new_rte
            ), "new_token and new_token_expiration required"
            extra = ", refresh_token=$4, refresh_token_expires=$5"
            args = args + [new_rt, new_rte]

        await self.db.execute(
            f"""
            UPDATE {self.schema}users_session
                set token=$1, expires=$2 {extra}
            WHERE refresh_token=$3
        """,
            *args,
        )
