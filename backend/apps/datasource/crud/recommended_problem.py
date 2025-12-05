import datetime

from sqlmodel import select

from common.core.deps import SessionDep, CurrentUser, Trans
from ..models.datasource import DsRecommendedProblem, RecommendedProblemBase, CoreDatasource, RecommendedProblemResponse
import orjson


def get_datasource_recommended(session: SessionDep, ds_id: int):
    statement = select(DsRecommendedProblem).where(DsRecommendedProblem.datasource_id == ds_id)
    dsRecommendedProblem = session.exec(statement).all()
    return dsRecommendedProblem

def get_datasource_recommended_chart(session: SessionDep, ds_id: int):
    statement = select(DsRecommendedProblem.question).where(DsRecommendedProblem.datasource_id == ds_id)
    dsRecommendedProblems = session.exec(statement).all()
    return dsRecommendedProblems


def get_datasource_recommended_base(session: SessionDep, ds_id: int):
    statement = select(CoreDatasource.id,CoreDatasource.recommended_config).where(CoreDatasource.id == ds_id)
    datasourceBase = session.exec(statement).first()
    if datasourceBase is None:
        return RecommendedProblemResponse(ds_id,0,None)
    elif datasourceBase.recommended_config == 1:
        return RecommendedProblemResponse(ds_id,1,None)
    else:
        dsRecommendedProblems = session.exec(select(DsRecommendedProblem.question).where(DsRecommendedProblem.datasource_id == ds_id)).all()
        return RecommendedProblemResponse(ds_id,datasourceBase.recommended_config, orjson.dumps(dsRecommendedProblems).decode())

def save_recommended_problem(session: SessionDep,user: CurrentUser, data_info: RecommendedProblemBase):
    session.query(DsRecommendedProblem).filter(DsRecommendedProblem.datasource_id == data_info.datasource_id).delete(synchronize_session=False)
    problemInfo = data_info.problemInfo
    if problemInfo is not None:
        for problemItem in problemInfo:
            problemItem.id = None
            problemItem.create_time = datetime.datetime.now()
            problemItem.create_by = user.id
            record = DsRecommendedProblem(**problemItem.model_dump())
            session.add(record)
            session.flush()
            session.refresh(record)
    session.commit()
