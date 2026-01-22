import json
import os
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, Path, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlbot_xpack.file_utils import SQLBotFileUtils
from sqlmodel import select

from apps.datasource.models.datasource import CoreDatasource
from apps.db.constant import DB
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from apps.system.crud.assistant import AssistantOutDs, AssistantOutDsFactory, get_assistant_info
from apps.system.crud.assistant_manage import dynamic_upgrade_cors, save
from apps.system.models.system_model import AssistantModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.system_schema import AssistantBase, AssistantDTO, AssistantUiSchema, AssistantValidator
from common.core.config import settings
from common.core.deps import CurrentAssistant, SessionDep, Trans, CurrentUser
from common.core.security import create_access_token
from common.core.sqlbot_cache import clear_cache
from common.utils.utils import get_origin_from_referer, origin_match_domain

router = APIRouter(tags=["system_assistant"], prefix="/system/assistant")
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log


@router.get("/info/{id}", include_in_schema=False)
async def info(request: Request, response: Response, session: SessionDep, trans: Trans, id: int) -> AssistantModel:
    if not id:
        raise Exception('miss assistant id')
    db_model = await get_assistant_info(session=session, assistant_id=id)
    if not db_model:
        raise RuntimeError(f"assistant application not exist")
    db_model = AssistantModel.model_validate(db_model)
    
    origin = request.headers.get("origin") or get_origin_from_referer(request)
    if not origin:
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    origin = origin.rstrip('/')
    if not origin_match_domain(origin, db_model.domain):
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    
    response.headers["Access-Control-Allow-Origin"] = origin
    return db_model


@router.get("/app/{appId}", include_in_schema=False)
async def getApp(request: Request, response: Response, session: SessionDep, trans: Trans, appId: str) -> AssistantModel:
    if not appId:
        raise Exception('miss assistant appId')
    db_model = session.exec(select(AssistantModel).where(AssistantModel.app_id == appId)).first()
    if not db_model:
        raise RuntimeError(f"assistant application not exist")
    db_model = AssistantModel.model_validate(db_model)
    origin = request.headers.get("origin") or get_origin_from_referer(request)
    if not origin:
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    origin = origin.rstrip('/')
    if not origin_match_domain(origin, db_model.domain):
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    
    response.headers["Access-Control-Allow-Origin"] = origin
    return db_model


@router.get("/validator", response_model=AssistantValidator, include_in_schema=False)
async def validator(session: SessionDep, id: int, virtual: Optional[int] = Query(None)):
    if not id:
        raise Exception('miss assistant id')

    db_model = await get_assistant_info(session=session, assistant_id=id)
    if not db_model:
        return AssistantValidator()
    db_model = AssistantModel.model_validate(db_model)
    assistant_oid = 1
    if (db_model.type == 0):
        configuration = db_model.configuration
        config_obj = json.loads(configuration) if configuration else {}
        assistant_oid = config_obj.get('oid', 1)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    assistantDict = {
        "id": virtual, "account": 'sqlbot-inner-assistant', "oid": assistant_oid, "assistant_id": id
    }
    access_token = create_access_token(
        assistantDict, expires_delta=access_token_expires
    )
    return AssistantValidator(True, True, True, access_token)


@router.get('/picture/{file_id}', summary=f"{PLACEHOLDER_PREFIX}assistant_picture_api", description=f"{PLACEHOLDER_PREFIX}assistant_picture_api")
async def picture(file_id: str = Path(description="file_id")):
    file_path = SQLBotFileUtils.get_file_path(file_id=file_id)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    if file_id.lower().endswith(".svg"):
        media_type = "image/svg+xml"
    else:
        media_type = "image/jpeg"

    def iterfile():
        with open(file_path, mode="rb") as f:
            yield from f

    return StreamingResponse(iterfile(), media_type=media_type)


@router.patch('/ui', summary=f"{PLACEHOLDER_PREFIX}assistant_ui_api", description=f"{PLACEHOLDER_PREFIX}assistant_ui_api")
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.APPLICATION, result_id_expr="id"))
async def ui(session: SessionDep, data: str = Form(), files: List[UploadFile] = []):
    json_data = json.loads(data)
    uiSchema = AssistantUiSchema(**json_data)
    id = uiSchema.id
    db_model = session.get(AssistantModel, id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    configuration = db_model.configuration
    config_obj = json.loads(configuration) if configuration else {}

    ui_schema_dict = uiSchema.model_dump(exclude_none=True, exclude_unset=True)
    if files:
        for file in files:
            origin_file_name = file.filename
            file_name, flag_name = SQLBotFileUtils.split_filename_and_flag(origin_file_name)
            file.filename = file_name
            if flag_name == 'logo' or flag_name == 'float_icon':
                try:
                    SQLBotFileUtils.check_file(file=file, file_types=[".jpg", ".png", ".svg"],
                                               limit_file_size=(10 * 1024 * 1024))
                except ValueError as e:
                    error_msg = str(e)
                    if '文件大小超过限制' in error_msg:
                        raise ValueError(f"文件大小超过限制（最大 10 M）")
                    else:
                        raise e
                if config_obj.get(flag_name):
                    SQLBotFileUtils.delete_file(config_obj.get(flag_name))
                file_id = await SQLBotFileUtils.upload(file)
                ui_schema_dict[flag_name] = file_id
            else:
                raise ValueError(f"Unsupported file flag: {flag_name}")

    for flag_name in ['logo', 'float_icon']:
        file_val = config_obj.get(flag_name)
        if file_val and not ui_schema_dict.get(flag_name):
            config_obj[flag_name] = None
            SQLBotFileUtils.delete_file(file_val)

    for attr, value in ui_schema_dict.items():
        if attr != 'id' and not attr.startswith("__"):
            config_obj[attr] = value

    db_model.configuration = json.dumps(config_obj, ensure_ascii=False)
    session.add(db_model)
    session.commit()
    await clear_ui_cache(db_model.id)
    return db_model


@clear_cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_INFO, keyExpression="id")
async def clear_ui_cache(id: int):
    pass

