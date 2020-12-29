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


async def test_users_search(users):
    _, ins = users
    storage = UserStorage(ins.pool)
    result = await storage.search()
    assert result["total"] == 3
    emails = set([r.email for r in result["items"]])
    assert emails == {"test@test.com", "admin@test.com", "inactive@test.com"}

    result = await storage.search(q="test%")
    assert result["total"] == 1
    assert result["items"][0].email == "test@test.com"

    result = await storage.search(is_active=False)
    assert result["total"] == 1
    assert result["items"][0].email == "inactive@test.com"

    result = await storage.search(is_admin=True, is_active=True)
    assert result["total"] == 1
    assert result["items"][0].email == "admin@test.com"

    result = await storage.search(is_staff=True)
    assert result["total"] == 3
