from sqlmodel import select

from common.core.deps import SessionDep
from ..models.datasource import DsRecommendedProblem


def get_datasource_recommended(session: SessionDep, ds_id: int):
    statement = select(DsRecommendedProblem).where(DsRecommendedProblem.datasource_id == ds_id)
    dsRecommendedProblem = session.exec(statement)
    return dsRecommendedProblem

