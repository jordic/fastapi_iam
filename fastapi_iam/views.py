from __future__ import annotations

from . import models
from .provider import IAMProvider
from fastapi import Depends
from fastapi.exceptions import HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from random import randint

import asyncio
import datetime
import uuid


async def status(request: Request, iam=Depends(IAMProvider)):
    breakpoint()
    async with iam.db.pool.acquire() as db:
        await db.fetch("select 1=1")
    return {"status": "ok"}


async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    iam=Depends(IAMProvider),
):
    hasher = iam.get_service("PasswordHasher")
    settings = iam.settings
    async with iam.pool.acquire() as db:
        repo = iam.get_repository("UserRepository")(db, settings["db_schema"])
        user = await repo.by_email(form_data["username"])
        valid = await hasher.check_password(
            user.password, form_data["password"]
        )
        if valid is False:
            await asyncio.sleep(randint(10, 200) / 1000)
            raise HTTPException(
                status_code=400, detail="Incorrect username or password"
            )
        # generate an acccess token
        jwt = iam.get_service("JWTService")
        access_token, expires = jwt.create_access_token(iam, user)
        refresh_token = uuid.uuid4().hex
        # store the access token + refresh token on the db
        ticket_repo = iam.get_repository("AuthTicketRepository")(
            db, settings["db_schema"]
        )
        ticket = models.AuthTicket(
            user_id=user.user_id,
            token=access_token,
            expires=expires,
            refres_token=refresh_token,
            refresh_token_expires=datetime.utcnow()
            + datetime.timedelta(seconds=settings["refresh_cookie_expiration"]),
        )
        await ticket_repo.store_ticket(ticket)
    # build the response and attach a refresh_token cookie
    response = JSONResponse(content={"access_token": access_token})
    cookie_domain = (
        settings["refresh_cookie_domain"]
        or request.headers["host"].split(":")[0]
    )
    response.set_cookie(
        settings["refresh_cookie_name"],
        refresh_token,
        max_age=settings["refresh_cookie_expiration"],
        expires=settings["refresh_cookie_expiration"],
        path="/",  # TODO scope cookie to auth path
        domain=cookie_domain,
        secure=False,
        httponly=True,
        samesite="lax",
    )
    return response


async def logout(iam=Depends(IAMProvider)):
    pass


async def refresh():
    pass


async def register():
    pass
