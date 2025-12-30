from typing import List

from fastapi import APIRouter, File, UploadFile, HTTPException

from apps.dashboard.crud.dashboard_service import list_resource, load_resource, \
    create_resource, create_canvas, validate_name, delete_resource, update_resource, update_canvas
from apps.dashboard.models.dashboard_model import CreateDashboard, BaseDashboard, QueryDashboard
from apps.swagger.i18n import PLACEHOLDER_PREFIX
from common.audit.models.log_model import OperationType, OperationModules
from common.audit.schemas.logger_decorator import LogConfig, system_log
from common.core.deps import SessionDep, CurrentUser

router = APIRouter(tags=["Dashboard"], prefix="/dashboard")


@router.post("/list_resource", summary=f"{PLACEHOLDER_PREFIX}list_resource_api")
async def list_resource_api(session: SessionDep, dashboard: QueryDashboard, current_user: CurrentUser):
    return list_resource(session=session, dashboard=dashboard, current_user=current_user)


@router.post("/load_resource", summary=f"{PLACEHOLDER_PREFIX}load_resource_api")
async def load_resource_api(session: SessionDep, current_user: CurrentUser, dashboard: QueryDashboard):
    resource_dict = load_resource(session=session, dashboard=dashboard)
    if resource_dict and resource_dict.get("create_by") != str(current_user.id):
        raise HTTPException(
            status_code=403,
            detail="You do not have permission to access this resource"
        )

    return resource_dict


@router.post("/create_resource", response_model=BaseDashboard, summary=f"{PLACEHOLDER_PREFIX}create_resource_api")
async def create_resource_api(session: SessionDep, user: CurrentUser, dashboard: CreateDashboard):
    return create_resource(session, user, dashboard)


@router.post("/update_resource", response_model=BaseDashboard, summary=f"{PLACEHOLDER_PREFIX}update_resource")
@system_log(LogConfig(
    operation_type=OperationType.UPDATE,
    module=OperationModules.DASHBOARD,
    resource_id_expr="dashboard.id"
))
async def update_resource_api(session: SessionDep, user: CurrentUser, dashboard: QueryDashboard):
    return update_resource(session=session, user=user, dashboard=dashboard)


@router.delete("/delete_resource/{resource_id}/{name}", summary=f"{PLACEHOLDER_PREFIX}delete_resource_api")
@system_log(LogConfig(
    operation_type=OperationType.DELETE,
    module=OperationModules.DASHBOARD,
    resource_id_expr="resource_id",
    remark_expr="name"
))
async def delete_resource_api(session: SessionDep, current_user: CurrentUser, resource_id: str, name: str):
    return delete_resource(session, current_user, resource_id)


@router.post("/create_canvas", response_model=BaseDashboard, summary=f"{PLACEHOLDER_PREFIX}create_canvas_api")
@system_log(LogConfig(
    operation_type=OperationType.CREATE,
    module=OperationModules.DASHBOARD,
    result_id_expr="id"
))
async def create_canvas_api(session: SessionDep, user: CurrentUser, dashboard: CreateDashboard):
    return create_canvas(session, user, dashboard)


@router.post("/update_canvas", response_model=BaseDashboard, summary=f"{PLACEHOLDER_PREFIX}update_canvas_api")
@system_log(LogConfig(
    operation_type=OperationType.UPDATE,
    module=OperationModules.DASHBOARD,
    resource_id_expr="dashboard.id"
))
async def update_canvas_api(session: SessionDep, user: CurrentUser, dashboard: CreateDashboard):
    return update_canvas(session, user, dashboard)


@router.post("/check_name", summary=f"{PLACEHOLDER_PREFIX}check_name_api")
async def check_name_api(session: SessionDep, user: CurrentUser, dashboard: QueryDashboard):
    return validate_name(session, user, dashboard)
