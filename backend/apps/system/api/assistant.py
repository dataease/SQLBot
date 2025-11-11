import json
import os
from datetime import timedelta
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlbot_xpack.file_utils import SQLBotFileUtils
from sqlmodel import select

from apps.system.crud.assistant import get_assistant_info
from apps.system.crud.assistant_manage import dynamic_upgrade_cors, save
from apps.system.models.system_model import AssistantModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.system_schema import AssistantBase, AssistantDTO, AssistantUiSchema, AssistantValidator
from common.core.config import settings
from common.core.deps import SessionDep, Trans
from common.core.security import create_access_token
from common.core.sqlbot_cache import clear_cache
from common.utils.utils import get_origin_from_referer

router = APIRouter(tags=["system/assistant"], prefix="/system/assistant")


@router.get("/info/{id}")
async def info(request: Request, response: Response, session: SessionDep, trans: Trans, id: int) -> AssistantModel:
    if not id:
        raise Exception('miss assistant id')
    db_model = await get_assistant_info(session=session, assistant_id=id)
    if not db_model:
        raise RuntimeError(f"assistant application not exist")
    db_model = AssistantModel.model_validate(db_model)
    response.headers["Access-Control-Allow-Origin"] = db_model.domain
    origin = request.headers.get("origin") or get_origin_from_referer(request)
    if not origin:
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    origin = origin.rstrip('/')
    if origin != db_model.domain:
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    return db_model


@router.get("/app/{appId}")
async def getApp(request: Request, response: Response, session: SessionDep, trans: Trans, appId: str) -> AssistantModel:
    if not appId:
        raise Exception('miss assistant appId')
    db_model = session.exec(select(AssistantModel).where(AssistantModel.app_id == appId)).first()
    if not db_model:
        raise RuntimeError(f"assistant application not exist")
    db_model = AssistantModel.model_validate(db_model)
    response.headers["Access-Control-Allow-Origin"] = db_model.domain
    origin = request.headers.get("origin") or get_origin_from_referer(request)
    if not origin:
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    origin = origin.rstrip('/')
    if origin != db_model.domain:
        raise RuntimeError(trans('i18n_embedded.invalid_origin', origin=origin or ''))
    return db_model


@router.get("/validator", response_model=AssistantValidator)
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


@router.get('/picture/{file_id}')
async def picture(file_id: str):
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


@router.patch('/ui')
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
                SQLBotFileUtils.check_file(file=file, file_types=[".jpg", ".jpeg", ".png", ".svg"],
                                           limit_file_size=(10 * 1024 * 1024))
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


@clear_cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_INFO, keyExpression="id")
async def clear_ui_cache(id: int):
    pass


@router.get("", response_model=list[AssistantModel])
async def query(session: SessionDep):
    list_result = session.exec(select(AssistantModel).where(AssistantModel.type != 4).order_by(AssistantModel.name,
                                                                                               AssistantModel.create_time)).all()
    return list_result


@router.get("/advanced_application", response_model=list[AssistantModel])
async def query_advanced_application(session: SessionDep):
    list_result = session.exec(select(AssistantModel).where(AssistantModel.type == 1).order_by(AssistantModel.name,
                                                                                               AssistantModel.create_time)).all()
    return list_result


@router.post("")
async def add(request: Request, session: SessionDep, creator: AssistantBase):
    await save(request, session, creator)


@router.put("")
@clear_cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_INFO, keyExpression="editor.id")
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


@router.get("/{id}", response_model=AssistantModel)
async def get_one(session: SessionDep, id: int):
    db_model = await get_assistant_info(session=session, assistant_id=id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    db_model = AssistantModel.model_validate(db_model)
    return db_model


@router.delete("/{id}")
@clear_cache(namespace=CacheNamespace.EMBEDDED_INFO, cacheName=CacheName.ASSISTANT_INFO, keyExpression="id")
async def delete(request: Request, session: SessionDep, id: int):
    db_model = session.get(AssistantModel, id)
    if not db_model:
        raise ValueError(f"AssistantModel with id {id} not found")
    session.delete(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)
