from __future__ import annotations

from . import models
from typing import Protocol

import typing


class IIAM(Protocol):
    """ Thats the main application entry point """

    settings: typing.Dict[str, typing.Any]

    security_policy: ISecurityPolicy
    services: typing.Dict[typing.Any, typing.Any]  # a registry for service
    # factory for each service
    services_factory: typing.Dict[typing.Any, typing.Callable]

    def get_security_policy(self) -> "ISecurityPolicy":
        pass

    def get_service(self, service_type):
        """Given a registered IService, factorizes an instance of it
        ready to be used. If no factory declared, it uses
            settings["default_service_factory"]
        This is mostly used to inject a db connection or other settings
        into a service.
        """
        pass


class ISecurityPolicy(Protocol):
    """
    ISecurityPolicy is the core of the iam,
    It manages login, session validation, refresh, remember and forget
    This component could be extended to be able to add new features
    to it
    """

    iam: IIAM  # instance of the main appliaction, used as a poor man registry

    async def login(
        self, username: str, password: str, request=None
    ) -> typing.Tuple[models.PublicUser, models.UserSession]:
        """ Given a username and a password login the user"""
        pass

    async def create_session(self, user) -> models.UserSession:
        """ Creates a session an 'stores' it """
        pass

    async def validate(self, token) -> models.User:
        """ Vadlidates a session and returns the avaialble user"""
        pass

    async def refresh(self, refresh_token) -> models.UserSession:
        """ Creates a new access token and stores it using the refresh token"""
        pass

    async def remember(self, user_session, response, *, request=None):
        """ Makes the refresh token persistent using a cookie """
        pass

    async def forget(self, user_session, response, *, request=None):
        """ Forgets a user, after logout, removing the cookie """
        pass


class IUsersStorage(Protocol):
    """ Persistent storage service for users """

    async def create(self, user):
        pass

    async def by_email(self, email: str):
        pass

    async def by_id(self, user_id: int):
        pass

    async def by_token(self, *, token: str = None, refresh_token: str = None):
        pass

    async def update_user(self, user, data):
        pass

    async def update_groups(self, user, groups):
        pass


class IGroupsStorage(Protocol):
    """ Persistent storage service for groups """

    async def add_group(self, name):
        pass

    async def get_groups(self):
        pass

    async def get_group(self, name):
        pass


class ISessionStorage(Protocol):
    """ Persistent storage for sessions """

    async def create(self, user_session):
        pass

    async def is_expired(self, refresh_token):
        pass

    async def delete(self, token):
        pass

    async def update_token(
        self, refresh_token, token, expires, new_rt=None, new_rte=None
    ):
        pass


class ITokenStorage(Protocol):
    async def create_token_verification(self, user):
        pass

    async def create_token_login(self, email):
        pass

    async def create_token_forgot_pass(self, email):
        pass
