from pydantic import BaseModel, Field, field_validator

from apps.system.models.system_model import AiModelBrief


class WorkspaceModelSettings(BaseModel):
    enable_custom_model: bool = False
    custom_model: str | None = Field(default=None, max_length=255)

    @field_validator("custom_model", mode="before")
    @classmethod
    def normalize_model_id(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool) or not isinstance(value, (int, str)):
            raise ValueError("Invalid model ID")
        value = str(value).strip()
        if not value:
            return None
        if (
            not value.isascii()
            or not value.isdecimal()
            or not 0 < int(value) <= 2**63 - 1
        ):
            raise ValueError("Invalid model ID")
        return str(int(value))


class WorkspaceModelSettingsOut(WorkspaceModelSettings):
    models: list[AiModelBrief]
    model_valid: bool


class ModelImpact(BaseModel):
    workspace_id: str
    workspace_name: str
    uses_default: bool
    assistants: list[str]
    models: list[AiModelBrief]


class ModelImpactResolution(BaseModel):
    workspace_id: int
    # None explicitly acknowledges the unavailable default; retain its old ID.
    custom_model: str | None = None


class ModelMappingUpdate(BaseModel):
    ws_ids: list[str]
    resolutions: list[ModelImpactResolution] = Field(default_factory=list)
