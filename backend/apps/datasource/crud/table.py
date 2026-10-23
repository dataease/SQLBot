import json

from sqlalchemy import select, update

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import parse_valid_embedding
from common.core.deps import SessionDep
from common.core.embedding_config import load_embedding_config
from common.utils.embedding_lifecycle import (
    EmbeddingGenerationError,
    lock_embedding_resource,
)
from common.utils.utils import SQLBotLogUtil

from ..models.datasource import CoreDatasource, CoreField, CoreTable
from .embedding_state import invalidate_metadata


def delete_table_by_ds_id(session: SessionDep, id: int):
    session.query(CoreTable).filter(CoreTable.ds_id == id).delete(
        synchronize_session=False
    )
    session.commit()


def get_tables_by_ds_id(session: SessionDep, id: int):
    return (
        session.query(CoreTable)
        .filter(CoreTable.ds_id == id)
        .order_by(CoreTable.table_name.asc())
        .all()
    )


def update_table(session: SessionDep, item: CoreTable):
    record = session.query(CoreTable).filter(CoreTable.id == item.id).first()
    invalidate_metadata(session, record.ds_id, [record.id])
    record.checked = item.checked
    record.custom_comment = item.custom_comment
    session.add(record)
    session.commit()


def _missing(vector):
    try:
        parse_valid_embedding(vector)
        return False
    except (TypeError, ValueError):
        return True


def _table_input(session, table):
    comment = (table.custom_comment or table.table_comment or "").strip()
    result = (
        f"# Table: {table.table_name}" + (f", {comment}" if comment else "") + "\n[\n"
    )
    fields = (
        session.query(CoreField)
        .filter(CoreField.table_id == table.id, CoreField.checked.is_(True))
        .order_by(CoreField.field_index, CoreField.id)
        .all()
    )
    lines = []
    for field in fields:
        comment = (field.custom_comment or field.field_comment or "").strip()
        lines.append(
            f"({field.field_name}:{field.field_type}"
            + (f", {comment}" if comment else "")
            + ")"
        )
    return result + ",\n".join(lines) + "\n]\n"


def _resource_input(session, record):
    if isinstance(record, CoreTable):
        return _table_input(session, record)
    tables = (
        session.query(CoreTable)
        .filter(CoreTable.ds_id == record.id, CoreTable.checked.is_(True))
        .order_by(CoreTable.id)
        .all()
    )
    return f"{record.name}, {record.description}\n" + "".join(
        _table_input(session, table) for table in tables
    )


def _generate(session_maker, resource, ids=None, config=None):
    session = session_maker()
    failed = []
    try:
        config = config or load_embedding_config(session)
        if not config.table_enabled:
            return
        query = select(resource.id, resource.embedding).order_by(resource.id)
        if ids is not None:
            query = query.where(resource.id.in_(ids))
        pending = [key for key, vector in session.execute(query) if _missing(vector)]
        session.commit()
        for key in pending:
            for attempt in range(3):
                try:
                    lock_embedding_resource(session, resource.__tablename__, key)
                    session.expire_all()
                    record = session.get(resource, key)
                    if record is None or not _missing(record.embedding):
                        session.commit()
                        break
                    original = _resource_input(session, record)
                    vector = parse_valid_embedding(
                        EmbeddingModelCache.get_model().embed_query(original)
                    )
                    # Writers invalidate parent first, then child, in the same
                    # transaction as metadata. Match that order for publication.
                    # The provider call above holds no business row locks.
                    ds_id = record.ds_id if resource is CoreTable else key
                    parent = session.execute(
                        select(CoreDatasource.id)
                        .where(CoreDatasource.id == ds_id)
                        .with_for_update()
                    ).scalar_one_or_none()
                    if parent is None:
                        session.rollback()
                        break
                    if resource is CoreTable:
                        session.execute(
                            select(CoreTable.id)
                            .where(CoreTable.id == key)
                            .with_for_update()
                        ).all()
                    session.expire_all()
                    current = session.get(resource, key)
                    if current is None:
                        session.rollback()
                        break
                    if original != _resource_input(session, current):
                        session.rollback()
                        if attempt == 2:
                            failed.append(key)
                        continue
                    if _missing(current.embedding):
                        session.execute(
                            update(resource)
                            .where(resource.id == key)
                            .values(
                                embedding=json.dumps([float(value) for value in vector])
                            )
                        )
                    session.commit()
                    break
                except Exception:
                    session.rollback()
                    if attempt == 2:
                        failed.append(key)
                        SQLBotLogUtil.exception(
                            "Embedding remains pending for %s: %s",
                            resource.__tablename__,
                            key,
                        )
        if failed:
            raise EmbeddingGenerationError(resource.__tablename__, failed)
    finally:
        session_maker.remove()


def run_fill_empty_table_and_ds_embedding(session_maker):
    # Each startup/reenable is an independent recoverable scan. Resource locks
    # deduplicate work across workers and are released even when a process dies.
    session = session_maker()
    try:
        config = load_embedding_config(session)
    finally:
        session_maker.remove()
    if not config.table_enabled:
        return
    failures = []
    for resource in (CoreTable, CoreDatasource):
        try:
            _generate(session_maker, resource, config=config)
        except EmbeddingGenerationError as exc:
            failures.extend(exc.ids)
    if failures:
        raise EmbeddingGenerationError("datasource_metadata", failures)


def save_table_embedding(session_maker, ids: list[int]):
    _generate(session_maker, CoreTable, ids)


def save_ds_embedding(session_maker, ids: list[int]):
    _generate(session_maker, CoreDatasource, ids)
