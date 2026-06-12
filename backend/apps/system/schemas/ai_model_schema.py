
from typing import List
from pydantic import BaseModel, Field

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.schemas import BaseCreatorDTO

class AiModelItem(BaseModel):
    name: str = Field(description=f"{PLACEHOLDER_PREFIX}model_name")
    model_type: int = Field(description=f"{PLACEHOLDER_PREFIX}model_type")
    base_model: str = Field(description=f"{PLACEHOLDER_PREFIX}base_model")
    supplier: int = Field(description=f"{PLACEHOLDER_PREFIX}supplier")
    protocol: int = Field(description=f"{PLACEHOLDER_PREFIX}protocol")
    default_model: bool = Field(default=False, description=f"{PLACEHOLDER_PREFIX}default_model")

class AiModelGridItem(AiModelItem, BaseCreatorDTO):
    ws_mapping_count: int = Field(default=0, description="workspace mapping count")

class AiModelConfigItem(BaseModel):
    key: str = Field(description=f"{PLACEHOLDER_PREFIX}arg_name")
    val: object = Field(description=f"{PLACEHOLDER_PREFIX}arg_val")
    name: str = Field(description=f"{PLACEHOLDER_PREFIX}arg_show_name")
    
class AiModelCreator(AiModelItem):
    api_domain: str = Field(description=f"{PLACEHOLDER_PREFIX}api_domain")
    api_key: str = Field(description=f"{PLACEHOLDER_PREFIX}api_key")
    config_list: List[AiModelConfigItem] = Field(description=f"{PLACEHOLDER_PREFIX}config_list")
    
class AiModelEditor(AiModelCreator, BaseCreatorDTO):
    pass

class BedrockModelListReq(BaseModel):
    region_name: str = Field(default="us-east-1", description="AWS region, e.g. ap-northeast-1")
    endpoint_type: str = Field(default="runtime", description="runtime or mantle")
    aws_access_key_id: str | None = Field(default=None, description="optional explicit AK")
    aws_secret_access_key: str | None = Field(default=None, description="optional explicit SK")
    aws_session_token: str | None = Field(default=None, description="optional session token")