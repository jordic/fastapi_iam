from .base import BaseRepository
from fastapi_asyncpg import sql

import uuid


class TokenStorage(BaseRepository):
    def create_token(self):
        return uuid.uuid4().hex

    async def create_token_verification(self, user):
        _ = self.create_token()

    async def store(self, token):
        return await sql.insert(self.db, f"{self.schema}users_token")
