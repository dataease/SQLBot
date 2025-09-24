# Author: Junjun
# Date: 2025/9/24
from typing import List

from fastapi import APIRouter

from apps.datasource.models.datasource import CoreDatasource
from common.core.deps import SessionDep

router = APIRouter(tags=["table_relation"], prefix="/table_relation")


@router.post("/save/{ds_id}")
async def save_relation(session: SessionDep, ds_id: int, relation: List[dict]):
    ds = session.get(CoreDatasource, ds_id)
    if ds:
        ds.table_relation = relation
        session.commit()
    else:
        raise Exception("no datasource")
    return True


@router.post("/get/{ds_id}")
async def save_relation(session: SessionDep, ds_id: int):
    ds = session.get(CoreDatasource, ds_id)
    if ds:
        return ds.table_relation if ds.table_relation else []
    return []
