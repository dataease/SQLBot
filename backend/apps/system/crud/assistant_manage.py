

from typing import Optional
from fastapi import FastAPI, Request
from sqlmodel import Session, select
from starlette.middleware.cors import CORSMiddleware
from apps.system.schemas.system_schema import AssistantBase
from common.core.config import settings
from apps.system.models.system_model import AssistantModel
from common.utils.time import get_timestamp
from common.utils.utils import get_domain_list


def dynamic_upgrade_cors(request: Request, session: Session):
    list_result = session.exec(select(AssistantModel).order_by(AssistantModel.create_time)).all()
    seen = set()
    unique_domains = []
    for item in list_result:
        if item.domain:
            for domain in get_domain_list(item.domain):
                domain = domain.strip()
                if domain and domain not in seen:
                    seen.add(domain)
                    unique_domains.append(domain)
    app: FastAPI = request.app
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            break
    if cors_middleware:
        updated_origins = list(set(settings.all_cors_origins + unique_domains))
        cors_middleware.kwargs['allow_origins'] = updated_origins


async def save(request: Request, session: Session, creator: AssistantBase, oid: Optional[int] = 1):
    db_model = AssistantModel.model_validate(creator)
    db_model.create_time = get_timestamp()
    db_model.oid = oid
    session.add(db_model)
    session.commit()
    dynamic_upgrade_cors(request=request, session=session)
    return db_model