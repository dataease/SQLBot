from datetime import datetime
from fastapi import APIRouter
from sqlmodel import select    
from apps.system.models.system_model import AiModelDetail
from apps.system.schemas.system_schema import model_status
from common.core.deps import SessionDep
from common.core.pagination import Paginator
from common.core.schemas import PaginatedResponse, PaginationParams
from common.utils.time import get_timestamp

router = APIRouter(tags=["system/aimodel"], prefix="/system/aimodel")


@router.get("/pager/{pageNum}/{pageSize}", response_model=PaginatedResponse[AiModelDetail])
async def pager(
    session: SessionDep,
    pageNum: int,
    pageSize: int
):
    pagination = PaginationParams(page=pageNum, size=pageSize)
    paginator = Paginator(session)
    filters = {}
    return await paginator.get_paginated_response(
        model=AiModelDetail,
        pagination=pagination,
        **filters)
    
@router.get("/{id}", response_model=AiModelDetail)
async def get_model_by_id(
    session: SessionDep,
    id: int
):
    term = session.get(AiModelDetail, id)
    return term
    
@router.post("", response_model=AiModelDetail)
async def add_model(
    session: SessionDep,
    creator: AiModelDetail
):
    data = AiModelDetail.model_validate(creator)
    data.create_time = get_timestamp()
    session.add(data)
    session.commit()
    return creator

@router.put("", response_model=AiModelDetail)
async def update_terminology(
    session: SessionDep,
    model: AiModelDetail
):
    model.id = int(model.id)
    term = session.exec(select(AiModelDetail).where(AiModelDetail.id == model.id)).first()
    update_data = model.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(term, field, value)
    session.add(term)
    session.commit()
    return model

@router.delete("/{id}", response_model=AiModelDetail)
async def delete_terminology(
    session: SessionDep,
    id: int
):
    term = session.exec(select(AiModelDetail).where(AiModelDetail.id == id)).first()
    session.delete(term)
    session.commit()
    return {
        "message": f"AiModel with ID {id} deleted successfully."
    }
    

@router.patch("/status", response_model=dict)
async def status(session: SessionDep, dto: model_status):
    ids = dto.ids
    status = dto.status
    if not ids:
        return {"message": "ids is empty"}
    statement = select(AiModelDetail).where(AiModelDetail.id.in_(ids))
    terms = session.exec(statement).all()
    for term in terms:
        term.status = status
        session.add(term)
    session.commit()
    return {"message": f"AiModel with IDs {ids} updated successfully."}