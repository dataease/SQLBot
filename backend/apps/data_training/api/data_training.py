from typing import Optional

from fastapi import APIRouter, Query

from apps.data_training.curd.data_training import page_data_training, create_training, update_training, delete_training, \
    enable_training
from apps.data_training.models.data_training_model import DataTrainingInfo
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["DataTraining"], prefix="/system/data-training")


@router.get("/page/{current_page}/{page_size}")
async def pager(session: SessionDep, current_user: CurrentUser, current_page: int, page_size: int,
                question: Optional[str] = Query(None, description="搜索问题(可选)")):
    current_page, page_size, total_count, total_pages, _list = page_data_training(session, current_page, page_size,
                                                                                  question,
                                                                                  current_user.oid)

    return {
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": _list
    }


@router.put("")
async def create_or_update(session: SessionDep, current_user: CurrentUser, trans: Trans, info: DataTrainingInfo):
    oid = current_user.oid
    if info.id:
        return update_training(session, info, oid, trans)
    else:
        return create_training(session, info, oid, trans)


@router.delete("")
async def delete(session: SessionDep, id_list: list[int]):
    delete_training(session, id_list)


@router.get("/{id}/enable/{enabled}")
async def enable(session: SessionDep, id: int, enabled: bool, trans: Trans):
    enable_training(session, id, enabled, trans)
