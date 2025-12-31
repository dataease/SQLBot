
from fastapi import APIRouter
from sqlmodel import func, select
from apps.system.crud.apikey_manage import clear_api_key_cache
from apps.system.models.system_model import ApiKeyModel
from apps.system.schemas.system_schema import ApikeyGridItem, ApikeyStatus
from common.core.deps import CurrentUser, SessionDep
from common.utils.time import get_timestamp
import secrets

router = APIRouter(tags=["system_apikey"], prefix="/system/apikey", include_in_schema=False)
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log

@router.get("")
async def grid(session: SessionDep, current_user: CurrentUser) -> list[ApikeyGridItem]:
    query = select(ApiKeyModel).where(ApiKeyModel.uid == current_user.id).order_by(ApiKeyModel.create_time.desc())
    return session.exec(query).all()

@router.post("")
@system_log(LogConfig(operation_type=OperationType.CREATE, module=OperationModules.API_KEY,result_id_expr='result.self'))
async def create(session: SessionDep, current_user: CurrentUser):
    count = session.exec(select(func.count()).select_from(ApiKeyModel).where(ApiKeyModel.uid == current_user.id)).one()
    if count >= 5:
        raise ValueError("Maximum of 5 API keys allowed")
    access_key = secrets.token_urlsafe(16)
    secret_key = secrets.token_urlsafe(32)
    api_key = ApiKeyModel(
        access_key=access_key,
        secret_key=secret_key,
        create_time=get_timestamp(),
        uid=current_user.id,
        status=True
    )
    session.add(api_key)
    session.commit()
    return api_key.id

@router.put("/status")
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.API_KEY,resource_id_expr='id'))
async def status(session: SessionDep, current_user: CurrentUser, dto: ApikeyStatus):
    api_key = session.get(ApiKeyModel, dto.id)
    if not api_key:
        raise ValueError("API Key not found")
    if api_key.uid != current_user.id:
        raise PermissionError("No permission to modify this API Key")
    if dto.status == api_key.status:
        return
    api_key.status = dto.status
    await clear_api_key_cache(api_key.access_key)
    session.add(api_key)
    session.commit()

@router.delete("/{id}")
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.API_KEY,resource_id_expr='id'))
async def delete(session: SessionDep, current_user: CurrentUser, id: int):
    api_key = session.get(ApiKeyModel, id)
    if not api_key:
        raise ValueError("API Key not found")
    if api_key.uid != current_user.id:
        raise PermissionError("No permission to delete this API Key")
    await clear_api_key_cache(api_key.access_key)
    session.delete(api_key)
    session.commit()
    