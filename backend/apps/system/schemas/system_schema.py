import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.schemas import BaseCreatorDTO

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*@"
    r"([a-zA-Z0-9]+(-[a-zA-Z0-9]+)*\.)+"
    r"[a-zA-Z]{2,}$"
)
PWD_REGEX = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)"
    r"(?=.*[~!@#$%^&*()_+\-={}|:\"<>?`\[\];',./])"
    r"[A-Za-z\d~!@#$%^&*()_+\-={}|:\"<>?`\[\];',./]{8,20}$"
)


class UserStatus(BaseCreatorDTO):
    status: int = Field(default=1, description=f"{PLACEHOLDER_PREFIX}status")


class UserLanguage(BaseModel):
    language: str = Field(description=f"{PLACEHOLDER_PREFIX}language")


class BaseUser(BaseModel):
    account: str = Field(min_length=1, max_length=100, description="用户账号")
    oid: int


class BaseUserDTO(BaseUser, BaseCreatorDTO):
    language: str = Field(pattern=r"^(zh-CN|en|ko-KR)$", default="zh-CN", description="用户语言")
    password: str
    status: int = 1
    origin: int = 0
    name: str

    def to_dict(self):
        return {
            "id": self.id,
            "account": self.account,
            "oid": self.oid
        }

    @field_validator("language")
    def validate_language(cls, lang: str) -> str:
        if not re.fullmatch(r"^(zh-CN|en|ko-KR)$", lang):
            raise ValueError("Language must be 'zh-CN', 'en', or 'ko-KR'")
        return lang


class UserCreator(BaseUser):
    name: str = Field(min_length=1, max_length=100, description=f"{PLACEHOLDER_PREFIX}user_name")
    email: str = Field(min_length=1, max_length=100, description=f"{PLACEHOLDER_PREFIX}user_email")
    status: int = Field(default=1, description=f"{PLACEHOLDER_PREFIX}status")
    origin: Optional[int] = Field(default=0, description=f"{PLACEHOLDER_PREFIX}origin")
    oid_list: Optional[list[int]] = Field(default=None, description=f"{PLACEHOLDER_PREFIX}oid")

    """ @field_validator("email")
    def validate_email(cls, lang: str) -> str:
        if not re.fullmatch(EMAIL_REGEX, lang):
            raise ValueError("Email format is invalid!")
        return lang """


class UserEditor(UserCreator, BaseCreatorDTO):
    pass


class UserGrid(UserEditor):
    create_time: int = Field(description=f"{PLACEHOLDER_PREFIX}create_time")
    language: str = Field(default="zh-CN" ,description=f"{PLACEHOLDER_PREFIX}language") 
    # space_name: Optional[str] = None
    # origin: str = ''


class PwdEditor(BaseModel):
    pwd: str = Field(description=f"{PLACEHOLDER_PREFIX}origin_pwd")
    new_pwd: str = Field(description=f"{PLACEHOLDER_PREFIX}new_pwd")


class UserWsBase(BaseModel):
    uid_list: list[int] = Field(description=f"{PLACEHOLDER_PREFIX}uid")
    oid: Optional[int] = Field(default=None, description=f"{PLACEHOLDER_PREFIX}oid")


class UserWsDTO(UserWsBase):
    weight: Optional[int] = Field(default=0, description=f"{PLACEHOLDER_PREFIX}weight")


class UserWsEditor(BaseModel):
    uid: int = Field(description=f"{PLACEHOLDER_PREFIX}uid")
    oid: int = Field(description=f"{PLACEHOLDER_PREFIX}oid")
    weight: int = Field(default=0, description=f"{PLACEHOLDER_PREFIX}weight")


class UserInfoDTO(UserEditor):
    language: str = "zh-CN"
    weight: int = 0
    isAdmin: bool = False


class AssistantBase(BaseModel):
    name: str = Field(description=f"{PLACEHOLDER_PREFIX}model_name")
    domain: str = Field(description=f"{PLACEHOLDER_PREFIX}assistant_domain")
    type: int = Field(default=0, description=f"{PLACEHOLDER_PREFIX}assistant_type")  # 0普通小助手 1高级 4页面嵌入
    configuration: Optional[str] = Field(default=None, description=f"{PLACEHOLDER_PREFIX}assistant_configuration")
    description: Optional[str] = Field(default=None, description=f"{PLACEHOLDER_PREFIX}assistant_description")


class AssistantDTO(AssistantBase, BaseCreatorDTO):
    pass


class AssistantHeader(AssistantDTO):
    unique: Optional[str] = None
    certificate: Optional[str] = None
    online: bool = False
    request_origin: Optional[str] = None


class AssistantValidator(BaseModel):
    valid: bool = False
    id_match: bool = False
    domain_match: bool = False
    token: Optional[str] = None

    def __init__(
            self,
            valid: bool = False,
            id_match: bool = False,
            domain_match: bool = False,
            token: Optional[str] = None,
            **kwargs
    ):
        super().__init__(
            valid=valid,
            id_match=id_match,
            domain_match=domain_match,
            token=token,
            **kwargs
        )


class WorkspaceUser(UserEditor):
    weight: int
    create_time: int


class UserWs(BaseCreatorDTO):
    name: str = Field(description="user_name")


class UserWsOption(UserWs):
    account: str = Field(description="user_account")


class AssistantFieldSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    type: Optional[str] = None
    comment: Optional[str] = None


class AssistantTableSchema(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    comment: Optional[str] = None
    rule: Optional[str] = None
    sql: Optional[str] = None
    fields: Optional[list[AssistantFieldSchema]] = None


class AssistantOutDsBase(BaseModel):
    id: Optional[int] = None
    name: str
    type: Optional[str] = None
    type_name: Optional[str] = None
    comment: Optional[str] = None
    description: Optional[str] = None
    configuration: Optional[str] = None


class AssistantOutDsSchema(AssistantOutDsBase):
    host: Optional[str] = None
    port: Optional[int] = None
    dataBase: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    db_schema: Optional[str] = None
    extraParams: Optional[str] = None
    tables: Optional[list[AssistantTableSchema]] = None


class AssistantUiSchema(BaseCreatorDTO):
    theme: Optional[str] = None
    header_font_color: Optional[str] = None
    logo: Optional[str] = None
    float_icon: Optional[str] = None
    float_icon_drag: Optional[bool] = False
    x_type: Optional[str] = 'right'
    x_val: Optional[int] = 0
    y_type: Optional[str] = 'bottom'
    y_val: Optional[int] = 33
    name: Optional[str] = None
    welcome: Optional[str] = None
    welcome_desc: Optional[str] = None

class ApikeyStatus(BaseModel):
    id: int = Field(description=f"{PLACEHOLDER_PREFIX}id")
    status: bool = Field(description=f"{PLACEHOLDER_PREFIX}status")

class ApikeyGridItem(BaseCreatorDTO):
    access_key: str = Field(description=f"Access Key")
    secret_key: str = Field(description=f"Secret Key")
    status: bool = Field(description=f"{PLACEHOLDER_PREFIX}status")
    create_time: int = Field(description=f"{PLACEHOLDER_PREFIX}create_time")