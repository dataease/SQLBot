from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from apps.system.schemas.logout_schema import LogoutSchema
from apps.system.schemas.system_schema import BaseUserDTO, LoginPwdEditor
from common.core.deps import SessionDep, Trans
from common.utils.crypto import sqlbot_decrypt
from ..crud.user import authenticate, check_pwd_format, clean_user_cache, get_db_user
from common.core.security import create_access_token, default_pwd, md5pwd, verify_md5pwd
from datetime import timedelta
from common.core.config import settings
from common.core.schemas import Token
from sqlbot_xpack.authentication.manage import logout as xpack_logout
from sqlbot_xpack.config.arg_manage import get_group_args

from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import system_log, LogConfig

router = APIRouter(tags=["login"], prefix="/login")


async def initial_pwd_disabled(session) -> bool:
    login_args = await get_group_args(session=session, flag='login')
    disabled_arg = next((a for a in login_args if a.pkey == 'login.initial_pwd_disabled'), None)
    return bool(disabled_arg and str(disabled_arg.pval).strip().lower() == 'true')


@router.post("/access-token")
@system_log(LogConfig(
    operation_type=OperationType.LOGIN,
    module=OperationModules.USER,
    result_id_expr="id"
))
async def local_login(
    session: SessionDep,
    trans: Trans,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    origin_account = await sqlbot_decrypt(form_data.username)
    origin_pwd = await sqlbot_decrypt(form_data.password)
    user: BaseUserDTO = authenticate(session=session, account=origin_account, password=origin_pwd)
    if not user:
        raise HTTPException(status_code=400, detail=trans('i18n_login.account_pwd_error'))
    if not user.oid or user.oid == 0:
        raise HTTPException(status_code=400, detail=trans('i18n_login.no_associated_ws', msg = trans('i18n_concat_admin')))
    if user.status != 1:
        raise HTTPException(status_code=400, detail=trans('i18n_login.user_disable', msg = trans('i18n_concat_admin')))
    if user.origin is not None and user.origin != 0:
        raise HTTPException(status_code=400, detail=trans('i18n_login.origin_error'))
    if (
        user.id != 1
        and await initial_pwd_disabled(session)
        and verify_md5pwd(default_pwd(), user.password)
    ):
        return Token(access_token='', need_change_pwd=True)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_dict = user.to_dict()
    return Token(
        access_token=create_access_token(user_dict, expires_delta=access_token_expires),
        need_change_pwd=False,
    )


@router.post("/change-pwd")
@system_log(LogConfig(
    operation_type=OperationType.UPDATE_PWD,
    module=OperationModules.USER,
    result_id_expr="id"
))
async def login_change_pwd(session: SessionDep, trans: Trans, editor: LoginPwdEditor):
    origin_account = await sqlbot_decrypt(editor.account)
    origin_pwd = await sqlbot_decrypt(editor.pwd)
    new_pwd = await sqlbot_decrypt(editor.new_pwd)
    user: BaseUserDTO = authenticate(session=session, account=origin_account, password=origin_pwd)
    if not user:
        raise HTTPException(status_code=400, detail=trans('i18n_login.account_pwd_error'))
    if user.origin is not None and user.origin != 0:
        raise HTTPException(status_code=400, detail=trans('i18n_login.origin_error'))
    if not check_pwd_format(new_pwd):
        raise HTTPException(status_code=400, detail=trans('i18n_format_invalid', key = trans('i18n_user.password')))
    if await initial_pwd_disabled(session) and new_pwd == default_pwd():
        raise HTTPException(status_code=400, detail=trans('i18n_login.new_pwd_is_initial'))
    db_user = get_db_user(session=session, user_id=user.id)
    db_user.password = md5pwd(new_pwd)
    session.add(db_user)
    await clean_user_cache(user.id)
    return db_user

@router.post("/logout")
async def logout(session: SessionDep, request: Request, dto: LogoutSchema):
    if dto.origin != 0:
        return await xpack_logout(session, request, dto)
    return None