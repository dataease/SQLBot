from fastapi import APIRouter

from apps.datasource.crud.recommended_problem import get_datasource_recommended
from common.core.deps import SessionDep

router = APIRouter(tags=["recommended_problem"], prefix="/recommended_problem")


@router.get("/get_datasource_recommended/{ds_id}")
async def datasource_recommended(session: SessionDep, ds_id: int):
    return get_datasource_recommended(session, ds_id)

