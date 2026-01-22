import secrets
import urllib.parse
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    PostgresDsn,
    computed_field,
    field_validator
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )
    PROJECT_NAME: str = "SQLBot"
    #CONTEXT_PATH: str = "/sqlbot"
    CONTEXT_PATH: str = ""
    API_V1_STR: str = CONTEXT_PATH + "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    FRONTEND_HOST: str = "http://localhost:5173"

    BACKEND_CORS_ORIGINS: Annotated[
        list[AnyUrl] | str, BeforeValidator(parse_cors)
    ] = []

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    POSTGRES_SERVER: str = 'localhost'
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = 'root'
    POSTGRES_PASSWORD: str = "Password123@pg"
    POSTGRES_DB: str = "sqlbot"
    SQLBOT_DB_URL: str = ''
    # SQLBOT_DB_URL: str = 'mysql+pymysql://root:Password123%40mysql@127.0.0.1:3306/sqlbot'

    TOKEN_KEY: str = "X-SQLBOT-TOKEN"
    DEFAULT_PWD: str = "SQLBot@123456"
    ASSISTANT_TOKEN_KEY: str = "X-SQLBOT-ASSISTANT-TOKEN"

    CACHE_TYPE: Literal["redis", "memory", "None"] = "memory"
    CACHE_REDIS_URL: str | None = None  # Redis URL, e.g., "redis://[[username]:[password]]@localhost:6379/0"

    LOG_LEVEL: str = "INFO"  # DEBUG, INFO, WARNING, ERROR
    LOG_DIR: str = "logs"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s:%(lineno)d - %(message)s"
    SQL_DEBUG: bool = False
    BASE_DIR: str = "/opt/sqlbot"
    SCRIPT_DIR: str = f"{BASE_DIR}/scripts"
    UPLOAD_DIR: str = "/opt/sqlbot/data/file"
    SQLBOT_KEY_EXPIRED: int = 100  # License key expiration timestamp, 0 means no expiration

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn | str:
        if self.SQLBOT_DB_URL:
            return self.SQLBOT_DB_URL
        # return MultiHostUrl.build(
        #     scheme="postgresql+psycopg",
        #     username=urllib.parse.quote(self.POSTGRES_USER),
        #     password=urllib.parse.quote(self.POSTGRES_PASSWORD),
        #     host=self.POSTGRES_SERVER,
        #     port=self.POSTGRES_PORT,
        #     path=self.POSTGRES_DB,
        # )
        return f"postgresql+psycopg://{urllib.parse.quote(self.POSTGRES_USER)}:{urllib.parse.quote(self.POSTGRES_PASSWORD)}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    MCP_IMAGE_PATH: str = '/opt/sqlbot/images'
    EXCEL_PATH: str = '/opt/sqlbot/data/excel'
    MCP_IMAGE_HOST: str = 'http://localhost:3000'
    SERVER_IMAGE_HOST: str = 'http://YOUR_SERVE_IP:MCP_PORT/images/'
    SERVER_IMAGE_TIMEOUT: int = 15

    LOCAL_MODEL_PATH: str = '/opt/sqlbot/models'
    DEFAULT_EMBEDDING_MODEL: str = 'shibing624/text2vec-base-chinese'
    EMBEDDING_ENABLED: bool = True
    EMBEDDING_DEFAULT_SIMILARITY: float = 0.4
    EMBEDDING_TERMINOLOGY_SIMILARITY: float = EMBEDDING_DEFAULT_SIMILARITY
    EMBEDDING_DATA_TRAINING_SIMILARITY: float = EMBEDDING_DEFAULT_SIMILARITY
    EMBEDDING_DEFAULT_TOP_COUNT: int = 5
    EMBEDDING_TERMINOLOGY_TOP_COUNT: int = EMBEDDING_DEFAULT_TOP_COUNT
    EMBEDDING_DATA_TRAINING_TOP_COUNT: int = EMBEDDING_DEFAULT_TOP_COUNT

    # 是否启用SQL查询行数限制，默认值，可被参数配置覆盖
    GENERATE_SQL_QUERY_LIMIT_ENABLED: bool = True

    PARSE_REASONING_BLOCK_ENABLED: bool = True
    DEFAULT_REASONING_CONTENT_START: str = '<think>'
    DEFAULT_REASONING_CONTENT_END: str = '</think>'

    PG_POOL_SIZE: int = 20
    PG_MAX_OVERFLOW: int = 30
    PG_POOL_RECYCLE: int = 3600
    PG_POOL_PRE_PING: bool = True

    TABLE_EMBEDDING_ENABLED: bool = True
    TABLE_EMBEDDING_COUNT: int = 10
    DS_EMBEDDING_COUNT: int = 10

    ORACLE_CLIENT_PATH: str = '/opt/sqlbot/db_client/oracle_instant_client'

    @field_validator('SQL_DEBUG',
                     'EMBEDDING_ENABLED',
                     'GENERATE_SQL_QUERY_LIMIT_ENABLED',
                     'PARSE_REASONING_BLOCK_ENABLED',
                     'PG_POOL_PRE_PING',
                     'TABLE_EMBEDDING_ENABLED',
                     mode='before')
    @classmethod
    def lowercase_bool(cls, v: Any) -> Any:
        """将字符串形式的布尔值转换为Python布尔值"""
        if isinstance(v, str):
            v_lower = v.lower().strip()
            if v_lower == 'true':
                return True
            elif v_lower == 'false':
                return False
        return v


settings = Settings()  # type: ignore
