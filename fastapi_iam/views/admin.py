from .. import models
from ..interfaces import IGroupsStorage
from ..interfaces import IUsersStorage
from ..provider import has_principal
from ..provider import IAMProvider
from fastapi import Depends
from fastapi.exceptions import HTTPException
from typing import Optional


async def query(
    q: Optional[str] = None,
    page: int = 0,
    limit: int = 100,
    is_staff: Optional[bool] = None,
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
):
    return {
        "q": q,
        "page": page,
        "limit": limit,
        "is_staff": is_staff,
        "is_active": is_active,
        "is_admin": is_admin,
    }


async def get_users(
    query: dict = Depends(query),
    iam=Depends(IAMProvider),
    principals=Depends(has_principal("admin")),
):
    users_service = iam.get_service(IUsersStorage)
    return await users_service.search(**query)


async def get_user(
    user_id: int,
    iam=Depends(IAMProvider),
    principals=Depends(has_principal("admin")),
):
    ur = iam.get_service(IUsersStorage)
    obj = await ur.by_id(user_id)
    if not obj:
        raise HTTPException(404)
    return models.PublicUser(**dict(obj))


async def create_user(
    user: models.UserCreate,
    iam=Depends(IAMProvider),
    principals=Depends(has_principal("admin")),
):
    res = await models.create_user(iam, user)
    return res


async def update_user(
    user: models.UserUpdate,
    user_id: int,
    iam=Depends(IAMProvider),
    principals=Depends(has_principal("admin")),
):
    ur = iam.get_service(IUsersStorage)
    obj = await ur.by_id(user_id)
    if obj is None:
        raise HTTPException(404, detail="user_not_found")

    data = user.dict(exclude_unset=True)
    if "password" in data:
        security_policy = iam.get_security_policy()
        hasher = security_policy.hasher
        data["password"] = await hasher.hash_password(data["password"])
    return await ur.update_user(user_id, data)


async def create_group(
    group: models.Group,
    iam=Depends(IAMProvider),
    principals=Depends(has_principal("admin")),
):
    gr = iam.get_service(IGroupsStorage)
    res = await gr.add_group(group.name)
    return dict(res)


async def get_groups(
    iam=Depends(IAMProvider), principals=Depends(has_principal("admin"))
):
    gr = iam.get_service(IGroupsStorage)
    return await gr.get_groups()


def setup_routes(router):
    router.add_api_route("/users", get_users)
    router.add_api_route(
        "/users", create_user, methods=["POST"], status_code=201
    )
    router.add_api_route("/users/{user_id:int}", get_user)
    router.add_api_route("/users/{user_id:int}", update_user, methods=["PATCH"])
    router.add_api_route(
        "/groups", create_group, methods=["POST"], status_code=201
    )
    router.add_api_route("/groups", get_groups, methods=["GET"])
