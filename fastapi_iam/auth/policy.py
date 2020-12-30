from .. import models
from ..interfaces import ISessionStorage
from ..interfaces import IUsersStorage
from .encoders import InvalidToken
from .encoders import JWTToken
from .extractors import BearerAuthPolicy
from .hasher import ArgonPasswordHasher
from fastapi.exceptions import HTTPException
from random import randint

import asyncio
import datetime
import typing

InvalidUser = HTTPException(status_code=403, detail="invalid_user")
ExpiredToken = HTTPException(status_code=417, detail="invalid_user")
InactiveUser = HTTPException(status_code=412, detail="inactive_user")

NO_CACHE = {"cache-control": "no-store", "pargma": "no-cache"}


async def invalid_user():
    await asyncio.sleep(randint(10, 200) / 1000)
    raise HTTPException(
        status_code=400, detail="Incorrect username or password"
    )


class PersistentSecurityPolicy:
    """
    A Security policy that stores tokens on the storage
    Token validation is done querying the existence of the token on the db
    Tokens could be invalidated removing it from the storage
    A refresh cookie is emmited that allows to refresh the token after expiration
      cookie refresh expiration is also configurable
    refresh_token rotation could also be configured from main settings
    """

    cookie_name = "refresh"
    hasher: ArgonPasswordHasher = ArgonPasswordHasher()
    extractors = [BearerAuthPolicy]
    encoder = JWTToken

    def __init__(self, iam):
        self.iam = iam

    async def login(
        self, username, password, request=None
    ) -> typing.Tuple[models.PublicUser, models.UserSession]:
        user_service = self.iam.get_service(IUsersStorage)
        user = await user_service.by_email(username)
        if not user:
            return await invalid_user()

        if user.is_active is False:
            raise InactiveUser

        valid = await self.hasher.check_password(user.password, password)
        if valid is False:
            return await invalid_user()

        user_session = await self.create_session(user)
        await user_service.update_user(
            user.user_id, {"last_login": datetime.datetime.utcnow()}
        )
        return user, user_session

    async def create_session(self, user) -> models.UserSession:
        """
        creates a sesssion, makes a token, and stores on the db.
        Also fabricates a token to be usable on the refreshtoken endpoint
        """
        encoder = self.encoder(self.cfg)
        token, expire = await encoder.create_access_token(user)
        refresh_token, refresh_expiration = encoder.create_refresh_token()
        us = models.UserSession(
            user_id=user.user_id,
            token=token,
            expires=expire,
            refresh_token=refresh_token,
            refresh_token_expires=refresh_expiration,
        )
        session_service = self.iam.get_service(ISessionStorage)
        await session_service.create(us)
        return us

    @property
    def schema(self):
        db_schema = self.iam.settings["db_schema"]
        return f"{db_schema}." if db_schema != "" else ""

    @property
    def cfg(self):
        return self.iam.settings

    async def validate(self, token) -> models.User:
        encoder = self.encoder(self.cfg)
        # decode token
        try:
            await encoder.validate(token.get("token"))
        except InvalidToken:
            raise InvalidUser

        user_service = self.iam.get_service(IUsersStorage)
        user = await user_service.by_token(token=token.get("token"))
        if user is None:
            raise InvalidUser
        return user

    async def refresh(self, token) -> models.UserSession:
        """creates a new access_token and updates it on the storage.
        Optionaly rotates the refresh_token. If refresh_token rotation
        enabled, we must be extra careful, because other authenticated
        devices will not be able to login again after it
        iam.get_repository(name, *args)
        """
        sess_repo = self.iam.get_service(ISessionStorage)
        users_repo = self.iam.get_service(IUsersStorage)
        user = await users_repo.by_token(refresh_token=token)
        expired = await sess_repo.is_expired(token)

        if expired is True:
            raise ExpiredToken

        if user is None:
            raise InvalidUser

        encoder = self.encoder(self.cfg)

        # handle refresh token rotation
        kwargs = {}
        rt = rte = None
        if self.cfg["rotate_refresh_tokens"] is True:
            rt, rte = encoder.create_refresh_token()
            kwargs = {"new_rt": rt, "new_rte": rte}

        new_token, new_expire = await encoder.create_access_token(user)
        # update storage token
        await sess_repo.update_token(token, new_token, new_expire, **kwargs)
        return models.UserSession(
            user_id=user.user_id,
            token=new_token,
            expires=new_expire,
            refresh_token=rt,
            refresh_token_expires=rte,
        )

    async def forget(self, user, response):
        sess_repo = self.iam.get_service(ISessionStorage)
        await sess_repo.delete(user.token)
        # cleanup cookie
        response.delete_cookie(
            self.cookie_name, path="/", domain=self.cfg["cookie_domain"]
        )

    async def remember(self, user_session, response, request=None):
        max_age = self.cfg["session_expiration"]
        domain = self.cfg["cookie_domain"] or (
            request.headers["host"].split(":")[0] if request else "localhost"
        )
        response.set_cookie(
            self.cookie_name,
            user_session.refresh_token,
            path="/",
            secure=False,
            httponly=True,
            samesite="lax",
            max_age=max_age,
            domain=domain,
        )


class JWTSecurityPolicy(PersistentSecurityPolicy):
    """ A security policy that DOES NOT store sessions on storage """

    async def create_session(self, user):
        encoder = self.encoder(self.cfg)
        token, expire = await encoder.create_access_token(user)
        refresh_token, refresh_expiration = encoder.create_refresh_token()
        us = models.UserSession(
            user_id=user.user_id,
            token=token,
            expires=expire,
            refresh_token=refresh_token,
            refresh_token_expires=refresh_expiration,
        )
        return us

    async def validate(self, token):
        encoder = self.encoder(self.cfg)
        # decode token
        try:
            result = await encoder.validate(token.get("token"))
        except InvalidToken:
            raise InvalidUser

        user_service = self.iam.get_service(IUsersStorage)
        user = await user_service.by_id(result["sub"])
        if user is None:
            raise InvalidUser
        return user
