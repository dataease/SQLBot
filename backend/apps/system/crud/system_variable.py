# Author: Junjun
# Date: 2026/1/26
import datetime
from collections.abc import Sequence

from fastapi import HTTPException, Request
from sqlalchemy import and_
from sqlalchemy import delete as sql_delete
from sqlmodel import select

from apps.system.models.system_variable_model import SystemVariable
from common.audit.models.log_model import (
    OperationModules,
    OperationStatus,
    OperationType,
    SystemLog,
    SystemLogsResource,
)
from common.audit.schemas.logger_decorator import SystemLogger
from common.core.deps import CurrentUser, SessionDep, Trans
from common.core.pagination import Paginator
from common.core.schemas import PaginationParams


def _audit_variable_change(
    session: SessionDep,
    user: CurrentUser,
    request: Request,
    operation: OperationType,
    resources: Sequence[tuple[int, str]],
) -> None:
    client_info = SystemLogger.get_client_info(request)
    resource_ids = [resource_id for resource_id, _ in resources]
    log = SystemLog(
        operation_type=operation,
        operation_status=OperationStatus.SUCCESS,
        module=OperationModules.SYSTEM_VARIABLE,
        user_id=user.id,
        user_name=user.name,
        oid=user.oid,
        ip_address=(client_info["ip_address"] or "")[:255] or None,
        user_agent=(client_info["user_agent"] or "")[:255] or None,
        request_method=request.method,
        request_path=request.scope["path"][:255],
        resource_id=str(resource_ids[0] if len(resource_ids) == 1 else resource_ids),
    )
    session.add(log)
    session.flush()
    session.add_all(
        SystemLogsResource(
            log_id=log.id,
            resource_id=str(resource_id),
            resource_name=name,
            module=log.module,
        )
        for resource_id, name in resources
    )


def save(session: SessionDep, user: CurrentUser, trans: Trans, variable: SystemVariable, request: Request):
    checkName(session, trans, variable)
    variable.type = 'custom'
    if variable.id is None:
        variable.create_time = datetime.datetime.now()
        variable.create_by = user.id
        record = variable
        operation = OperationType.CREATE
    else:
        record = session.query(SystemVariable).filter(SystemVariable.id == variable.id).first()
        update_data = variable.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)
        operation = OperationType.UPDATE
    session.add(record)
    session.flush()
    _audit_variable_change(session, user, request, operation, [(record.id, record.name)])
    session.commit()
    return True


def delete(session: SessionDep, ids: list[int], user: CurrentUser, request: Request):
    if not ids:
        return
    deleted = session.execute(
        sql_delete(SystemVariable)
        .where(SystemVariable.id.in_(ids))
        .returning(SystemVariable.id, SystemVariable.name)
    ).tuples().all()
    if deleted:
        _audit_variable_change(session, user, request, OperationType.DELETE, deleted)
        session.commit()


def list_all(session: SessionDep, trans: Trans, variable: SystemVariable):
    if variable.name is None:
        records = session.query(SystemVariable).order_by(SystemVariable.type.desc(),
                                                         SystemVariable.name.asc()).all()
    else:
        records = session.query(SystemVariable).filter(
            and_(SystemVariable.name.ilike(f'%{variable.name}%'), SystemVariable.type != 'system')).order_by(
            SystemVariable.type.desc(), SystemVariable.name.asc()).all()

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
        stmt = select(SystemVariable).order_by(SystemVariable.type.desc(), SystemVariable.name.asc())
    else:
        stmt = select(SystemVariable).where(
            and_(SystemVariable.name.ilike(f'%{variable.name}%'), SystemVariable.type != 'system')).order_by(
            SystemVariable.type.desc(), SystemVariable.name.asc())

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


def checkValue(session: SessionDep, trans: Trans, values: list):
    # values: [{"variableId":1,"variableValues":["a","b"]}]

    pass
