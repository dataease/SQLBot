from contextvars import ContextVar
from functools import wraps
from inspect import signature
from typing import Optional
from fastapi import HTTPException, Request
from pydantic import BaseModel
import re
from starlette.middleware.base import BaseHTTPMiddleware
from sqlmodel import Session, select
from apps.chat.models.chat_model import Chat
from apps.dashboard.models.dashboard_model import CoreDashboard
from apps.datasource.crud.datasource import get_ws_ds
from apps.datasource.models.datasource import CoreDatasource
from common.core.db import engine
from apps.system.schemas.system_schema import UserInfoDTO

from common.utils.locale import I18n
i18n = I18n()

class SqlbotPermission(BaseModel):
    role: Optional[list[str]] = None
    type: Optional[str] = None
    keyExpression: Optional[str] = None

async def get_ws_resource(oid, type) -> list:
    with Session(engine) as session:
        stmt = None
        if type == 'ds' or type == 'datasource':
            return await get_ws_ds(session, oid)
        if type == 'chat':
            stmt = select(Chat.id).where(Chat.oid == oid)
        if type == 'dashboard':
            # workspace_id 是 VARCHAR 类型，需要转换为字符串
            stmt = select(CoreDashboard.id).where(CoreDashboard.workspace_id == str(oid))
        if stmt is not None:
            db_list = session.exec(stmt).all()
            return db_list
        return []     
            

async def check_ws_permission(oid, type, resource) -> bool:
    if not resource or (isinstance(resource, list) and len(resource) == 0):
        return True

    resource_id_list = await get_ws_resource(oid, type)
    if not resource_id_list:
        return False
    if isinstance(resource, list):
        return set(resource).issubset(set(resource_id_list))
    return resource in resource_id_list


async def _dynamic_assistant_ds_allowed(assistant, ds_id) -> bool:
    """高级小助手（type 1/3 动态数据源）的 ds 来自宿主 API，本地 core_datasource 无记录：
    仅当 ds_id 在本地不存在时才跳过归属校验；本地数据源仍按工作区 oid 校验。"""
    if assistant is None or assistant.type not in (1, 3) or isinstance(ds_id, list):
        return False
    with Session(engine) as session:
        return session.get(CoreDatasource, ds_id) is None


def require_permissions(permission: SqlbotPermission):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request = RequestContext.get_request()
            
            current_user: UserInfoDTO = getattr(request.state, 'current_user', None)
            if not current_user:
                raise HTTPException(
                    status_code=401,
                    detail="用户未认证"
                )
            assistant = getattr(request.state, 'assistant', None)
            current_oid = current_user.oid
            
            trans = i18n(request)
            
            if current_user.isAdmin and not permission.type:
                return await func(*args, **kwargs)
            role_list = permission.role
            keyExpression = permission.keyExpression
            resource_type = permission.type
            
            if role_list:
                if 'admin' in role_list and not current_user.isAdmin:
                    #raise Exception('no permission to execute, only for admin')
                    raise Exception(trans('i18n_permission.only_admin'))
                if 'ws_admin' in role_list and current_user.weight == 0 and not current_user.isAdmin:
                    #raise Exception('no permission to execute, only for workspace admin')
                    raise Exception(trans('i18n_permission.only_ws_admin'))
            if not resource_type:
                return await func(*args, **kwargs)
            if keyExpression:
                sig = signature(func)
                bound_args = sig.bind_partial(*args, **kwargs)
                bound_args.apply_defaults()
                
                if keyExpression.startswith("args["):
                    if match := re.match(r"args\[(\d+)\]", keyExpression):
                        index = int(match.group(1))
                        value = bound_args.args[index]
                        if await check_ws_permission(current_oid, resource_type, value) or (
                                resource_type in ('ds', 'datasource')
                                and await _dynamic_assistant_ds_allowed(assistant, value)):
                            return await func(*args, **kwargs)
                        #raise Exception('no permission to execute or resource do not exist!')
                        raise Exception(trans('i18n_permission.permission_resource_limit'))
                            
                parts = keyExpression.split('.')
                if not bound_args.arguments.get(parts[0]):
                    return await func(*args, **kwargs)
                value = bound_args.arguments[parts[0]]
                for part in parts[1:]:
                    value = getattr(value, part)
                if await check_ws_permission(current_oid, resource_type, value) or (
                        resource_type in ('ds', 'datasource')
                        and await _dynamic_assistant_ds_allowed(assistant, value)):
                    return await func(*args, **kwargs)
                raise Exception(trans('i18n_permission.permission_resource_limit'))
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

class RequestContext:
    
    _current_request: ContextVar[Request] = ContextVar("_current_request")
    @classmethod
    def set_request(cls, request: Request):
        return cls._current_request.set(request)
    
    @classmethod
    def get_request(cls) -> Request:
        try:
            return cls._current_request.get()
        except LookupError:
            raise RuntimeError(
                "No request context found. "
                "Make sure RequestContextMiddleware is installed."
            )
    
    @classmethod
    def reset(cls, token):
        cls._current_request.reset(token)

class RequestContextMiddleware(BaseHTTPMiddleware):
    
    async def dispatch(self, request: Request, call_next):
        token = RequestContext.set_request(request)
        try:
            response = await call_next(request)
            return response
        finally:
            RequestContext.reset(token)