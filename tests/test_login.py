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
    assert "user:1" in validated["principals"]
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
