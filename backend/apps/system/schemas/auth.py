
from typing import Optional
from pydantic import BaseModel
from enum import Enum

class LocalLoginSchema(BaseModel):
    account: str
    password: str
    
class CacheNamespace(Enum):
    AUTH_INFO = "sqlbot:auth"
    EMBEDDED_INFO = "sqlbot:embedded"
    def __str__(self):
        return self.value
class CacheName(Enum):
    USER_INFO = "user:info"
    ASSISTANT_INFO = "assistant:info"
    ASSISTANT_DS = "assistant:ds"
    def __str__(self):
        return self.value
    
