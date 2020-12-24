from __future__ import annotations

from .. import models
from ..provider import get_current_user
from ..provider import IAMProvider
from fastapi import Cookie
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from random import randint
from typing import Optional

import asyncio


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
    cfg = iam.settings
    ph = cfg["password_hasher"]()
    async with iam.pool.acquire() as db:
        um = models.UserRepository(db, cfg["db_schema"])
        user = await um.by_email(form_data.username)
        if not user:
            return await invalid_user()

    if user.is_active is False:
        raise HTTPException(status_code=412, detail="User is inactive")

    valid = await ph.check_password(user.password, form_data.password)
    if valid is False:
        return await invalid_user()

    session_manager = iam.get_session_manager()
    # generate an acccess token
    user_session = await session_manager.create_session(user)

    # build the response and attach a refresh_token cookie
    response = JSONResponse(
        content={"access_token": user_session.token},
        headers={"cache-control": "no-store", "pargma": "no-cache"},
    )
    await session_manager.remember(user_session, response, request=request)
    return response


async def whoami(user=Depends(get_current_user)):
    return models.PublicUser(**user.dict())


async def logout(user=Depends(get_current_user), iam=Depends(IAMProvider)):
    token = getattr(user, "token", None)
    if not token:
        return {}
    session_manager = iam.get_session_manager()
    response = JSONResponse(content="keep safe")
    await session_manager.forget(user, response)


async def renew(
    request: Request,
    iam=Depends(IAMProvider),
    refresh: Optional[str] = Cookie(None),
):
    sm = iam.get_session_manager()
    user_session = await sm.refresh(refresh)
    response = JSONResponse(
        {"access_token": user_session.token, "expiration": user_session.expires}
    )
    if iam.settings["rotate_refresh_tokens"] is True:
        await sm.remember(user_session, response, request=request)
    return response
