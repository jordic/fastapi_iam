from fastapi_iam.auth.policy import JWTSecurityPolicy
from fastapi_iam.auth.policy import InvalidRefreshToken
from fastapi_iam import models

import pytest
import jwt

pytestmark = pytest.mark.asyncio


def test_signed_refresh_token():
    class FakeIAM:
        def __init__(self, settings):
            self.settings = settings

    settings = {"session_expiration": 1, "refresh_token_secret_key": "xxxxx"}

    user = models.User(
        **{
            "user_id": 12,
            "email": "test@test.com",
            "username": "noname",
            "password": "asdf",
            "is_active": True,
            "is_staff": True,
            "is_admin": False,
        }
    )

    security = JWTSecurityPolicy(FakeIAM(settings))

    token, _ = security.create_refresh_token(user)
    assert token is not None
    valid = security.validate_refresh_token(token)
    assert valid == 12

    # expire
    settings = {"session_expiration": -1, "refresh_token_secret_key": "xxxxx"}
    security = JWTSecurityPolicy(FakeIAM(settings))
    token, _ = security.create_refresh_token(user)
    assert token is not None
    with pytest.raises(InvalidRefreshToken):
        valid = security.validate_refresh_token(token)

    # invalid
    with pytest.raises(InvalidRefreshToken):
        security.validate_refresh_token("asdfas.dfasdf")


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


async def test_JWTSecurityPolicy(users):
    client, iam = users
    iam.security_policy = JWTSecurityPolicy
    res = await client.post(
        "/auth/login",
        form={"username": "test@test.com", "password": "asdf"},
    )
    assert res.status_code == 200
    assert "access_token" in res.json()
    token = res.json()["access_token"]
    # ensure token is decodificable
    _ = jwt.decode(
        token,
        iam.settings["jwt_secret_key"],
        algorithms=iam.settings["jwt_algorithm"],
    )
    # no session persisted on the db
    async with iam.pool.acquire() as db:
        sess_num = await db.fetchval("SELECT count(*) from users_session")
    assert sess_num == 0

    # test refresh token
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