@router.get("/ds", include_in_schema=False, response_model=list[dict])
async def ds(session: SessionDep, current_assistant: CurrentAssistant):
    if current_assistant.type == 0:
        online = current_assistant.online
        configuration = current_assistant.configuration
        config: dict[any] = json.loads(configuration)
        oid: int = int(config['oid'])
        stmt = select(CoreDatasource.id, CoreDatasource.name, CoreDatasource.description, CoreDatasource.type, CoreDatasource.type_name, CoreDatasource.num).where(
            CoreDatasource.oid == oid)
        if not online:
            public_list: list[int] = config.get('public_list') or None
            if public_list:
                stmt = stmt.where(CoreDatasource.id.in_(public_list))
            else:
                return []
        db_ds_list = session.exec(stmt)
        return [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description,
                "type": ds.type,
                "type_name": ds.type_name,
                "num": ds.num,
            }
            for ds in db_ds_list]
    if current_assistant.type == 1:
        out_ds_instance: AssistantOutDs = AssistantOutDsFactory.get_instance(current_assistant)
        return [
            {
                "id": ds.id,
                "name": ds.name,
                "description": ds.description or ds.comment,
                "type": ds.type,
                "type_name": get_db_type(ds.type),
                "num": len(ds.tables) if ds.tables else 0,
            }
            for ds in out_ds_instance.ds_list
            if get_db_type(ds.type)
        ]
        
    return None

def get_db_type(type):
    try:
        db = DB.get_db(type)
        return db.db_name
    except Exception:
        return None


@router.get("", response_model=list[AssistantModel], summary=f"{PLACEHOLDER_PREFIX}assistant_grid_api", description=f"{PLACEHOLDER_PREFIX}assistant_grid_api")
async def query(session: SessionDep, current_user: CurrentUser):
    list_result = session.exec(select(AssistantModel).where(AssistantModel.oid == current_user.oid, AssistantModel.type != 4).order_by(AssistantModel.name,
                                                                                               AssistantModel.create_time)).all()
    return list_result


@router.get("/advanced_application", response_model=list[AssistantModel], include_in_schema=False)
async def query_advanced_application(session: SessionDep):
    list_result = session.exec(select(AssistantModel).where(AssistantModel.type == 1).order_by(AssistantModel.name,
                                                                                               AssistantModel.create_time)).all()
    return list_result


@router.post("", summary=f"{PLACEHOLDER_PREFIX}assistant_create_api", description=f"{PLACEHOLDER_PREFIX}assistant_create_api")
@system_log(LogConfig(operation_type=OperationType.CREATE, module=OperationModules.APPLICATION, result_id_expr="id"))
async def add(request: Request, session: SessionDep, current_user: CurrentUser, creator: AssistantBase):
    oid = current_user.oid if creator.type != 4 else 1
    return await save(request, session, creator, oid)


@router.put("", summary=f"{PLACEHOLDER_PREFIX}assistant_update_api", description=f"{PLACEHOLDER_PREFIX}assistant_update_api")
@clear_cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_INFO, keyExpression="editor.id")
@system_log(LogConfig(operation_type=OperationType.UPDATE, module=OperationModules.APPLICATION, resource_id_expr="editor.id"))
async def update(request: Request, session: SessionDep, editor: AssistantDTO):
    id = editor.id
    db_model = session.get(AssistantModel, id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    update_data = AssistantModel.model_validate(editor)
    db_model.sqlmodel_update(update_data)
    session.add(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)


@router.get("/{id}", response_model=AssistantModel, summary=f"{PLACEHOLDER_PREFIX}assistant_query_api", description=f"{PLACEHOLDER_PREFIX}assistant_query_api")
async def get_one(session: SessionDep, id: int = Path(description="ID")):
    db_model = await get_assistant_info(session=session, assistant_id=id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    db_model = AssistantModel.model_validate(db_model)
    return db_model


@router.delete("/{id}", summary=f"{PLACEHOLDER_PREFIX}assistant_del_api", description=f"{PLACEHOLDER_PREFIX}assistant_del_api")
@clear_cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_INFO, keyExpression="id")
@system_log(LogConfig(operation_type=OperationType.DELETE, module=OperationModules.APPLICATION, resource_id_expr="id"))
async def delete(request: Request, session: SessionDep, id: int = Path(description="ID")):
    db_model = session.get(AssistantModel, id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    session.delete(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)

