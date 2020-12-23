from fastapi_asyncpg import sql
from fastapi_iam.models import UserRepository
from fastapi_iam.models import GroupRepository
from fastapi_iam import models
import pytest


pytestmark = pytest.mark.asyncio

user1 = models.UserCreate(email="test@test.com", password="test")

groups = ["admin", "staff", "mkt"]
groupsc = ["organitzacio:admin", "organitzacio:staff", "organitzacio:mkt"]


async def testing_works(conn):
    repo = UserRepository(conn)

    org = await repo.create_organization("Organització")
    assert org.pub_id == "organitzacio"

    await repo.create(user1, 1)
    assert await sql.count(conn, "users") == 1
    user = await repo.by_email("test@test.com")
    assert user.password == "test"
    grepo = GroupRepository(conn)
    # add groups to user
    for group in groups:
        await grepo.add_group(group, org.org_id)
    assert await sql.count(conn, "groups") == 3
    assert set(await grepo.get_groups(org.org_id)) == set(groups)

    user = await repo.update_groups(user, [groups[0], groups[1]])
    assert len(user.groups) == 2
    assert set(user.groups) == set(groupsc[:2])
    user = await repo.update_groups(user, groups)
    assert set(user.groups) == set(groupsc)

    user = await repo.update_groups(user, ["xxxxx"])
    assert len(user.groups) == 0
