
from sqlmodel import BigInteger, Field, SQLModel
from common.core.models import SnowflakeBase


class AiModelBase:
    name: str = Field(max_length=255, nullable=False)
    type: int = Field(nullable=False)

class AiModelDetail(AiModelBase, SnowflakeBase, table=True):
   __tablename__ = "ai_model"
   api_key: str | None = Field(max_length=255, nullable=True)
   endpoint: str = Field(max_length=255, nullable=False)
   max_context_window: int = Field(default=0)
   temperature: float = Field(default=0.0)
   status: bool = Field(default=True)
   description: str | None = Field(max_length=255, nullable=True)
   create_time: int = Field(default=0, sa_type=BigInteger())