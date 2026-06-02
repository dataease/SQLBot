import json
from typing import List, Union

from fastapi import APIRouter, Path, Query, Body
from fastapi.responses import StreamingResponse
from sqlmodel import func, select, update, delete

from apps.ai_model.model_factory import LLMConfig, LLMFactory
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.crud.aimodel_manage import get_ai_model_list_by_workspace
from apps.system.models.system_model import AiModelDetail, AiModelWorkspaceMapping, AiModelBrief
from apps.system.schemas.ai_model_schema import AiModelConfigItem, AiModelCreator, AiModelEditor, AiModelGridItem
from apps.system.schemas.permission import SqlbotPermission, require_permissions
from common.core.deps import SessionDep, Trans, CurrentUser
from common.utils.crypto import sqlbot_decrypt
from common.utils.time import get_timestamp
from common.utils.utils import SQLBotLogUtil, prepare_model_arg

router = APIRouter(tags=["system_model"], prefix="/system/aimodel")
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log


@router.post("/status", include_in_schema=False)
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def check_llm(info: AiModelCreator, trans: Trans):
    async def generate():
        try:
            additional_params = {item.key: prepare_model_arg(item.val) for item in info.config_list if
                                 item.key and item.val}
            config = LLMConfig(
                model_type="openai" if info.protocol == 1 else "vllm",
                model_name=info.base_model,
                api_key=info.api_key,
                api_base_url=info.api_domain,
                additional_params=additional_params,
            )
            llm_instance = LLMFactory.create_llm(config)
            async for chunk in llm_instance.llm.astream("1+1=?"):
                SQLBotLogUtil.info(chunk)
                if chunk and isinstance(chunk, str):
                    yield json.dumps({"content": chunk}) + "\n"
                if chunk and isinstance(chunk, dict) and chunk.content:
                    yield json.dumps({"content": chunk.content}) + "\n"

        except Exception as e:
            SQLBotLogUtil.error(f"Error checking LLM: {e}")
            error_msg = trans('i18n_llm.validate_error', msg=str(e))
            yield json.dumps({"error": error_msg}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@router.get("/default", include_in_schema=False)
async def check_default(session: SessionDep, trans: Trans):
    db_model = session.exec(
        select(AiModelDetail).where(AiModelDetail.default_model == True)
    ).first()
    if not db_model:
        raise Exception(trans('i18n_llm.miss_default'))


@router.put("/default/{id}", summary=f"{PLACEHOLDER_PREFIX}system_model_default",
            description=f"{PLACEHOLDER_PREFIX}system_model_default")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.AI_MODEL, resource_id_expr="id"))
async def set_default(session: SessionDep, id: int = Path(description="ID")):
    db_model = session.get(AiModelDetail, id)
    if not db_model:
        raise ValueError(f"AiModelDetail with id {id} not found")
    if db_model.default_model:
        return

    try:
        session.exec(
            update(AiModelDetail).values(default_model=False)
        )
        db_model.default_model = True
        session.add(db_model)
        session.commit()
    except Exception as e:
        session.rollback()
        raise e


@router.get("", response_model=list[AiModelGridItem], summary=f"{PLACEHOLDER_PREFIX}system_model_grid",
            description=f"{PLACEHOLDER_PREFIX}system_model_grid")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def query(
        session: SessionDep,
        keyword: Union[str, None] = Query(default=None, max_length=255, description=f"{PLACEHOLDER_PREFIX}keyword")
):
    statement = select(AiModelDetail.id,
                       AiModelDetail.name,
                       AiModelDetail.model_type,
                       AiModelDetail.base_model,
                       AiModelDetail.supplier,
                       AiModelDetail.protocol,
                       AiModelDetail.default_model)
    if keyword is not None:
        statement = statement.where(AiModelDetail.name.like(f"%{keyword}%"))
    statement = statement.order_by(AiModelDetail.default_model.desc(), AiModelDetail.name, AiModelDetail.create_time)
    items = session.exec(statement).all()
    return items


@router.get("/{id}", response_model=AiModelEditor, summary=f"{PLACEHOLDER_PREFIX}system_model_query",
            description=f"{PLACEHOLDER_PREFIX}system_model_query")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def get_model_by_id(
        session: SessionDep,
        id: int = Path(description="ID")
):
    db_model = session.get(AiModelDetail, id)
    if not db_model:
        raise ValueError(f"AiModelDetail with id {id} not found")

    config_list: List[AiModelConfigItem] = []
    if db_model.config:
        try:
            raw = json.loads(db_model.config)
            config_list = [AiModelConfigItem(**item) for item in raw]
        except Exception:
            pass
    try:
        if db_model.api_key:
            db_model.api_key = await sqlbot_decrypt(db_model.api_key)
        if db_model.api_domain:
            db_model.api_domain = await sqlbot_decrypt(db_model.api_domain)
    except Exception:
        pass
    data = AiModelDetail.model_validate(db_model).model_dump(exclude_unset=True)
    data.pop("config", None)
    data["config_list"] = config_list
    return AiModelEditor(**data)


