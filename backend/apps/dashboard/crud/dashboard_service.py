from sqlalchemy import select, and_, text
from apps.dashboard.models.dashboard_model import CoreDashboard, CreateDashboard, QueryDashboard, DashboardBaseResponse
from common.core.deps import SessionDep, CurrentUser
import uuid
import time

from common.utils.tree_utils import build_tree_generic


def list_resource(session: SessionDep, dashboard: QueryDashboard, current_user: CurrentUser):
    sql = "SELECT id, name, type, node_type, pid, create_time FROM core_dashboard"
    filters = []
    params = {}
    oid = str(current_user.oid if current_user.oid is not None else 1)
    filters.append("workspace_id = :workspace_id")
    filters.append("create_by = :create_by")
    params["workspace_id"] = oid
    params["create_by"] = str(current_user.id)
    if dashboard.node_type is not None and dashboard.node_type != "":
        filters.append("node_type = :node_type")
        params["node_type"] = dashboard.node_type

    if filters:
        sql += " WHERE " + " AND ".join(filters)
    sql += " ORDER BY create_time DESC"
    result = session.execute(text(sql), params)
    nodes = [DashboardBaseResponse(**row) for row in result.mappings()]
    tree = build_tree_generic(nodes, root_pid="root")
    return tree
    

def load_resource(session: SessionDep, dashboard: QueryDashboard):
    sql = text("""
               SELECT cd.*,
                      creator.name AS create_name,
                      updater.name AS update_name
               FROM core_dashboard cd
                        LEFT JOIN sys_user creator ON cd.create_by = creator.id::varchar
        LEFT JOIN sys_user updater
               ON cd.update_by = updater.id:: varchar
               WHERE cd.id = :dashboard_id
               """)
    result = session.execute(sql, {"dashboard_id": dashboard.id}).mappings().first()
    return result


def get_create_base_info(user: CurrentUser, dashboard: CreateDashboard):
    new_id = uuid.uuid4().hex
    record = CoreDashboard(**dashboard.model_dump())
    record.workspace_id = user.oid
    record.id = new_id
    record.create_by = user.id
    record.create_time = int(time.time())
    return record


def create_resource(session: SessionDep, user: CurrentUser, dashboard: CreateDashboard):
    record = get_create_base_info(user, dashboard)
    session.add(record)
    session.flush()
    session.refresh(record)
    session.commit()
    return record


def update_resource(session: SessionDep, user: CurrentUser, dashboard: QueryDashboard):
    record = session.query(CoreDashboard).filter(CoreDashboard.id == dashboard.id).first()
    record.name = dashboard.name
    record.update_by = user.id
    record.update_time = int(time.time())
    session.add(record)
    session.commit()
    return record


def create_canvas(session: SessionDep, user: CurrentUser, dashboard: CreateDashboard):
    record = get_create_base_info(user, dashboard)
    record.node_type = dashboard.node_type
    record.component_data = dashboard.component_data
    record.canvas_style_data = dashboard.canvas_style_data
    record.canvas_view_info = dashboard.canvas_view_info
    session.add(record)
    session.flush()
    session.refresh(record)
    session.commit()
    return record


def update_canvas(session: SessionDep, user: CurrentUser, dashboard: CreateDashboard):
    record = session.query(CoreDashboard).filter(CoreDashboard.id == dashboard.id).first()
    record.name = dashboard.name
    record.update_by = user.id
    record.update_time = int(time.time())
    record.component_data = dashboard.component_data
    record.canvas_style_data = dashboard.canvas_style_data
    record.canvas_view_info = dashboard.canvas_view_info
    session.add(record)
    session.commit()
    return record


def validate_name(session: SessionDep,user: CurrentUser,  dashboard: QueryDashboard) -> bool:
    if not dashboard.opt:
        raise ValueError("opt is required")
    oid = str(user.oid if user.oid is not None else 1)
    uid = str(user.id)


    if dashboard.opt in ('newLeaf', 'newFolder'):
        query = session.query(CoreDashboard).filter(
            and_(
                CoreDashboard.workspace_id == oid,
                CoreDashboard.create_by == uid,
                CoreDashboard.name == dashboard.name
            )
        )
    elif dashboard.opt in ('updateLeaf', 'updateFolder', 'rename'):
        if not dashboard.id:
            raise ValueError("id is required for update operation")
        query = session.query(CoreDashboard).filter(
            and_(
                CoreDashboard.workspace_id == oid,
                CoreDashboard.create_by == uid,
                CoreDashboard.name == dashboard.name,
                CoreDashboard.id != dashboard.id
            )
        )
    else:
        raise ValueError(f"Invalid opt value: {dashboard.opt}")
    return not session.query(query.exists()).scalar()


def delete_resource(session: SessionDep, current_user: CurrentUser, resource_id: str):
    coreDashboard = session.get(CoreDashboard, resource_id)
    if not coreDashboard:
        raise ValueError(f"Resource with id {resource_id} does not exist")
    if coreDashboard.create_by != str(current_user.id):
        raise ValueError(f"Resource with id {resource_id} not owned by the current user")
    sql = text("DELETE FROM core_dashboard WHERE id = :resource_id")
    result = session.execute(sql, {"resource_id": resource_id})
    session.commit()
    return result.rowcount > 0
