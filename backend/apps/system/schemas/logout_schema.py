from typing import Optional
from pydantic import BaseModel


class LogoutSchema(BaseModel):
    token: Optional[str] = None
    flag: Optional[str] = 'default'
    origin: Optional[int] = 0
    data: Optional[str] = None