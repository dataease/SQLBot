
from typing import Optional
from sqlmodel import Session, func, select, delete as sqlmodel_delete
from apps.system.models.system_model import UserWsModel, WorkspaceModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from apps.system.schemas.system_schema import EMAIL_REGEX, PWD_REGEX, BaseUserDTO, UserInfoDTO, UserWs
from common.core.deps import SessionDep
from common.core.sqlbot_cache import cache, clear_cache
from common.utils.locale import I18n
from common.utils.utils import SQLBotLogUtil
from ..models.user import UserModel, UserPlatformModel
from common.core.security import verify_md5pwd
import re

def get_db_user(*, session: Session, user_id: int) -> UserModel:
    db_user = session.get(UserModel, user_id)
    return db_user

def get_user_by_account(*, session: Session, account: str) -> BaseUserDTO | None:
    statement = select(UserModel).where(UserModel.account == account)
    db_user = session.exec(statement).first()
    if not db_user:
        return None
    return BaseUserDTO.model_validate(db_user.model_dump())

@cache(namespace=CacheNamespace.AUTH_INFO, cacheName=CacheName.USER_INFO, keyExpression="user_id")
async def get_user_info(*, session: Session, user_id: int) -> UserInfoDTO | None:
    db_user: UserModel = get_db_user(session = session, user_id = user_id)
    if not db_user:
        return None
    userInfo = UserInfoDTO.model_validate(db_user.model_dump())
    userInfo.isAdmin = userInfo.id == 1 and userInfo.account == 'admin'
    if userInfo.isAdmin:
        return userInfo
    ws_model: UserWsModel = session.exec(select(UserWsModel).where(UserWsModel.uid == userInfo.id, UserWsModel.oid == userInfo.oid)).first()
    userInfo.weight = ws_model.weight if ws_model else -1
    return userInfo

def authenticate(*, session: Session, account: str, password: str) -> BaseUserDTO | None:
    db_user = get_user_by_account(session=session, account=account)
    if not db_user:
        return None
    if not verify_md5pwd(password, db_user.password):
        return None
    return db_user

async def user_ws_options(session: Session, uid: int, trans: Optional[I18n] = None) -> list[UserWs]:
    if uid == 1:
        stmt = select(WorkspaceModel.id, WorkspaceModel.name).order_by(WorkspaceModel.name, WorkspaceModel.create_time)
    else:
        stmt = select(WorkspaceModel.id, WorkspaceModel.name).join(
            UserWsModel, UserWsModel.oid == WorkspaceModel.id
        ).where(
            UserWsModel.uid == uid,
        ).order_by(WorkspaceModel.name, WorkspaceModel.create_time)
    result = session.exec(stmt)
    if not trans:
        return result.all()
    list_result = [
        UserWs(id = id, name = trans(name) if name.startswith('i18n') else name) 
        for id, name in result.all()
    ]
    if list_result:
        list_result.sort(key=lambda x: x.name)
    return list_result
    
@clear_cache(namespace=CacheNamespace.AUTH_INFO, cacheName=CacheName.USER_INFO, keyExpression="id")
async def single_delete(session: SessionDep, id: int):
    user_model: UserModel = get_db_user(session = session, user_id = id)
    del_stmt = sqlmodel_delete(UserWsModel).where(UserWsModel.uid == id)
    session.exec(del_stmt)
    if user_model and user_model.origin and user_model.origin != 0:
        platform_del_stmt = sqlmodel_delete(UserPlatformModel).where(UserPlatformModel.uid == id)
        session.exec(platform_del_stmt)
    session.delete(user_model)
    session.commit()

@clear_cache(namespace=CacheNamespace.AUTH_INFO, cacheName=CacheName.USER_INFO, keyExpression="id")    
async def clean_user_cache(id: int):
    SQLBotLogUtil.info(f"User cache for [{id}] has been cleaned")


def check_account_exists(*, session: Session, account: str) -> bool:
    return session.exec(select(func.count()).select_from(UserModel).where(UserModel.account == account)).one() > 0
def check_email_exists(*, session: Session, email: str) -> bool:
    return session.exec(select(func.count()).select_from(UserModel).where(UserModel.email == email)).one() > 0



def check_email_format(email: str) -> bool:
    return bool(EMAIL_REGEX.fullmatch(email))

def check_pwd_format(pwd: str) -> bool:
    return bool(PWD_REGEX.fullmatch(pwd))
