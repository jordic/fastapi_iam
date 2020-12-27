import asyncpg


class BaseRepository:
    def __init__(self, db: asyncpg.Connection, schema: str = None):
        self.db = db
        self._schema = schema

    @property
    def schema(self):
        return f"{self._schema}." if self._schema else ""
