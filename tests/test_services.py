import pytest

pytestmark = pytest.mark.asyncio


async def test_password_hasher(iam):
    service = iam.get_service("PasswordHasher")
    password = "1qaz2wsx"
    token = await service.hash_password(password)
    check_pass = await service.check_password(token, password)
    assert check_pass is True
