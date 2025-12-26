from fastapi import APIRouter, Request
from sqlbot_xpack.config.model import SysArgModel

from apps.system.crud.parameter_manage import get_groups, get_parameter_args, save_parameter_args
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import SessionDep

router = APIRouter(tags=["system/parameter"], prefix="/system/parameter", include_in_schema=False)
from sqlbot_xpack.audit.models.log_model import OperationType, OperationModules
from sqlbot_xpack.audit.schemas.logger_decorator import LogConfig, system_log

@router.get("/login")
async def get_login_args(session: SessionDep) -> list[SysArgModel]:
    return await get_groups(session, "login")


@router.get("")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def get_args(session: SessionDep) -> list[SysArgModel]:
    return await get_parameter_args(session)


@router.post("", )
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.PARAMS_SETTING))
async def save_args(session: SessionDep, request: Request):
    return await save_parameter_args(session=session, request=request)


@router.get("/chat")
async def get_chat_args(session: SessionDep) -> list[SysArgModel]:
    return await get_groups(session, "chat")
