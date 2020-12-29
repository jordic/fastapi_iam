import pytest
import jwt


pytestmark = pytest.mark.asyncio


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


async def test_login(users):
    client, ins = users
    res = await client.post(
        "/auth/login",
        form={"username": "test@test.com", "password": "asdf"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
    token = res.json()["access_token"]

    # ensure token is decodificable
    validated = jwt.decode(
        token,
        ins.settings["jwt_secret_key"],
        algorithms=ins.settings["jwt_algorithm"],
    )

    assert validated["email"] == "test@test.com"
    assert "staff" in validated["principals"]
    assert validated["is_admin"] is False

    assert "refresh" in res.cookies
    # todo: verify cookie max-age, domain, httponly
    res = await client.post(
        "/auth/login", form={"username": "invalid", "password": "asdf"}
    )
    assert res.status_code == 400

    res = await client.get("/auth/whoami")
    assert res.status_code == 200
    assert res.json()["username"] == "anonymous"

    res = await client.get("/auth/whoami", headers=auth_header(token))
    assert res.status_code == 200
    user = res.json()
    assert user["email"] == "test@test.com"
    assert "password" not in user
    assert user["is_admin"] is False

    # ensure we can logout
    res = await client.get("/auth/logout", headers=auth_header(token))
    assert res.status_code == 200

    res = await client.get("/auth/whoami", headers=auth_header(token))
    assert res.status_code == 403
    # TODO check cookie logout is present

    # we don't fail if there's no cookie
    res = await client.post("/auth/logout")


async def test_invalid_token(users):
    client, _ = users
    res = await client.get(
        "/auth/whoami", headers={"Authorization": "Bearer XXX"}
    )
    assert res.status_code == 403


async def test_disable_user(users):
    client, iam = users
    res = await client.post(
        "/auth/login",
        form={"username": "test@test.com", "password": "asdf"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
    token = res.json()["access_token"]

    res = await client.get("/auth/whoami", headers=auth_header(token))
    assert res.status_code == 200

    user_id = res.json()["user_id"]
    async with iam.pool.acquire() as db:
        await db.execute(
            "update users set is_active=false where user_id=$1", user_id
        )

    res = await client.post(
        "/auth/login",
        form={"username": "test@test.com", "password": "asdf"},
    )
    assert res.status_code == 412


async def test_refresh_token(users):
    client, iam = users
    # change expiration time to be negative
    iam.settings["jwt_expiration"] = -60
    res = await client.post(
        "/auth/login",
        form={"username": "test@test.com", "password": "asdf"},
    )
    assert res.status_code == 200
    access_token = res.json()["access_token"]
    try:
        _ = jwt.decode(
            access_token,
            iam.settings["jwt_secret_key"],
            algorithms=iam.settings["jwt_algorithm"],
        )
    except jwt.exceptions.ExpiredSignatureError:
        pass

    # keep the refresh cookie for later use
    refresh_token = res.cookies["refresh"]

    # we are not authenticated
    res = await client.get("/auth/whoami", headers=auth_header(access_token))
    assert res.status_code == 403

    headers = {"refresh": f"{refresh_token}"}
    iam.settings["jwt_expiration"] = 60 * 60 * 24

    renew = await client.post("/auth/renew", cookies=headers)
    assert renew.status_code == 200
    nt = renew.json()["access_token"]
    res = await client.get("/auth/whoami", headers=auth_header(nt))
    assert res.status_code == 200
