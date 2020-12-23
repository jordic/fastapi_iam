from __future__ import annotations
from fastapi import Depends
from fastapi.requests import Request
from fastapi.security import OAuth2PasswordBearer
from .auth import extractors
from .models import anonymous_user
from fastapi.exceptions import HTTPException

current_app = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

PermissionDenied = HTTPException(
    status_code=403, detail="Insuficient permissions"
)


def set_provider(app):
    global current_app
    current_app = app


def IAMProvider():
    return current_app


async def get_current_user(
    request: Request, iam=Depends(IAMProvider), token=Depends(oauth2_scheme)
):
    token = await extractors(iam, request)
    if not token:
        return anonymous_user
    session_manager = iam.settings["session_manager"](iam)
    user = await session_manager.find_user(token)
    user.token = token.get("token")
    return user


class has_principal:
    def __init__(self, principal):
        self.principal = principal

    async def __call__(self, user=Depends(get_current_user)):
        if self.principal not in user.get_principals():
            raise PermissionDenied()
