# Author: Junjun
# Date: 2026/1/26
import datetime

from typing import List
from fastapi import HTTPException
from sqlalchemy import and_
from sqlmodel import select

from apps.system.models.system_variable_model import SystemVariable
from common.core.deps import SessionDep, CurrentUser, Trans
from common.core.pagination import Paginator
from common.core.schemas import PaginationParams


def save(session: SessionDep, user: CurrentUser, trans: Trans, variable: SystemVariable):
    checkName(session, trans, variable)
    variable.type = 'custom'
    if variable.id is None:
        variable.create_time = datetime.datetime.now()
        variable.create_by = user.id
        session.add(variable)
        session.commit()
    else:
        record = session.query(SystemVariable).filter(SystemVariable.id == variable.id).first()
        update_data = variable.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)
        session.add(record)
        session.commit()
    return True


def delete(session: SessionDep, ids: List[int]):
    session.query(SystemVariable).filter(SystemVariable.id.in_(ids)).delete()


def list_all(session: SessionDep, trans: Trans, variable: SystemVariable):
    if variable.name is None:
        records = session.query(SystemVariable).order_by(SystemVariable.type.desc()).all()
    else:
        records = session.query(SystemVariable).filter(
            and_(SystemVariable.name.like(f'%{variable.name}%'), SystemVariable.type != 'system')).order_by(
            SystemVariable.type.desc()).all()

    res = []
    for r in records:
        data = SystemVariable(**r.__dict__)
        if data.type == 'system':
            data.name = trans(data.name)
        res.append(data)
    return res


async def list_page(session: SessionDep, trans: Trans, pageNum: int, pageSize: int, variable: SystemVariable):
    pagination = PaginationParams(page=pageNum, size=pageSize)
    paginator = Paginator(session)
    filters = {}

    if variable.name is None:
        stmt = select(SystemVariable).order_by(SystemVariable.type.desc())
    else:
        stmt = select(SystemVariable).where(
            and_(SystemVariable.name.like(f'%{variable.name}%'), SystemVariable.type != 'system')).order_by(
            SystemVariable.type.desc())

    variable_page = await paginator.get_paginated_response(
        stmt=stmt,
        pagination=pagination,
        **filters)

    res = []
    for r in variable_page.items:
        data = SystemVariable(**r)
        if data.type == 'system':
            data.name = trans(data.name)
        res.append(data)

    return {"items": res, "page": variable_page.page, "size": variable_page.size, "total": variable_page.total,
            "total_pages": variable_page.total_pages}


def checkName(session: SessionDep, trans: Trans, variable: SystemVariable):
    if variable.id is None:
        records = session.query(SystemVariable).filter(SystemVariable.name == variable.name).all()
        if records and len(records) > 0:
            raise HTTPException(status_code=500, detail=trans('i18n_variable.name_exist'))
    else:
        records = session.query(SystemVariable).filter(
            and_(SystemVariable.name == variable.name, SystemVariable.id != variable.id)).all()
        if records and len(records) > 0:
            raise HTTPException(status_code=500, detail=trans('i18n_variable.name_exist'))


def checkValue(session: SessionDep, trans: Trans, values:List):
    # values: [{"variableId":1,"variableValues":["a","b"]}]

    pass