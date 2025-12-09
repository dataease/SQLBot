
from fastapi import APIRouter, Request
from sqlbot_xpack.config.model import SysArgModel


from apps.system.crud.parameter_manage import get_parameter_args, save_parameter_args
from common.core.deps import SessionDep

router = APIRouter(tags=["system/parameter"], prefix="/system/parameter")

@router.get("")
async def get_args(session: SessionDep) -> list[SysArgModel]:
    return await get_parameter_args(session)

@router.post("", )
async def save_args(session: SessionDep, request: Request):
    return await save_parameter_args(session = session, request = request)
