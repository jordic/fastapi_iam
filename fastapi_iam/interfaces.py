from __future__ import annotations

from typing import Protocol


class IIAM(Protocol):
    """ Thats the main application entry point """

    def get_session_manager() -> "ISessionManager":
        pass


class ISessionManager(Protocol):
    """
    The main responsability of a session manager is to handle
    the different flows of autenticated users.

    It's also emiting jwt tokens to be consumed for other systems
    but it ensures the presence of the token on the db.

    If token is invalidated from the db, the user is automatically logged out
    A cookie is emitted to act as a refresh token for the user
    """

    iam: IIAM  # instance of the main appliaction, used as a poor man registry

    async def create_session(self, user):
        pass

    async def validate(self, token):
        pass

    async def refresh(self, refresh_token):
        pass

    async def remember(self, user_session, response, *, request=None):
        pass

    async def forget(self, user_session, response, *, request=None):
        pass


class IUsersStorage(Protocol):
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
    async def add_group(self, name):
        pass

    async def get_groups(self):
        pass

    async def get_group(self, name):
        pass


class ISessionStorage(Protocol):
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
