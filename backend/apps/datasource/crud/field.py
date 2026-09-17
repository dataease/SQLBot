from common.core.deps import SessionDep
from ..models.datasource import CoreField, FieldObj, CoreTable
from sqlalchemy import or_, and_
from fastapi import HTTPException


def delete_field_by_ds_id(session: SessionDep, id: int):
    session.query(CoreField).filter(CoreField.ds_id == id).delete(synchronize_session=False)
    session.commit()


def get_fields_by_table_id(session: SessionDep, ds_id: int, id: int, field: FieldObj):
    table = session.query(CoreTable).filter(and_(CoreTable.id == id, CoreTable.ds_id == ds_id)).first()
    if not table:
        raise HTTPException(status_code=500, detail='The data source ID does not match the table ID')

    if field and field.fieldName:
        return session.query(CoreField).filter(
            and_(CoreField.table_id == id, or_(CoreField.field_name.like(f'%{field.fieldName}%'),
                                               CoreField.field_name.like(f'%{field.fieldName.lower()}%'),
                                               CoreField.field_name.like(f'%{field.fieldName.upper()}%')))).order_by(
            CoreField.field_index.asc()).all()
    else:
        return session.query(CoreField).filter(CoreField.table_id == id).order_by(CoreField.field_index.asc()).all()


def update_field(session: SessionDep, item: CoreField):
    record = session.query(CoreField).filter(CoreField.id == item.id).first()
    record.checked = item.checked
    record.custom_comment = item.custom_comment
    session.add(record)
    session.commit()
