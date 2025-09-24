import json
from typing import List, Optional

from sqlalchemy import and_
from sqlbot_xpack.permissions.api.permission import transRecord2DTO
from sqlbot_xpack.permissions.models.ds_permission import DsPermission, PermissionDTO
from sqlbot_xpack.permissions.models.ds_rules import DsRules

from apps.datasource.crud.row_permission import transFilterTree
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from common.core.deps import CurrentUser, SessionDep


def get_row_permission_filters(session: SessionDep, current_user: CurrentUser, ds: CoreDatasource,
                               tables: Optional[list] = None, single_table: Optional[CoreTable] = None):
    if single_table:
        table_list = [session.get(CoreTable, single_table.id)]
    else:
        table_list = session.query(CoreTable).filter(
            and_(CoreTable.ds_id == ds.id, CoreTable.table_name.in_(tables))
        ).all()

    filters = []
    if is_normal_user(current_user):
        contain_rules = session.query(DsRules).all()
        for table in table_list:
            row_permissions = session.query(DsPermission).filter(
                and_(DsPermission.table_id == table.id, DsPermission.type == 'row')).all()
            res: List[PermissionDTO] = []
            if row_permissions is not None:
                for permission in row_permissions:
                    # check permission and user in same rules
                    flag = False
                    for r in contain_rules:
                        p_list = json.loads(r.permission_list)
                        u_list = json.loads(r.user_list)
                        if p_list is not None and u_list is not None and permission.id in p_list and (
                                current_user.id in u_list or f'{current_user.id}' in u_list):
                            flag = True
                            break
                    if flag:
                        res.append(transRecord2DTO(session, permission))
            where_str = transFilterTree(session, res, ds)
            filters.append({"table": table.table_name, "filter": where_str})
    return filters


def get_column_permission_fields(session: SessionDep, current_user: CurrentUser, table: CoreTable,
                                 fields: list[CoreField], contain_rules: list[DsRules]):
    if is_normal_user(current_user):
        column_permissions = session.query(DsPermission).filter(
            and_(DsPermission.table_id == table.id, DsPermission.type == 'column')).all()
        if column_permissions is not None:
            for permission in column_permissions:
                # check permission and user in same rules
                # obj = session.query(DsRules).filter(
                #     and_(DsRules.permission_list.op('@>')(cast([permission.id], JSONB)),
                #          or_(DsRules.user_list.op('@>')(cast([f'{current_user.id}'], JSONB)),
                #              DsRules.user_list.op('@>')(cast([current_user.id], JSONB))))
                # ).first()
                flag = False
                for r in contain_rules:
                    p_list = json.loads(r.permission_list)
                    u_list = json.loads(r.user_list)
                    if p_list is not None and u_list is not None and permission.id in p_list and (
                            current_user.id in u_list or f'{current_user.id}' in u_list):
                        flag = True
                        break
                if flag:
                    permission_list = json.loads(permission.permissions)
                    fields = filter_list(fields, permission_list)
    return fields


def is_normal_user(current_user: CurrentUser):
    return current_user.id != 1


def filter_list(list_a, list_b):
    id_to_invalid = {}
    for b in list_b:
        if not b['enable']:
            id_to_invalid[b['field_id']] = True

    return [a for a in list_a if not id_to_invalid.get(a.id, False)]
