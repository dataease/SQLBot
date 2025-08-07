from common.core.deps import SessionDep
from ..models.datasource import CoreField


def delete_field_by_ds_id(session: SessionDep, id: int):
    session.query(CoreField).filter(CoreField.ds_id == id).delete(synchronize_session=False)
    session.commit()


def get_fields_by_table_id(session: SessionDep, id: int):
    return session.query(CoreField).filter(CoreField.table_id == id).all()


def update_field(session: SessionDep, item: CoreField):
    record = session.query(CoreField).filter(CoreField.id == item.id).first()
    record.checked = item.checked
    record.custom_comment = item.custom_comment
    session.add(record)
    session.commit()
