from .base import BaseRepository
from fastapi_asyncpg import sql


class GroupStorage(BaseRepository):
    async def add_group(self, name):
        return await sql.insert(self.db, f"{self.schema}groups", {"name": name})

    async def get_groups(self):
        return [
            r["name"] for r in await self.db.fetch("SELECT name from groups")
        ]
