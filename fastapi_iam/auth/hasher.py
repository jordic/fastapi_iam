from ..utils import run_in_threadpool
from functools import lru_cache

import argon2

ph = argon2.PasswordHasher()


class ArgonPasswordHasher:
    algorithm = "argon2"

    async def hash_password(self, password):
        if isinstance(password, str):
            password = password.encode("utf-8")

        hashed_password = await run_in_threadpool(ph.hash, password)
        return hashed_password

    @lru_cache(100)
    async def check_password(self, token, password) -> bool:
        return await run_in_threadpool(
            self.argon2_password_validator, token, password
        )

    def argon2_password_validator(self, token, password):
        try:
            return ph.verify(token, password)
        except (
            argon2.exceptions.InvalidHash,
            argon2.exceptions.VerifyMismatchError,
        ):
            return False
