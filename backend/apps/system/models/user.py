
from typing import Optional
from sqlmodel import BigInteger, SQLModel, Field

from common.core.models import SnowflakeBase
from common.core.security import default_md5_pwd
from common.utils.time import get_timestamp



class BaseUserPO(SQLModel):
    account: str = Field(max_length=255, unique=True)
    oid: int = Field(nullable=False, sa_type=BigInteger(), default=0)
    name: str = Field(max_length=255, unique=True)
    password: str = Field(default_factory=default_md5_pwd, max_length=255)
    email: str = Field(max_length=255)
    status: int = Field(default=0, nullable=False)
    origin: int = Field(nullable=False, default=0)
    create_time: int = Field(default_factory=get_timestamp, sa_type=BigInteger(), nullable=False)
    language: str = Field(max_length=255, default="zh-CN")
    
class UserModel(SnowflakeBase, BaseUserPO, table=True):
    __tablename__ = "sys_user"
    

class UserPlatformBase(SQLModel):
    uid: int = Field(nullable=False, sa_type=BigInteger())
    origin: int = Field(nullable=False, default=0)
    platform_uid: str = Field(max_length=255, nullable=False)
    
class UserPlatformModel(SnowflakeBase, UserPlatformBase, table=True):
    __tablename__ = "sys_user_platform"
    
    
