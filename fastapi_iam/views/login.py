from __future__ import annotations

from .. import events
from .. import models
from ..provider import get_current_user
from ..provider import IAMProvider
from fastapi import Cookie
from fastapi import Depends
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from random import randint
from typing import Optional

import asyncio

NO_CACHE = {"cache-control": "no-store", "pargma": "no-cache"}


async def status(request: Request, iam=Depends(IAMProvider)):
    async with iam.db.pool.acquire() as db:
        await db.fetch("select 1=1")
    return {"status": "ok"}


async def invalid_user():
    await asyncio.sleep(randint(10, 200) / 1000)
    raise HTTPException(
        status_code=400, detail="Incorrect username or password"
    )


async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    iam=Depends(IAMProvider),
):
    auth_manager = iam.get_security_policy()
    return await auth_manager.login(
        form_data.username, form_data.password, request=request
    )


async def whoami(user=Depends(get_current_user)):
    return models.PublicUser(**user.dict())


async def logout(user=Depends(get_current_user), iam=Depends(IAMProvider)):
    token = getattr(user, "token", None)
    if not token:
        return {}
    session_manager = iam.get_security_policy()
    await events.notify(events.UserLogout(user))
    response = JSONResponse(content="keep safe")
    await session_manager.forget(user, response)


async def renew(
    request: Request,
    iam=Depends(IAMProvider),
    refresh: Optional[str] = Cookie(None),
):
    sm = iam.get_security_policy()
    user_session = await sm.refresh(refresh)
    response = JSONResponse(
        jsonable_encoder(
            {
                "access_token": user_session.token,
                "expiration": user_session.expires,
            }
        ),
        headers=NO_CACHE,
    )
    if iam.settings["rotate_refresh_tokens"] is True:
        await sm.remember(user_session, response, request=request)
    return response


async def reset_password():
    pass


async def password_change():
    pass
