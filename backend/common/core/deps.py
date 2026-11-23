import base64
from typing import Annotated
from urllib.parse import unquote

from fastapi import Depends, HTTPException, Request
from sqlmodel import Session
from apps.system.schemas.system_schema import AssistantHeader, UserInfoDTO
from common.core.db import get_session
from common.utils.locale import I18n


SessionDep = Annotated[Session, Depends(get_session)]
i18n = I18n()
async def get_i18n(request: Request):
    return i18n(request)

Trans = Annotated[I18n, Depends(get_i18n)]
async def get_current_user(request: Request) -> UserInfoDTO:
    return request.state.current_user

CurrentUser = Annotated[UserInfoDTO, Depends(get_current_user)]

async def get_current_assistant(request: Request) -> AssistantHeader | None:
    base_assistant = getattr(request.state, "assistant", None)
    if base_assistant is None:
        # The certificate/online headers only describe an assistant identity that
        # the middleware has already resolved. Without it they used to be written
        # onto None and turn the request into a 500.
        return None
    entry_certificate = request.headers.get("X-SQLBOT-ASSISTANT-CERTIFICATE")
    if entry_certificate:
        try:
            decoded_certificate = base64.b64decode(entry_certificate).decode("utf-8")
        except ValueError:
            # binascii.Error and UnicodeDecodeError both subclass ValueError.
            raise HTTPException(status_code=400, detail="invalid assistant certificate")
        base_assistant.certificate = unquote(decoded_certificate)
    entry_online = request.headers.get("X-SQLBOT-ASSISTANT-ONLINE")
    if entry_online:
        base_assistant.online = str(entry_online).lower() == "true"
    return base_assistant

CurrentAssistant = Annotated[AssistantHeader, Depends(get_current_assistant)]



