from .. import models
from ..interfaces import ISecurityPolicy
from ..interfaces import ISessionStorage
from ..interfaces import IUsersStorage
from .extractors import BearerAuthPolicy
from .hasher import ArgonPasswordHasher
from fastapi.exceptions import HTTPException
from random import randint

import asyncio
import datetime
import jwt
import typing
import uuid

InvalidUser = HTTPException(status_code=403, detail="invalid_user")
ExpiredToken = HTTPException(status_code=417, detail="invalid_user")
InactiveUser = HTTPException(status_code=412, detail="inactive_user")

NO_CACHE = {"cache-control": "no-store", "pargma": "no-cache"}


async def invalid_user():
    await asyncio.sleep(randint(10, 200) / 1000)
    raise HTTPException(
        status_code=400, detail="Incorrect username or password"
    )


class PersistentSecurityPolicy(ISecurityPolicy):

    cookie_name = "refresh"
    hasher: ArgonPasswordHasher = ArgonPasswordHasher()
    extractors = [BearerAuthPolicy]

    def __init__(self, iam):
        """Every session data manager receives an instance of the iam
        preconfigured app. This way, you can wire dependencies from the
        instantiation, and use the iam instance (singleton) as a
        poor man registry
        """
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
        token, expire = await self.create_access_token(user)
        refresh_token, refresh_expiration = self.get_new_refresh_token()
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

    def get_new_refresh_token(self):
        rt = uuid.uuid4().hex
        rte = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=self.cfg["session_expiration"]
        )
        return rt, rte

    @property
    def schema(self):
        db_schema = self.iam.settings["db_schema"]
        return f"{db_schema}." if db_schema != "" else ""

    @property
    def cfg(self):
        return self.iam.settings

    async def validate(self, token) -> models.User:
        # decode token
        try:
            _ = jwt.decode(
                token.get("token"),
                self.iam.settings["jwt_secret_key"],
                algorithms=self.iam.settings["jwt_algorithm"],
            )
        except (
            jwt.exceptions.DecodeError,
            jwt.exceptions.ExpiredSignatureError,
        ):
            raise InvalidUser

        user_service = self.iam.get_service(IUsersStorage)
        user = await user_service.by_token(token=token.get("token"))
        if user is None:
            raise InvalidUser
        return user

    async def create_access_token(self, user: models.User):
        expiration = self.cfg["jwt_expiration"]
        to_encode = {"sub": user.user_id}
        to_encode.update(user.get_jwt_claims())
        expire = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=expiration
        )
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode,
            self.cfg["jwt_secret_key"],
            algorithm=self.cfg["jwt_algorithm"],
        )
        return encoded_jwt.decode("utf-8"), expire

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

        # handle refresh token rotation
        kwargs = {}
        rt = rte = None
        if self.cfg["rotate_refresh_tokens"] is True:
            rt, rte = self.get_new_refresh_token()
            kwargs = {"new_rt": rt, "new_rte": rte}

        new_token, new_expire = await self.create_access_token(user)
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
