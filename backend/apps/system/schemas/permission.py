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
from apps.datasource.models.datasource import CoreDatasource
from common.core.db import engine
from apps.system.schemas.system_schema import UserInfoDTO


class SqlbotPermission(BaseModel):
    role: Optional[list[str]] = None
    type: Optional[str] = None
    keyExpression: Optional[str] = None

async def get_ws_resource(oid, type) -> list:
    with Session(engine) as session:
        stmt = None
        if type == 'ds' or type == 'datasource':
            stmt = select(CoreDatasource.id).where(CoreDatasource.oid == oid)
        if type == 'chat':
            stmt = select(Chat.id).where(Chat.oid == oid) 
        if stmt is not None:
            db_list = session.exec(stmt).all()
            return db_list
        return []     
            

async def check_ws_permission(oid, type, resource) -> bool:
    resource_id_list = await get_ws_resource(oid, type)
    if not resource_id_list:
        return False
    if isinstance(resource, list):
        return set(resource).issubset(set(resource_id_list))
    return resource in resource_id_list
        
 
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
            current_oid = current_user.oid
            
            if current_user.isAdmin:
                return await func(*args, **kwargs)
            role_list = permission.role
            keyExpression = permission.keyExpression
            resource_type = permission.type
            
            if role_list:
                if 'admin' in role_list and not current_user.isAdmin:
                    raise Exception('no permission to execute, only for admin')
                if 'ws_admin' in role_list and current_user.weight == 0:
                    raise Exception('no permission to execute, only for workspace admin')
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
                        if await check_ws_permission(current_oid, resource_type, value):
                            return await func(*args, **kwargs)
                        raise Exception('no permission to execute or resource do not exist!')
                            
                parts = keyExpression.split('.')
                if not bound_args.arguments.get(parts[0]):
                    return await func(*args, **kwargs)
                value = bound_args.arguments[parts[0]]
                for part in parts[1:]:
                    value = getattr(value, part)
                if await check_ws_permission(current_oid, resource_type, value):
                    return await func(*args, **kwargs)
                raise Exception('no permission to execute or resource do not exist!')
            
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