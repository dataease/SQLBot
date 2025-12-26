from sqlmodel import Field, SQLModel
from datetime import datetime
from typing import Optional
from enum import Enum
from pydantic import BaseModel

class OperationModules(str, Enum):
    CHAT = "chat"  # 问数
    DATASOURCE = "datasource"  # 数据源
    DASHBOARD = "dashboard"  # 仪表板
    MEMBER = "member"  # 成员
    PERMISSION = "permission"  # 权限
    RULES = "rules"  # q组
    TERMINOLOGY = "terminology"  # 术语
    DATA_TRAINING = "data_training"  # SQL 示例库
    PROMPT_WORDS = "prompt_words"  # 自定义提示词
    USER = "user"  # 用户
    WORKSPACE = "workspace"  # 工作空间
    AI_MODEL = "ai_model"  # AI 模型
    APPLICATION = "application"  # 嵌入式管理 应用
    THEME = "theme"  # 外观配置
    PARAMS_SETTING = "params_setting"  # 参数配置
    API_KEY = "api_key"  # api key
    LOG_SETTING = "log_setting"  # api key

class OperationStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"

class OperationType(str, Enum):
    CREATE = "create"
    DELETE = "delete"
    UPDATE = "update"
    EDIT = "edit"
    LOGIN = "login"
    VIEW = "view"
    EXPORT = "export"
    IMPORT = "import"
    ADD = "add"
    CREATE_OR_UPDATE = "create_or_update"


class SystemLog(SQLModel, table=True):
    __tablename__ = "sys_logs"
    id: Optional[int] = Field(default=None, primary_key=True)
    operation_type: str = Field(default=None)
    operation_detail: str = Field(default=None)
    user_id: Optional[int] = Field(default=None)
    operation_status: str = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    user_agent: Optional[str] = Field(default=None)
    execution_time: int = Field(default=0, description="执行时间(毫秒)")
    error_message: Optional[str] = Field(default=None)
    create_time: datetime = Field(default_factory=datetime.now)
    module: Optional[str] = Field(default=None)
    oid: Optional[int] = Field(default=None)
    resource_id: Optional[str] = Field(default=None)
    request_method: Optional[str] = Field(default=None)
    request_path: Optional[str] = Field(default=None)
    remark: Optional[str] = Field(default=None)
    user_name: Optional[str] = Field(default=None)
    resource_name: Optional[str] = Field(default=None)


class SystemLogInfo(BaseModel):
    id: str = Field(default=None)
    operation_type_name: str = Field(default=None)
    operation_detail_info: str = Field(default=None)
    user_name: str = Field(default=None)
    resource_name: str = Field(default=None)
    operation_status:  str = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    create_time: datetime = Field(default_factory=datetime.now)
    oid_list:  str = Field(default=None)
    remark:  str = Field(default=None)

class SystemLogInfoResult(BaseModel):
    id: str = Field(default=None)
    operation_type_name: str = Field(default=None)
    operation_detail_info: str = Field(default=None)
    user_name: str = Field(default=None)
    resource_name: str = Field(default=None)
    operation_status:  str = Field(default=None)
    operation_status_name:  str = Field(default=None)
    ip_address: Optional[str] = Field(default=None)
    create_time: datetime = Field(default_factory=datetime.now)
    oid_name:  str = Field(default=None)
    oid:  str = Field(default=None)
    error_message:  str = Field(default=None)
    remark:  str = Field(default=None)
