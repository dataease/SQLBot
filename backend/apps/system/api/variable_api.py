# Author: Junjun
# Date: 2026/1/26
from fastapi import APIRouter, Request

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.crud.system_variable import delete, list_all, list_page, save
from apps.system.models.system_variable_model import SystemVariable
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.config import settings
from common.core.deps import CurrentUser, SessionDep, Trans

router = APIRouter(tags=["System_variable"], prefix="/sys_variable")
path = settings.EXCEL_PATH


@router.post("/save", response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_save")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def save_variable(
    request: Request, session: SessionDep, user: CurrentUser, trans: Trans, variable: SystemVariable
):
    return save(session, user, trans, variable, request)


@router.post("/delete", response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_delete")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def delete_variable(request: Request, session: SessionDep, user: CurrentUser, ids: list[int]):
    return delete(session, ids, user, request)


@router.post("/listAll",response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_list")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def list_all_data(session: SessionDep, trans: Trans, variable: SystemVariable = None):
    return list_all(session, trans, variable)


@router.post("/listPage/{pageNum}/{pageSize}",response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_page")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def pager(session: SessionDep, trans: Trans, pageNum: int, pageSize: int,
                        variable: SystemVariable = None):
    return await list_page(session, trans, pageNum, pageSize, variable)
