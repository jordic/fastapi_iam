from . import auth
from . import interfaces
from . import views
from .initialize import initialize_db
from .provider import set_provider
from .services import pg
from .views import admin
from fastapi import APIRouter
from fastapi_asyncpg import configure_asyncpg
from functools import partial

import logging
import typing

logger = logging.getLogger("fastapi_iam")


default_settings = {
    "db_schema": "",
    "jwt_expiration": 6 * 60 * 60,  # expiratoin in seconds
    "jwt_algorithm": "HS256",
    "jwt_secret_key": "XXXXX",
    "cookie_domain": None,
    "session_expiration": 60 * 60 * 24 * 360,  # one year
    "rotate_refresh_tokens": True,
    "db_pool": None,
    "services": {
        interfaces.IUsersStorage: pg.UserStorage,
        interfaces.ISessionStorage: pg.SessionStorage,
        interfaces.IGroupsStorage: pg.GroupStorage,
    },
    "default_service_factory": pg.pg_service_factory,
    "admin_routes": True,
    "refresh_token_secret_key": "xxxxx",  # just in case using secure cookie tokens
}


def configure_iam(
    settings: typing.Dict[str, typing.Any],
    *,
    security_policy=auth.PersistentSecurityPolicy,
    fastapi_asyncpg: configure_asyncpg = None,
):
    if "jwt_secret_key" not in settings:
        logger.warning("INSECURE SECRET KEY, provide a new one")

    defaults = default_settings.copy()
    defaults.update(settings)
    iam = IAM(
        defaults,
        fastapi_asyncpg=fastapi_asyncpg,
        security_policy=security_policy,
    )
    set_provider(iam)
    return iam


class IAM:
    def __init__(
        self,
        settings,
        *,
        fastapi_asyncpg=None,
        security_policy=None,
        api_router_cls=APIRouter,
    ):
        self.router = api_router_cls()
        self.settings = settings
        self.db = fastapi_asyncpg
        self.security_policy = security_policy
        self.services = settings["services"]
        self.services_factory = {}
        self.initialize_iam_db = partial(initialize_db, settings)
        self.setup_routes()

    def set_asyncpg(self, db):
        self.db = db

    def setup_routes(self):
        self.router.add_api_route("/status", views.status)
        self.router.add_api_route("/login", views.login, methods=["POST"])
        self.router.add_api_route(
            "/logout", views.logout, methods=["POST", "GET"]
        )
        self.router.add_api_route("/renew", views.renew, methods=["POST"])
        self.router.add_api_route("/whoami", views.whoami)

        if self.settings["admin_routes"] is True:
            admin.setup_routes(self.router)

    @property
    def pool(self):
        return self.db.pool

    def get_security_policy(self):
        return self.security_policy(self)

    def get_service(self, service_type):
        assert service_type in self.services
        factory = self.settings["default_service_factory"]
        if service_type in self.services_factory:
            factory = self.services_factory[service_type]
        return factory(self, self.services[service_type])
