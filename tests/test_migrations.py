import pytest

pytestmark = pytest.mark.asyncio


async def testing_migrations(conn):
    val = await conn.fetchval("SELECT value from users_version")
    assert val == 1
