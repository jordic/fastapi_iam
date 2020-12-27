from fastapi_asyncpg import sql
from fastapi_iam.services.pg import UserStorage
from fastapi_iam.services.pg import GroupStorage
from fastapi_iam import models
import pytest


pytestmark = pytest.mark.asyncio

user1 = models.UserCreate(email="test@test.com", password="test")

groups = ["admin", "staff", "mkt"]


async def test_base_model_service_storage(conn):
    repo = UserStorage(conn)

    await repo.create(user1)
    assert await sql.count(conn, "users") == 1
    user = await repo.by_email("test@test.com")
    assert user.password == "test"
    grepo = GroupStorage(conn)
    # add groups to user
    for group in groups:
        await grepo.add_group(group)
    assert await sql.count(conn, "groups") == 3
    assert set(await grepo.get_groups()) == set(groups)

    user = await repo.update_groups(user, [groups[0], groups[1]])
    assert len(user.groups) == 2
    assert set(user.groups) == set(groups[:2])
    user = await repo.update_groups(user, groups)
    assert set(user.groups) == set(groups)

    user = await repo.update_groups(user, ["xxxxx"])
    assert len(user.groups) == 0
