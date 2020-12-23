from ..utils import run_in_threadpool
from functools import lru_cache

import argon2
import uuid


ph = argon2.PasswordHasher()


class ArgonPasswordHasher:
    algorithm = "argon2"

    async def hash_password(self, password, salt=None):
        if salt is None:
            salt = uuid.uuid4().hex

        if isinstance(salt, str):
            salt = salt.encode("utf-8")

        if isinstance(password, str):
            password = password.encode("utf-8")

        hashed_password = await run_in_threadpool(ph.hash, password + salt)
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
        return await run_in_threadpool(
            self.argon2_password_validator, token, password
        )

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
