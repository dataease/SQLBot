# Author: Junjun
# Date: 2025/7/1
import json
import traceback
from datetime import timedelta

import jwt
from fastapi import HTTPException, status, APIRouter
from fastapi.responses import StreamingResponse
# from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pydantic import ValidationError
from sqlmodel import select
from starlette.responses import JSONResponse

from apps.chat.api.chat import create_chat
from apps.chat.models.chat_model import ChatMcp, CreateChat, ChatStart, McpQuestion, McpAssistant, ChatQuestion, \
    ChatFinishStep
from apps.chat.task.llm import LLMService
from apps.system.crud.user import authenticate
from apps.system.crud.user import get_db_user
from apps.system.models.system_model import UserWsModel
from apps.system.models.user import UserModel
from apps.system.schemas.system_schema import BaseUserDTO, AssistantHeader
from apps.system.schemas.system_schema import UserInfoDTO
from common.core import security
from common.core.config import settings
from common.core.deps import SessionDep
from common.core.schemas import TokenPayload, XOAuth2PasswordBearer, Token
from common.core.security import create_access_token

reusable_oauth2 = XOAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token"
)

router = APIRouter(tags=["mcp"], prefix="/mcp")


# @router.post("/access_token", operation_id="access_token")
# def local_login(
#         session: SessionDep,
#         form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
# ) -> Token:
#     user = authenticate(session=session, account=form_data.username, password=form_data.password)
#     if not user:
#         raise HTTPException(status_code=400, detail="Incorrect account or password")
#     access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
#     user_dict = user.to_dict()
#     return Token(access_token=create_access_token(
#         user_dict, expires_delta=access_token_expires
#     ))


# @router.get("/ds_list", operation_id="get_datasource_list")
# async def datasource_list(session: SessionDep):
#     return get_datasource_list(session=session)
#
#
# @router.get("/model_list", operation_id="get_model_list")
# async def get_model_list(session: SessionDep):
#     return session.query(AiModelDetail).all()


@router.post("/mcp_start", operation_id="mcp_start")
async def mcp_start(session: SessionDep, chat: ChatStart):
    user: BaseUserDTO = authenticate(session=session, account=chat.username, password=chat.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect account or password")

    if not user.oid or user.oid == 0:
        raise HTTPException(status_code=400, detail="No associated workspace, Please contact the administrator")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_dict = user.to_dict()
    t = Token(access_token=create_access_token(
        user_dict, expires_delta=access_token_expires
    ))
    c = create_chat(session, user, CreateChat(origin=1), False)
    return {"access_token": t.access_token, "chat_id": c.id}


@router.post("/mcp_question", operation_id="mcp_question")
async def mcp_question(session: SessionDep, chat: McpQuestion):
    try:
        payload = jwt.decode(
            chat.token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_data = TokenPayload(**payload)
    except (InvalidTokenError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    # session_user = await get_user_info(session=session, user_id=token_data.id)

    db_user: UserModel = get_db_user(session=session, user_id=token_data.id)
    session_user = UserInfoDTO.model_validate(db_user.model_dump())
    session_user.isAdmin = session_user.id == 1 and session_user.account == 'admin'
    if session_user.isAdmin:
        session_user = session_user
    ws_model: UserWsModel = session.exec(
        select(UserWsModel).where(UserWsModel.uid == session_user.id, UserWsModel.oid == session_user.oid)).first()
    session_user.weight = ws_model.weight if ws_model else -1

    session_user = UserInfoDTO.model_validate(session_user)
    if not session_user:
        raise HTTPException(status_code=404, detail="User not found")

    if session_user.status != 1:
        raise HTTPException(status_code=400, detail="Inactive user")

    mcp_chat = ChatMcp(token=chat.token, chat_id=chat.chat_id, question=chat.question)

    try:
        llm_service = await LLMService.create(session_user, mcp_chat)
        llm_service.init_record()
        llm_service.run_task_async(False, chat.stream)
    except Exception as e:
        traceback.print_exc()

        if chat.stream:
            def _err(_e: Exception):
                yield str(_e) + '\n\n'

            return StreamingResponse(_err(e), media_type="text/event-stream")
        else:
            return JSONResponse(
                content={'message': str(e)},
                status_code=500,
            )
    if chat.stream:
        return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")
    else:
        res = llm_service.await_result()
        raw_data = {}
        for chunk in res:
            if chunk:
                raw_data = chunk
        status_code = 200
        if not raw_data.get('success'):
            status_code = 500

        return JSONResponse(
            content=raw_data,
            status_code=status_code,
        )


@router.post("/mcp_assistant", operation_id="mcp_assistant")
async def mcp_assistant(session: SessionDep, chat: McpAssistant):
    session_user = BaseUserDTO(**{
        "id": -1, "account": 'sqlbot-mcp-assistant', "oid": 1, "assistant_id": -1, "password": '', "language": "zh-CN"
    })
    # session_user: UserModel = get_db_user(session=session, user_id=1)
    # session_user.oid = 1
    c = create_chat(session, session_user, CreateChat(origin=1), False)

    # build assistant param
    configuration = {"endpoint": chat.url}
    # authorization = [{"key": "x-de-token",
    #                 "value": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1aWQiOjEsIm9pZCI6MSwiZXhwIjoxNzU4NTEyMDA2fQ.3NR-pgnADLdXZtI3dXX5-LuxfGYRvYD9kkr2de7KRP0",
    #                 "target": "header"}]
    mcp_assistant_header = AssistantHeader(id=1, name='mcp_assist', domain='', type=1,
                                           configuration=json.dumps(configuration),
                                           certificate=chat.authorization)

    # assistant question
    mcp_chat = ChatQuestion(chat_id=c.id, question=chat.question)
    # ask
    try:
        llm_service = await LLMService.create(session_user, mcp_chat, mcp_assistant_header)
        llm_service.init_record()
        llm_service.run_task_async(False, chat.stream, ChatFinishStep.QUERY_DATA)
    except Exception as e:
        traceback.print_exc()

        if chat.stream:
            def _err(_e: Exception):
                yield str(_e) + '\n\n'

            return StreamingResponse(_err(e), media_type="text/event-stream")
        else:
            return JSONResponse(
                content={'message': str(e)},
                status_code=500,
            )
    if chat.stream:
        return StreamingResponse(llm_service.await_result(), media_type="text/event-stream")
    else:
        res = llm_service.await_result()
        raw_data = {}
        for chunk in res:
            if chunk:
                raw_data = chunk
        status_code = 200
        if not raw_data.get('success'):
            status_code = 500

        return JSONResponse(
            content=raw_data,
            status_code=status_code,
        )
