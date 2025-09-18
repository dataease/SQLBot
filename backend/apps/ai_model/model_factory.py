from functools import lru_cache
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Type

from langchain.chat_models.base import BaseChatModel
from pydantic import BaseModel
from sqlmodel import Session, select

from apps.ai_model.openai.llm import BaseChatOpenAI
from apps.system.models.system_model import AiModelDetail
from common.core.db import engine
from common.utils.crypto import sqlbot_decrypt
from common.utils.utils import prepare_model_arg
from langchain_community.llms import VLLMOpenAI
from langchain_openai import AzureChatOpenAI
# from langchain_community.llms import Tongyi, VLLM

class LLMConfig(BaseModel):
    """Base configuration class for large language models"""
    model_id: Optional[int] = None
    model_type: str  # Model type: openai/tongyi/vllm etc.
    model_name: str  # Specific model name
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None
    additional_params: Dict[str, Any] = {}
    class Config:
        frozen = True

    def __hash__(self):
        if hasattr(self, 'additional_params') and isinstance(self.additional_params, dict):
            hashable_params = frozenset((k, tuple(v) if isinstance(v, (list, dict)) else v) 
                            for k, v in self.additional_params.items())
        else:
            hashable_params = None
        
        return hash((
            self.model_id,
            self.model_type,
            self.model_name,
            self.api_key,
            self.api_base_url,
            hashable_params
        ))


class BaseLLM(ABC):
    """Abstract base class for large language models"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self._llm = self._init_llm()

    @abstractmethod
    def _init_llm(self) -> BaseChatModel:
        """Initialize specific large language model instance"""
        pass

    @property
    def llm(self) -> BaseChatModel:
        """Return the langchain LLM instance"""
        return self._llm

class OpenAIvLLM(BaseLLM):
    def _init_llm(self) -> VLLMOpenAI:
        return VLLMOpenAI(
            openai_api_key=self.config.api_key or 'Empty',
            openai_api_base=self.config.api_base_url,
            model_name=self.config.model_name,
            streaming=True,
            **self.config.additional_params,
        )

class OpenAIAzureLLM(BaseLLM):
    def _init_llm(self) -> AzureChatOpenAI:
        api_version = self.config.additional_params.get("api_version")
        deployment_name = self.config.additional_params.get("deployment_name")
        if api_version:
            self.config.additional_params.pop("api_version")
        if deployment_name:
            self.config.additional_params.pop("deployment_name")
        return AzureChatOpenAI(
            azure_endpoint=self.config.api_base_url,
            api_key=self.config.api_key or 'Empty',
            model_name=self.config.model_name,
            api_version=api_version,
            deployment_name=deployment_name,
            streaming=True,
            **self.config.additional_params,
        )
class OpenAILLM(BaseLLM):
    def _init_llm(self) -> BaseChatModel:
        
        params = {}
        for key, value in self.config.additional_params.items():
            if isinstance(value, str) and value.strip().startswith(('{', '[')):
                try:
                    import json
                    parsed_value = json.loads(value)
                    params[key] = parsed_value
                except json.JSONDecodeError as e:
                    
                    params[key] = value
            else:
                params[key] = value

        return BaseChatOpenAI(
            model=self.config.model_name,
            api_key=self.config.api_key or 'Empty',
            base_url=self.config.api_base_url,
            stream_usage=True,
            # **self.config.additional_params,
            **params,
        )

    def generate(self, prompt: str) -> str:
        return self.llm.invoke(prompt)


class LLMFactory:
    """Large Language Model Factory Class"""

    _llm_types: Dict[str, Type[BaseLLM]] = {
        "openai": OpenAILLM,
        "tongyi": OpenAILLM,
        "vllm": OpenAIvLLM,
        "azure": OpenAIAzureLLM,
    }

    @classmethod
    @lru_cache(maxsize=32)
    def create_llm(cls, config: LLMConfig) -> BaseLLM:
        llm_class = cls._llm_types.get(config.model_type)
        if not llm_class:
            raise ValueError(f"Unsupported LLM type: {config.model_type}")
        return llm_class(config)

    @classmethod
    def register_llm(cls, model_type: str, llm_class: Type[BaseLLM]):
        """Register new model type"""
        cls._llm_types[model_type] = llm_class


#  todo
""" def get_llm_config(aimodel: AiModelDetail) -> LLMConfig:
    config = LLMConfig(
        model_type="openai",
        model_name=aimodel.name,
        api_key=aimodel.api_key,
        api_base_url=aimodel.endpoint,
        additional_params={"temperature": aimodel.temperature}
    )
    return config """


async def get_default_config() -> LLMConfig:
    with Session(engine) as session:
        db_model = session.exec(
            select(AiModelDetail).where(AiModelDetail.default_model == True)
        ).first()
        if not db_model:
            raise Exception("The system default model has not been set")

        additional_params = {}
        if db_model.config:
            try:
                config_raw = json.loads(db_model.config)
                additional_params = {item["key"]: prepare_model_arg(item.get('val')) for item in config_raw if "key" in item and "val" in item}
            except Exception:
                pass
        if not db_model.api_domain.startswith("http"):
            db_model.api_domain = await sqlbot_decrypt(db_model.api_domain)
            if db_model.api_key:
                db_model.api_key = await sqlbot_decrypt(db_model.api_key)
            

        # 构造 LLMConfig
        return LLMConfig(
            model_id=db_model.id,
            model_type="openai" if db_model.protocol == 1 else "vllm",
            model_name=db_model.base_model,
            api_key=db_model.api_key,
            api_base_url=db_model.api_domain,
            additional_params=additional_params,
        )
