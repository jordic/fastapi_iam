from fastapi_asyncpg import configure_asyncpg
from . import views
from . import services
from . import respository
from .initialize import initialize_db
from .provider import set_provider
from fastapi import APIRouter
from functools import partial

import typing
import logging

logger = logging.getLogger("fastapi_iam")


default_settings = {
    "db_schema": "",
    "password_algorithm": "argon2",
    "jwt_expiration": 1 * 60 * 60,  # expiratoin in seconds
    "jwt_algorithm": "HS256",
    "jwt_secret_key": "XXXXX",
    "cookie_domain": None,
    "refresh_cookie_name": "refresh_token",
    "refresh_cookie_expiration": 60 * 60 * 24,  # one day
}

_services = {
    "PasswordHasher": services.PasswordHasher,
    "AuthService": services.AuthService,
}


def configure_iam(
    settings: dict[str, typing.Any],
    *,
    fastapi_asyncpg: configure_asyncpg = None,
    services: dict[str, typing.Any] = None,
    repositories: dict[str, typing.Any] = None,
):
    if "jwt_secret_key" not in settings:
        logger.warning("INSECURE SECRET KEY, provide a new one")

    defaults = default_settings.copy()
    defaults.update(settings)
    default_services = _services.copy()
    default_services.update(services or {})
    iam = IAM(
        defaults,
        fastapi_asyncpg=fastapi_asyncpg,
        services=default_services,
        repositories=repositories,
    )
    set_provider(iam)
    return iam


class IAM:
    def __init__(
        self,
        settings,
        *,
        fastapi_asyncpg=None,
        api_router_cls=APIRouter,
        services=_services,
        repositories=None,
    ):
        self.router = api_router_cls()
        self.settings = settings
        self.db = fastapi_asyncpg
        self.initialize_iam_db = partial(initialize_db, settings)
        self.services = services
        self._services_ins = {}
        self._repostiories = repositories or {}
        self.setup_routes()

    def set_asyncpg(self, db):
        self.db = db

    def setup_routes(self):
        self.router.add_api_route("/status", views.status)
        self.router.add_api_route("/login", views.login, methods=["POST"])

    def get_service(self, name):
        assert name in self.services
        if name not in self._services_ins:
            self._services_ins[name] = self.services[name]()
        return self._services_ins[name]

    def get_repository(self, name):
        if name in self._repositories:
            return self._repostiories[name]
        return getattr(respository, name)
