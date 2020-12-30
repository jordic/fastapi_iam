from .. import models

import datetime
import jwt
import time
import typing
import uuid


class ITokenEncoder(typing.Protocol):
    cfg: typing.Dict[str, typing.Any]

    async def create_access_token(
        self, user: models.User
    ) -> typing.Tuple[str, datetime.datetime]:
        pass

    async def validate(self, token: str):
        pass

    def create_refresh_token(self) -> typing.Tuple[str, datetime.datetime]:
        pass


class InvalidToken(Exception):
    pass


class JWTToken(ITokenEncoder):
    def __init__(self, cfg):
        self.cfg = cfg

    async def create_access_token(
        self, user: models.User
    ) -> typing.Tuple[str, datetime.datetime]:
        expiration = self.cfg["jwt_expiration"]
        to_encode = {"sub": user.user_id}
        # TODO: add func to be able to customize how claims are processed
        to_encode.update(user.get_jwt_claims())
        expire = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=expiration
        )
        expire_unixts = int(time.mktime(expire.timetuple()))
        to_encode.update({"exp": expire_unixts})
        encoded_jwt = jwt.encode(
            to_encode,
            self.cfg["jwt_secret_key"],
            algorithm=self.cfg["jwt_algorithm"],
        )
        # jwt types say that is returning bytes, but really is returning a str
        # mypy complains about
        if isinstance(encoded_jwt, bytes):
            encoded_jwt = encoded_jwt.decode("utf-8")
        return encoded_jwt, expire

    async def validate(self, token: str) -> typing.Dict[str, typing.Any]:
        try:
            result = jwt.decode(
                token,
                self.cfg["jwt_secret_key"],
                algorithms=self.cfg["jwt_algorithm"],
            )
        except (
            jwt.DecodeError,
            jwt.ExpiredSignatureError,
        ):
            raise InvalidToken()
        return result

    def create_refresh_token(self) -> typing.Tuple[str, datetime.datetime]:
        rt = uuid.uuid4().hex
        rte = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=self.cfg["session_expiration"]
        )
        return rt, rte
