from fastapi_asyncpg import sql
from fastapi_iam.respository import UserRepository
from fastapi_iam.respository import GroupRepository
from fastapi_iam import models
from fastapi_iam.respository import AuthTicketRepository
import pytest


pytestmark = pytest.mark.asyncio

user1 = models.UserCreate(email="test@test.com", password="test")

groups = ["group:admin", "group:staff", "group:mkt"]


async def testing_works(conn):
    repo = UserRepository(conn)
    await repo.create(user1)
    assert await sql.count(conn, "users") == 1
    user = await repo.by_email("test@test.com")
    assert user.password == "test"

    grepo = GroupRepository(conn)
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
