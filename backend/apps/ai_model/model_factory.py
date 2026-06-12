from functools import lru_cache
import json
import re
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

# protocol(int) stored on the model record -> internal model_type used by the factory
PROTOCOL_OPENAI = 1
PROTOCOL_VLLM = 2
PROTOCOL_BEDROCK = 3

_PROTOCOL_MODEL_TYPE: Dict[int, str] = {
    PROTOCOL_OPENAI: "openai",
    PROTOCOL_VLLM: "vllm",
    PROTOCOL_BEDROCK: "bedrock",
}


def get_model_type_by_protocol(protocol: Optional[int]) -> str:
    """Map the stored protocol value to the factory model_type.

    Falls back to the legacy behaviour (1 -> openai, everything else -> vllm)
    for any unknown value so existing records keep working.
    """
    if protocol == PROTOCOL_OPENAI:
        return "openai"
    return _PROTOCOL_MODEL_TYPE.get(protocol, "vllm")


def _region_from_bedrock_url(url: Optional[str]) -> Optional[str]:
    """Extract the AWS region from a bedrock-runtime / bedrock-mantle endpoint url."""
    if not url:
        return None
    match = re.search(r"bedrock(?:-runtime|-mantle)?\.([a-z0-9-]+)\.(?:amazonaws\.com|api\.aws)", url)
    return match.group(1) if match else None

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
        return BaseChatOpenAI(
            model=self.config.model_name,
            api_key=self.config.api_key or 'Empty',
            base_url=self.config.api_base_url,
            stream_usage=True,
            **self.config.additional_params,
        )

    def generate(self, prompt: str) -> str:
        return self.llm.invoke(prompt)


class BedrockLLM(BaseLLM):
    """Amazon Bedrock support for both available endpoint families:

    - ``bedrock-runtime`` (default): native Bedrock inference via the Converse
      API. Authenticates with SigV4 using the standard AWS credential chain
      (IAM role / profile / env vars) or explicit keys passed as advanced args.
    - ``bedrock-mantle``: OpenAI-compatible endpoint (Chat Completions). Reuses
      the OpenAI client with the mantle base url and a Bedrock API key.

    Control args are read from ``additional_params``:
      - ``endpoint_type``: ``runtime`` (default) or ``mantle``
      - ``region_name``: e.g. ``us-east-1`` (inferred from the url when omitted)
      - ``aws_access_key_id`` / ``aws_secret_access_key`` / ``aws_session_token``
      - ``provider``: optional explicit Bedrock provider for the model
    Any remaining params (``temperature``, ``max_tokens`` ...) are forwarded to
    the underlying model.
    """

    def _init_llm(self) -> BaseChatModel:
        params = dict(self.config.additional_params or {})
        endpoint_type = str(params.pop("endpoint_type", "") or "runtime").lower()
        region_name = params.pop("region_name", None) or _region_from_bedrock_url(self.config.api_base_url)

        if endpoint_type == "mantle":
            # OpenAI-compatible endpoint, served by the bedrock-mantle endpoint.
            base_url = self.config.api_base_url
            if not base_url and region_name:
                base_url = f"https://bedrock-mantle.{region_name}.api.aws/v1"
            return BaseChatOpenAI(
                model=self.config.model_name,
                api_key=self.config.api_key or 'Empty',
                base_url=base_url,
                stream_usage=True,
                **params,
            )

        # default: native bedrock-runtime endpoint via the Converse API
        from langchain_aws import ChatBedrockConverse

        aws_access_key_id = params.pop("aws_access_key_id", None)
        aws_secret_access_key = params.pop("aws_secret_access_key", None)
        aws_session_token = params.pop("aws_session_token", None)
        provider = params.pop("provider", None)

        kwargs: Dict[str, Any] = {}
        if region_name:
            kwargs["region_name"] = region_name
        # api_domain may hold a custom/private bedrock-runtime endpoint url
        if self.config.api_base_url and "bedrock-mantle" not in self.config.api_base_url:
            kwargs["endpoint_url"] = self.config.api_base_url
        if aws_access_key_id and aws_secret_access_key:
            kwargs["aws_access_key_id"] = aws_access_key_id
            kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                kwargs["aws_session_token"] = aws_session_token
        if provider:
            kwargs["provider"] = provider

        return ChatBedrockConverse(
            model=self.config.model_name,
            **kwargs,
            **params,
        )


class LLMFactory:
    """Large Language Model Factory Class"""

    _llm_types: Dict[str, Type[BaseLLM]] = {
        "openai": OpenAILLM,
        "tongyi": OpenAILLM,
        "vllm": OpenAIvLLM,
        "azure": OpenAIAzureLLM,
        "bedrock": BedrockLLM,
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


async def get_default_config(custom_model_id: Optional[int] = None) -> LLMConfig:
    with Session(engine) as session:
        db_model: AiModelDetail | None = None
        if custom_model_id:
            db_model = session.get(AiModelDetail, custom_model_id)
        if not db_model:
            db_model = session.exec(
                select(AiModelDetail).where(AiModelDetail.default_model == True)
            ).first()
        if not db_model:
            raise Exception("The system default model has not been set")

        additional_params = {}
        if db_model.config:
            try:
                config_raw = json.loads(db_model.config)
                additional_params = {item["key"]: prepare_model_arg(item.get('val')) for item in config_raw if
                                     "key" in item and "val" in item}
            except Exception:
                pass
        if not db_model.api_domain.startswith("http"):
            db_model.api_domain = await sqlbot_decrypt(db_model.api_domain)
            if db_model.api_key:
                db_model.api_key = await sqlbot_decrypt(db_model.api_key)

        # 构造 LLMConfig
        return LLMConfig(
            model_id=db_model.id,
            model_type=get_model_type_by_protocol(db_model.protocol),
            model_name=db_model.base_model,
            api_key=db_model.api_key,
            api_base_url=db_model.api_domain,
            additional_params=additional_params,
        )
