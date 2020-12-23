from __future__ import annotations

from .. import models
from ..provider import IAMProvider
from ..provider import get_current_user
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from random import randint

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

    session_manager = cfg["session_manager"](iam)
    # generate an acccess token
    user_session = await session_manager.create_session(user)

    # build the response and attach a refresh_token cookie
    response = JSONResponse(
        content={"access_token": user_session.token},
        headers={"cache-control": "no-store", "pargma": "no-cache"},
    )
    session_manager.remember(user_session, response, request=request)
    return response


async def whoami(user=Depends(get_current_user)):
    return models.PublicUser(**user.dict())


async def logout(user=Depends(get_current_user), iam=Depends(IAMProvider)):
    token = getattr(user, "token", None)
    if not token:
        return {}
    session_manager = iam.settings["session_manager"](iam)
    response = JSONResponse(content="keep safe")
    await session_manager.forget(user, response)
