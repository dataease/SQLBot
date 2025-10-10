import json
import time
import traceback
from typing import List

from sqlalchemy import and_, select, update

from apps.ai_model.embedding import EmbeddingModelCache
from common.core.config import settings
from common.core.deps import SessionDep
from common.utils.utils import SQLBotLogUtil
from ..models.datasource import CoreTable, CoreField, CoreDatasource


def delete_table_by_ds_id(session: SessionDep, id: int):
    session.query(CoreTable).filter(CoreTable.ds_id == id).delete(synchronize_session=False)
    session.commit()


def get_tables_by_ds_id(session: SessionDep, id: int):
    return session.query(CoreTable).filter(CoreTable.ds_id == id).order_by(
        CoreTable.table_name.asc()).all()


def update_table(session: SessionDep, item: CoreTable):
    record = session.query(CoreTable).filter(CoreTable.id == item.id).first()
    record.checked = item.checked
    record.custom_comment = item.custom_comment
    session.add(record)
    session.commit()


def run_fill_empty_table_and_ds_embedding(session_maker):
    try:
        if not settings.TABLE_EMBEDDING_ENABLED:
            return

        session = session_maker()

        SQLBotLogUtil.info('get tables')
        stmt = select(CoreTable.id).where(and_(CoreTable.embedding.is_(None)))
        results = session.execute(stmt).scalars().all()
        SQLBotLogUtil.info('table result: ' + str(len(results)))
        save_table_embedding(session_maker, results)

        SQLBotLogUtil.info('get datasource')
        ds_stmt = select(CoreDatasource.id).where(and_(CoreDatasource.embedding.is_(None)))
        ds_results = session.execute(ds_stmt).scalars().all()
        SQLBotLogUtil.info('datasource result: ' + str(len(ds_results)))
        save_ds_embedding(session_maker, ds_results)
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


def save_table_embedding(session_maker, ids: List[int]):
    if not settings.TABLE_EMBEDDING_ENABLED:
        return

    if not ids or len(ids) == 0:
        return
    try:
        SQLBotLogUtil.info('start table embedding')
        start_time = time.time()
        model = EmbeddingModelCache.get_model()
        session = session_maker()
        for _id in ids:
            table = session.query(CoreTable).filter(CoreTable.id == _id).first()
            fields = session.query(CoreField).filter(CoreField.table_id == table.id).all()

            schema_table = ''
            schema_table += f"# Table: {table.table_name}"
            table_comment = ''
            if table.custom_comment:
                table_comment = table.custom_comment.strip()
            if table_comment == '':
                schema_table += '\n[\n'
            else:
                schema_table += f", {table_comment}\n[\n"

            if fields:
                field_list = []
                for field in fields:
                    field_comment = ''
                    if field.custom_comment:
                        field_comment = field.custom_comment.strip()
                    if field_comment == '':
                        field_list.append(f"({field.field_name}:{field.field_type})")
                    else:
                        field_list.append(f"({field.field_name}:{field.field_type}, {field_comment})")
                schema_table += ",\n".join(field_list)
            schema_table += '\n]\n'
            # table_schema.append(schema_table)
            emb = json.dumps(model.embed_query(schema_table))

            stmt = update(CoreTable).where(and_(CoreTable.id == _id)).values(embedding=emb)
            session.execute(stmt)
            session.commit()

        end_time = time.time()
        SQLBotLogUtil.info('table embedding finished in: ' + str(end_time - start_time) + ' seconds')
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


def save_ds_embedding(session_maker, ids: List[int]):
    if not settings.TABLE_EMBEDDING_ENABLED:
        return

    if not ids or len(ids) == 0:
        return
    try:
        SQLBotLogUtil.info('start datasource embedding')
        start_time = time.time()
        model = EmbeddingModelCache.get_model()
        session = session_maker()
        for _id in ids:
            schema_table = ''
            ds = session.query(CoreDatasource).filter(CoreDatasource.id == _id).first()
            schema_table += f"{ds.name}, {ds.description}\n"
            tables = session.query(CoreTable).filter(CoreTable.ds_id == ds.id).all()
            for table in tables:
                fields = session.query(CoreField).filter(CoreField.table_id == table.id).all()

                schema_table += f"# Table: {table.table_name}"
                table_comment = ''
                if table.custom_comment:
                    table_comment = table.custom_comment.strip()
                if table_comment == '':
                    schema_table += '\n[\n'
                else:
                    schema_table += f", {table_comment}\n[\n"

                if fields:
                    field_list = []
                    for field in fields:
                        field_comment = ''
                        if field.custom_comment:
                            field_comment = field.custom_comment.strip()
                        if field_comment == '':
                            field_list.append(f"({field.field_name}:{field.field_type})")
                        else:
                            field_list.append(f"({field.field_name}:{field.field_type}, {field_comment})")
                    schema_table += ",\n".join(field_list)
                schema_table += '\n]\n'
            # table_schema.append(schema_table)
            emb = json.dumps(model.embed_query(schema_table))

            stmt = update(CoreDatasource).where(and_(CoreDatasource.id == _id)).values(embedding=emb)
            session.execute(stmt)
            session.commit()

        end_time = time.time()
        SQLBotLogUtil.info('datasource embedding finished in: ' + str(end_time - start_time) + ' seconds')
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()
