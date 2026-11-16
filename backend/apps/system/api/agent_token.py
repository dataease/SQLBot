"""Self-service management of SQLBot MCP agent tokens.

Every route acts on the caller's own tokens only. The plain token is returned
once, by ``POST``; listings expose the prefix only.
"""


from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_serializer

from apps.system.crud import agent_token_manage as tokens
from apps.system.models.system_model import AgentTokenModel
from common.audit.models.log_model import OperationModules, OperationType
from common.audit.schemas.logger_decorator import LogConfig, system_log
from common.core.deps import CurrentUser, SessionDep, Trans

router = APIRouter(tags=["system_agent_token"], prefix="/system/agent-token", include_in_schema=False)


class AgentTokenCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    # ``None`` follows the owner's datasource permissions.
    datasource_ids: list[int] | None = None


class AgentTokenStatus(BaseModel):
    id: int
    status: bool


class AgentTokenItem(BaseModel):
    id: int
    name: str
    token_prefix: str
    status: bool
    oid: int
    datasource_ids: list[str] | None = None
    create_time: int
    last_used_time: int | None = None
    last_used_ip: str | None = None

    @field_serializer("id", "oid")
    def big_int_to_str(self, v: int) -> str:
        return str(v)

    @classmethod
    def of(cls, model: AgentTokenModel) -> "AgentTokenItem":
        scope = tokens.load_ds_ids(model.allowed_ds_ids)
        return cls(
            id=model.id, name=model.name, token_prefix=f"{tokens.TOKEN_SCHEME}{model.token_prefix}",
            status=model.status, oid=model.oid,
            datasource_ids=None if scope is None else sorted(str(i) for i in scope),
            create_time=model.create_time, last_used_time=model.last_used_time, last_used_ip=model.last_used_ip,
        )


class AgentTokenCreated(AgentTokenItem):
    # Shown once; the server keeps only its digest.
    token: str


def _raise(trans: Trans, error: tokens.AgentTokenError):
    status = 404 if error.key == "not_found" else 400
    raise HTTPException(status_code=status, detail=trans(f"i18n_agent_token.{error.key}", **error.params))


@router.get("")
async def list_agent_tokens(session: SessionDep, current_user: CurrentUser) -> list[AgentTokenItem]:
    return [AgentTokenItem.of(m) for m in tokens.list_tokens(session, current_user.id)]


@router.post("")
@system_log(LogConfig(operation_type=OperationType.CREATE, module=OperationModules.AGENT_TOKEN,
                      result_id_expr="id", save_on_success_only=True))
async def create_agent_token(session: SessionDep, current_user: CurrentUser, trans: Trans,
                             body: AgentTokenCreate) -> AgentTokenCreated:
    try:
        issued = tokens.create_token(session, uid=current_user.id, oid=current_user.oid,
                                     name=body.name, ds_ids=body.datasource_ids)
    except tokens.AgentTokenError as e:
        _raise(trans, e)
    item = AgentTokenItem.of(issued.model)
    return AgentTokenCreated(**item.model_dump(), token=issued.plain)


@router.put("/status")
@system_log(LogConfig(operation_type=OperationType.UPDATE_STATUS, module=OperationModules.AGENT_TOKEN,
                      resource_id_expr="body.id"))
async def update_agent_token_status(session: SessionDep, current_user: CurrentUser, trans: Trans,
                                    body: AgentTokenStatus) -> AgentTokenItem:
    try:
        model = tokens.set_token_status(session, uid=current_user.id, token_id=body.id, status=body.status)
    except tokens.AgentTokenError as e:
        _raise(trans, e)
    return AgentTokenItem.of(model)


@router.delete("/{token_id}")
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.AGENT_TOKEN,
                      resource_id_expr="token_id"))
async def delete_agent_token(session: SessionDep, current_user: CurrentUser, trans: Trans, token_id: int):
    try:
        tokens.delete_token(session, uid=current_user.id, token_id=token_id)
    except tokens.AgentTokenError as e:
        _raise(trans, e)
