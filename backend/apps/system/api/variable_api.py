# Author: Junjun
# Date: 2026/1/26
from typing import List
from fastapi import APIRouter

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.crud.system_variable import save, delete, list_all, list_page
from apps.system.models.system_variable_model import SystemVariable
from common.core.config import settings
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["System_variable"], prefix="/sys_variable")
path = settings.EXCEL_PATH


@router.post("/save", response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_save")
async def save_variable(session: SessionDep, user: CurrentUser, trans: Trans, variable: SystemVariable):
    return save(session, user, trans, variable)


@router.post("/delete",response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_delete")
async def delete_variable(session: SessionDep, ids: List[int]):
    return delete(session, ids)


@router.post("/listAll",response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_list")
async def list_all_data(session: SessionDep, trans: Trans, variable: SystemVariable = None):
    return list_all(session, trans, variable)


@router.post("/listPage/{pageNum}/{pageSize}",response_model=None, summary=f"{PLACEHOLDER_PREFIX}variable_page")
async def pager(session: SessionDep, trans: Trans, pageNum: int, pageSize: int,
                        variable: SystemVariable = None):
    return await list_page(session, trans, pageNum, pageSize, variable)
