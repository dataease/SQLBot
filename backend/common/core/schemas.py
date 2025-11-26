from fastapi import HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlmodel import SQLModel
from starlette.status import HTTP_403_FORBIDDEN, HTTP_401_UNAUTHORIZED
from common.core.config import settings
from fastapi.security.utils import get_authorization_scheme_param
from typing import Generic, TypeVar, Optional
class TokenPayload(BaseModel):
    account: str | None = None
    id: int | None = None
    oid: int | None = None
    
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"
    platform_info: Optional[dict] = None
    
class XOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        authorization = request.headers.get(settings.TOKEN_KEY)
        if request.headers.get(settings.ASSISTANT_TOKEN_KEY):
            authorization = request.headers.get(settings.ASSISTANT_TOKEN_KEY)
        scheme, param = get_authorization_scheme_param(authorization)
        
        if not authorization or scheme.lower() not in  ["bearer", "assistant"]:
            if self.auto_error:
                raise HTTPException(
                    status_code=HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None
        return param
    



T = TypeVar('T')

class PaginationParams(BaseModel):
    page: int = 1
    size: int = 20
    order_by: Optional[str] = None
    desc: bool = False

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    total_pages: int
    

class BaseCreatorDTO(BaseModel):
    id: int
    class Config:
        json_encoders = {
            int: lambda v: str(v) if isinstance(v, int) and v > (2**53 - 1) else v
        }