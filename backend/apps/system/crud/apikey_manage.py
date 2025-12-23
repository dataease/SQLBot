
from sqlmodel import select

from apps.system.models.system_model import ApiKeyModel
from apps.system.schemas.auth import CacheName, CacheNamespace
from common.core.deps import SessionDep
from common.core.sqlbot_cache import cache, clear_cache
from common.utils.utils import SQLBotLogUtil

@cache(namespace=CacheNamespace.AUTH_INFO, cacheName=CacheName.ASK_INFO, keyExpression="access_key")
async def get_api_key(session: SessionDep, access_key: str) -> ApiKeyModel | None:
    query = select(ApiKeyModel).where(ApiKeyModel.access_key == access_key)
    return session.exec(query).first()

@clear_cache(namespace=CacheNamespace.AUTH_INFO, cacheName=CacheName.ASK_INFO, keyExpression="access_key")
async def clear_api_key_cache(access_key: str):
     SQLBotLogUtil.info(f"Api key cache for [{access_key}] has been cleaned")