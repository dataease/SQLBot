# Author: Junjun
# Date: 2025/9/24
from typing import List

from fastapi import APIRouter, Path

from apps.datasource.models.datasource import CoreDatasource
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.core.deps import SessionDep

router = APIRouter(tags=["Table Relation"], prefix="/table_relation")


@router.post("/save/{ds_id}", response_model=List[dict], summary=f"{PLACEHOLDER_PREFIX}tr_save")
async def save_relation(session: SessionDep, relation: List[dict],
                        ds_id: int = Path(..., description=f"{PLACEHOLDER_PREFIX}ds_id")):
    ds = session.get(CoreDatasource, ds_id)
    if ds:
        ds.table_relation = relation
        session.commit()
    else:
        raise Exception("no datasource")
    return True


@router.post("/get/{ds_id}", response_model=List[dict], summary=f"{PLACEHOLDER_PREFIX}tr_get")
async def save_relation(session: SessionDep, ds_id: int = Path(..., description=f"{PLACEHOLDER_PREFIX}ds_id")):
    ds = session.get(CoreDatasource, ds_id)
    if ds:
        return ds.table_relation if ds.table_relation else []
    return []
