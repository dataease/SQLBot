from typing import Optional

from fastapi import APIRouter, Query

from apps.terminology.curd.terminology import page_terminology, create_terminology, update_terminology, \
    delete_terminology, enable_terminology
from apps.terminology.models.terminology_model import TerminologyInfo
from common.core.deps import SessionDep, CurrentUser, Trans

router = APIRouter(tags=["Terminology"], prefix="/system/terminology")


@router.get("/page/{current_page}/{page_size}")
async def pager(session: SessionDep, current_user: CurrentUser, current_page: int, page_size: int,
                word: Optional[str] = Query(None, description="搜索术语(可选)")):
    current_page, page_size, total_count, total_pages, _list = page_terminology(session, current_page, page_size, word,
                                                                                current_user.oid)

    return {
        "current_page": current_page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": total_pages,
        "data": _list
    }


@router.put("")
async def create_or_update(session: SessionDep, current_user: CurrentUser, trans: Trans, info: TerminologyInfo):
    oid = current_user.oid
    if info.id:
        return update_terminology(session, info, oid, trans)
    else:
        return create_terminology(session, info, oid, trans)


@router.delete("")
async def delete(session: SessionDep, id_list: list[int]):
    delete_terminology(session, id_list)


@router.get("/{id}/enable/{enabled}")
async def enable(session: SessionDep, id: int, enabled: bool, trans: Trans):
    enable_terminology(session, id, enabled, trans)
