from fastapi_iam import testing

import pytest

pytestmark = pytest.mark.asyncio


async def test_admin_routes(users):
    client, iam = users
    # tc is a customized test client that injects the correct headers
    tc = await testing.login(client, "test@test.com", "asdf")
    res = await tc.get("/auth/whoami")
    assert res.status_code == 200
    assert res.json()["email"] == "test@test.com"

    res = await tc.get("/auth/users")
    assert res.status_code == 403

    logged = await testing.login(client, "admin@test.com", "asdf1")
    res = await logged.get("/auth/users")
    assert res.status_code == 200
    assert res.json()["total"] == 3


async def test_create_user(users):
    client, _ = users
    logged = await testing.login(client, "admin@test.com", "asdf1")
    # create a new user
    new_user = {
        "email": "new@test.com",
        "password": "1234",
        "is_staff": True,
        "is_admin": True,
        "is_active": True,
    }
    resp = await logged.post("/auth/users", json=new_user)
    assert resp.status_code == 201
    res = await logged.get("/auth/users")
    assert res.json()["total"] == 4

    new_ = await testing.login(client, "new@test.com", "1234")
    resp = await new_.get("/auth/users")
    assert resp.json()["total"] == 4

    inactive = new_user.copy()
    inactive.update({"is_active": False, "email": "new2@test.com"})
    resp = await logged.post("/auth/users", json=inactive)
    res = await logged.get("/auth/users?is_active=false")
    assert res.json()["total"] == 2


async def test_create_group(users):
    client, _ = users
    logged = await testing.login(client, "admin@test.com", "asdf1")
    res = await logged.post("/auth/groups", json={"name": "group1"})
    assert res.status_code == 201

    res = await logged.get("/auth/groups")
    assert res.json() == ["group1"]