@router.post("", summary=f"{PLACEHOLDER_PREFIX}system_model_create",
             description=f"{PLACEHOLDER_PREFIX}system_model_create")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.CREATE, module=OperationModules.AI_MODEL, result_id_expr="id"))
async def add_model(
        session: SessionDep,
        creator: AiModelCreator
):
    data = creator.model_dump(exclude_unset=True)
    data["config"] = json.dumps([item.model_dump(exclude_unset=True) for item in creator.config_list])
    data.pop("config_list", None)
    detail = AiModelDetail.model_validate(data)
    detail.create_time = get_timestamp()
    count = session.exec(select(func.count(AiModelDetail.id))).one()
    if count == 0:
        detail.default_model = True
    session.add(detail)
    session.commit()
    return detail


@router.put("", summary=f"{PLACEHOLDER_PREFIX}system_model_update",
            description=f"{PLACEHOLDER_PREFIX}system_model_update")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(
    LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.AI_MODEL, resource_id_expr="editor.id"))
async def update_model(
        session: SessionDep,
        editor: AiModelEditor
):
    id = int(editor.id)
    data = editor.model_dump(exclude_unset=True)
    data["config"] = json.dumps([item.model_dump(exclude_unset=True) for item in editor.config_list])
    data.pop("config_list", None)
    db_model = session.get(AiModelDetail, id)
    # update_data = AiModelDetail.model_validate(data)
    db_model.sqlmodel_update(data)
    session.add(db_model)
    session.commit()


@router.delete("/{id}", summary=f"{PLACEHOLDER_PREFIX}system_model_del",
               description=f"{PLACEHOLDER_PREFIX}system_model_del")
@require_permissions(permission=SqlbotPermission(role=['admin']))
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.AI_MODEL, resource_id_expr="id"))
async def delete_model(
        session: SessionDep,
        trans: Trans,
        id: int = Path(description="ID")
):
    item = session.get(AiModelDetail, id)
    if item.default_model:
        raise Exception(trans('i18n_llm.delete_default_error', key=item.name))
    session.delete(item)
    session.commit()


@router.get("/{id}/ws_mapping", response_model=List[int], summary=f"{PLACEHOLDER_PREFIX}system_model_query",
            description=f"{PLACEHOLDER_PREFIX}system_model_query")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def get_model_ws_mapping_by_id(
        session: SessionDep,
        id: int = Path(description="ID")
):
    db_model = session.get(AiModelDetail, id)
    if not db_model:
        raise ValueError(f"AiModelDetail with id {id} not found")

    # 根据 ai_model_id 查询关联的 workspace_id 列表
    stmt = (
        select(AiModelWorkspaceMapping.workspace_id)
        .where(AiModelWorkspaceMapping.ai_model_id == id)
        .distinct()
    )
    ws_ids: List[int] = session.exec(stmt).all()

    return ws_ids


@router.put("/{id}/ws_mapping", response_model=List[int], summary=f"{PLACEHOLDER_PREFIX}system_model_query",
            description=f"{PLACEHOLDER_PREFIX}system_model_query")
@require_permissions(permission=SqlbotPermission(role=['admin']))
async def update_model_ws_mapping_by_id(
        session: SessionDep,
        id: int = Path(description="ID"),
        ws_ids: List[int] = Body(description="workspace id list"),
):
    if ws_ids is None:
        ws_ids = []
    # 提前去重
    ws_ids = list(set(ws_ids))

    db_model = session.get(AiModelDetail, id)
    if not db_model:
        raise ValueError(f"AiModelDetail with id {id} not found")

    # 根据 ai_model_id 更新关联的 workspace_id 列表
    # 1. 批量删除旧映射
    session.execute(
        delete(AiModelWorkspaceMapping)
        .where(AiModelWorkspaceMapping.ai_model_id == id)
    )

    # 2. 插入去重后的映射关系
    for ws_id in ws_ids:
        session.add(
            AiModelWorkspaceMapping(ai_model_id=id, workspace_id=ws_id)
        )

    session.commit()

    return ws_ids


@router.get("/list_by_ws", response_model=AiModelBrief, summary=f"{PLACEHOLDER_PREFIX}system_model_query",
            description=f"{PLACEHOLDER_PREFIX}system_model_query")
@require_permissions(permission=SqlbotPermission(role=['ws_admin']))
async def get_model_by_ws(
        session: SessionDep,
        current_user: CurrentUser
):
    return get_ai_model_list_by_workspace(session, current_user.workspace_id)
