from __future__ import annotations

from functools import lru_cache
from functools import partial
from . import models

import asyncio
import concurrent.futures
import uuid
import datetime

import argon2
import jwt

ph = argon2.PasswordHasher()


class _base_service:
    pass


class AuthService(_base_service):
    async def authenticated_userid(request):
        pass

    async def permits(request, context, permission):
        pass

    async def remember(request, userid, **kw):
        pass

    async def forget(request, **kw):
        pass


class PasswordHasher(_base_service):
    algorithm = "argon2"

    async def hash_password(self, password, salt=None):
        if salt is None:
            salt = uuid.uuid4().hex

        if isinstance(salt, str):
            salt = salt.encode("utf-8")

        if isinstance(password, str):
            password = password.encode("utf-8")

        to_hash = partial(ph.hash, password + salt)
        hashed_password = await self.run_in_thread_pool(to_hash)
        return "{}:{}:{}".format(
            self.algorithm, salt.decode("utf-8"), hashed_password
        )

    @lru_cache(1000)
    async def check_password(self, token, password) -> bool:
        split = token.split(":")
        if len(split) != 3:
            return False
        algorithm = split[0]
        assert self.algorithm == algorithm, "hasher not available"
        to_validate = partial(self.argon2_password_validator, token, password)
        return await self.run_in_thread_pool(to_validate)

    async def run_in_thread_pool(self, func):
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(pool, func)

    def argon2_password_validator(self, token, password):
        split = token.split(":")
        if len(split) != 3:
            return False
        salt = split[1]
        hashed = split[2]
        try:
            return ph.verify(hashed, password + salt)
        except (
            argon2.exceptions.InvalidHash,
            argon2.exceptions.VerifyMismatchError,
        ):
            return False


class JWTService(_base_service):
    def create_access_token(self, iam, user: models.User):
        settings = iam.settings
        expiration = settings["jwt_expiration"]
        to_encode = {"sub": user.email}
        expire = datetime.utcnow() + datetime.timedelta(seconds=expiration)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            settings["jwt_secret_key"],
            algorithm=settings["jwt_algorithm"],
        )
        return encoded_jwt, expire
