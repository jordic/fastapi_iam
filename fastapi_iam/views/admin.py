from ..provider import IAMProvider
from fastapi import Depends
from ..provider import has_principal
from ..interfaces import IUsersStorage
from ..interfaces import IGroupsStorage
from .. import models
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


async def create_user(user: models.UserCreate, iam=Depends(IAMProvider)):
    res = await models.create_user(iam, user)
    return res


async def update_user(
    iam=Depends(IAMProvider), principals=Depends(has_principal("admin"))
):
    pass


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
    router.add_api_route(
        "/groups", create_group, methods=["POST"], status_code=201
    )
    router.add_api_route("/groups", get_groups, methods=["GET"])
