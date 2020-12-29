import pytest
from fastapi_iam import auth

pytestmark = pytest.mark.asyncio


async def test_password_argon_hasher():
    service = auth.ArgonPasswordHasher()
    password = "1qaz2wsx"
    token = await service.hash_password(password)
    check_pass = await service.check_password(token, password)
    assert check_pass is True
