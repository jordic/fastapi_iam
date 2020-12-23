from .. import models
from fastapi_asyncpg import sql
from fastapi.exceptions import HTTPException

import datetime
import json
import jwt
import uuid

InvalidUser = HTTPException(status_code=403, detail="invalid_user")


class SessionDbManager:
    """
    A session manager that persists data on the db.
    It's also emiting jwt tokens to be consumed for other systems
    but it ensures the presence of the token on the db.
    If token is invalidated from the db, the user is automatically logged out
    A cookie is emitted to act as a refresh token for the user
    """

    cookie_name = "refresh"

    def __init__(self, iam):
        """Every session data manager receives an instance of the iam
        preconfigured app. This way, you can wire dependencies from the
        instantiation, and use the iam instance (singleton) as a
        poor man registry
        """
        self.iam = iam

    async def create_session(self, user, data=None) -> models.UserSession:
        """
        creates a sesssion, makes a token, and stores on the db.
        Also fabricates a token to be usable on the refreshtoken endpoint
        """
        token, expire = await self.create_access_token(user)
        refresh_token = refresh_token = uuid.uuid4().hex
        refresh_expiration = datetime.datetime.utcnow() + datetime.timedelta(
            seconds=self.cfg["session_expiration"]
        )
        data = data or {}
        async with self.iam.pool.acquire() as db:
            result = await sql.insert(
                db,
                f"{self.schema}users_session",
                {
                    "user_id": user.user_id,
                    "token": token,
                    "expires": expire,
                    "refresh_token": refresh_token,
                    "refresh_token_expires": refresh_expiration,
                    "data": json.dumps(data),
                },
            )
            return models.UserSession(**dict(result))

    @property
    def schema(self):
        db_schema = self.iam.settings["db_schema"]
        return f"{db_schema}." if db_schema != "" else ""

    @property
    def cfg(self):
        return self.iam.settings

    async def find_user(self, token) -> models.User:
        if token.get("id") == "root":  # todo ensure password matches
            return models.root_user
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

        async with self.iam.pool.acquire() as db:
            repo = models.UserRepository(db, self.schema)
            user = await repo.by_token(token=token.get("token"))
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

    async def update():
        pass

    async def forget(self, user, response):
        async with self.iam.pool.acquire() as db:
            await sql.delete(
                db, f"{self.schema}users_session", "token=$1", args=[user.token]
            )
            # cleanup cookie
            response.delete_cookie(
                self.cookie_name, path="/", domain=self.cfg["cookie_domain"]
            )

    def remember(self, user_session, response, request=None):
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
