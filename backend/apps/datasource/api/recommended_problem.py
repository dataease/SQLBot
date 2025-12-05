from fastapi import APIRouter

from apps.datasource.crud.datasource import update_ds_recommended_config
from apps.datasource.crud.recommended_problem import get_datasource_recommended, \
    save_recommended_problem, get_datasource_recommended_base
from apps.datasource.models.datasource import RecommendedProblemBase
from common.core.deps import SessionDep, CurrentUser

router = APIRouter(tags=["recommended_problem"], prefix="/recommended_problem")


@router.get("/get_datasource_recommended/{ds_id}")
async def datasource_recommended(session: SessionDep, ds_id: int):
    return get_datasource_recommended(session, ds_id)

@router.get("/get_datasource_recommended_base/{ds_id}")
async def datasource_recommended(session: SessionDep, ds_id: int):
    return get_datasource_recommended_base(session, ds_id)


@router.post("/save_recommended_problem")
async def datasource_recommended(session: SessionDep, user: CurrentUser, data_info: RecommendedProblemBase):
    update_ds_recommended_config(session, data_info.datasource_id, data_info.recommended_config)
    return save_recommended_problem(session, user, data_info)
