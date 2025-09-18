
from typing import List
from pydantic import BaseModel, field_validator
import json

from common.core.schemas import BaseCreatorDTO

class AiModelItem(BaseModel):
    name: str
    model_type: int
    base_model: str
    supplier: int
    protocol: int
    default_model: bool = False

class AiModelGridItem(AiModelItem, BaseCreatorDTO):
    pass

class AiModelConfigItem(BaseModel):
    key: str
    val: object
    name: str
    @field_validator('val')
    @classmethod
    def parse_json_strings(cls, v):
        if isinstance(v, str) and v.strip().startswith(('{', '[')):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                pass
        return v    
class AiModelCreator(AiModelItem):
    api_domain: str
    api_key: str
    config_list: List[AiModelConfigItem]
    
class AiModelEditor(AiModelCreator, BaseCreatorDTO):
    pass