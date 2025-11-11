import datetime
import logging
import traceback
from typing import List, Optional
from xml.dom.minidom import parseString

import dicttoxml
from sqlalchemy import and_, select, func, delete, update, or_
from sqlalchemy import text

from apps.ai_model.embedding import EmbeddingModelCache
from apps.data_training.models.data_training_model import DataTrainingInfo, DataTraining, DataTrainingInfoResult
from apps.datasource.models.datasource import CoreDatasource
from apps.system.models.system_model import AssistantModel
from apps.template.generate_chart.generator import get_base_data_training_template
from common.core.config import settings
from common.core.deps import SessionDep, Trans
from common.utils.embedding_threads import run_save_data_training_embeddings


def page_data_training(session: SessionDep, current_page: int = 1, page_size: int = 10, name: Optional[str] = None,
                       oid: Optional[int] = 1):
    _list: List[DataTrainingInfoResult] = []

    current_page = max(1, current_page)
    page_size = max(10, page_size)

    total_count = 0
    total_pages = 0

    if name and name.strip() != "":
        keyword_pattern = f"%{name.strip()}%"
        parent_ids_subquery = (
            select(DataTraining.id)
            .where(and_(DataTraining.question.ilike(keyword_pattern), DataTraining.oid == oid))  # LIKE查询条件
        )
    else:
        parent_ids_subquery = (
            select(DataTraining.id).where(and_(DataTraining.oid == oid))
        )

    count_stmt = select(func.count()).select_from(parent_ids_subquery.subquery())
    total_count = session.execute(count_stmt).scalar()
    total_pages = (total_count + page_size - 1) // page_size

    if current_page > total_pages:
        current_page = 1

    paginated_parent_ids = (
        parent_ids_subquery
        .order_by(DataTraining.create_time.desc())
        .offset((current_page - 1) * page_size)
        .limit(page_size)
        .subquery()
    )

    stmt = (
        select(
            DataTraining.id,
            DataTraining.oid,
            DataTraining.datasource,
            CoreDatasource.name,
            DataTraining.question,
            DataTraining.create_time,
            DataTraining.description,
            DataTraining.enabled,
            DataTraining.advanced_application,
            AssistantModel.name.label('advanced_application_name'),
        )
        .outerjoin(CoreDatasource, and_(DataTraining.datasource == CoreDatasource.id))
        .outerjoin(AssistantModel,
                   and_(DataTraining.advanced_application == AssistantModel.id, AssistantModel.type == 1))
        .where(and_(DataTraining.id.in_(paginated_parent_ids)))
        .order_by(DataTraining.create_time.desc())
    )

    result = session.execute(stmt)

    for row in result:
        _list.append(DataTrainingInfoResult(
            id=str(row.id),
            oid=str(row.oid),
            datasource=row.datasource,
            datasource_name=row.name,
            question=row.question,
            create_time=row.create_time,
            description=row.description,
            enabled=row.enabled,
            advanced_application=str(row.advanced_application) if row.advanced_application else None,
            advanced_application_name=row.advanced_application_name,
        ))

    return current_page, page_size, total_count, total_pages, _list


def create_training(session: SessionDep, info: DataTrainingInfo, oid: int, trans: Trans):
    create_time = datetime.datetime.now()
    if info.datasource is None and info.advanced_application is None:
        if oid == 1:
            raise Exception(trans("i18n_data_training.datasource_assistant_cannot_be_none"))
        else:
            raise Exception(trans("i18n_data_training.datasource_cannot_be_none"))

    parent = DataTraining(question=info.question, create_time=create_time, description=info.description, oid=oid,
                          datasource=info.datasource, enabled=info.enabled,
                          advanced_application=info.advanced_application)

    stmt = select(DataTraining.id).where(and_(DataTraining.question == info.question, DataTraining.oid == oid))

    if info.datasource is not None and info.advanced_application is not None:
        stmt = stmt.where(
            or_(DataTraining.datasource == info.datasource,
                DataTraining.advanced_application == info.advanced_application))
    elif info.datasource is not None and info.advanced_application is None:
        stmt = stmt.where(and_(DataTraining.datasource == info.datasource))
    elif info.datasource is None and info.advanced_application is not None:
        stmt = stmt.where(and_(DataTraining.advanced_application == info.advanced_application))

    exists = session.query(stmt.exists()).scalar()

    if exists:
        raise Exception(trans("i18n_data_training.exists_in_db"))

    result = DataTraining(**parent.model_dump())

    session.add(parent)
    session.flush()
    session.refresh(parent)

    result.id = parent.id
    session.commit()

    # embedding
    run_save_data_training_embeddings([result.id])

    return result.id


def update_training(session: SessionDep, info: DataTrainingInfo, oid: int, trans: Trans):
    if info.datasource is None and info.advanced_application is None:
        if oid == 1:
            raise Exception(trans("i18n_data_training.datasource_assistant_cannot_be_none"))
        else:
            raise Exception(trans("i18n_data_training.datasource_cannot_be_none"))

    count = session.query(DataTraining).filter(
        DataTraining.id == info.id
    ).count()
    if count == 0:
        raise Exception(trans('i18n_data_training.data_training_not_exists'))

    stmt = select(DataTraining.id).where(
        and_(DataTraining.question == info.question, DataTraining.oid == oid, DataTraining.id != info.id))

    if info.datasource is not None and info.advanced_application is not None:
        stmt = stmt.where(
            or_(DataTraining.datasource == info.datasource,
                DataTraining.advanced_application == info.advanced_application))
    elif info.datasource is not None and info.advanced_application is None:
        stmt = stmt.where(and_(DataTraining.datasource == info.datasource))
    elif info.datasource is None and info.advanced_application is not None:
        stmt = stmt.where(and_(DataTraining.advanced_application == info.advanced_application))

    exists = session.query(stmt.exists()).scalar()

    if exists:
        raise Exception(trans("i18n_data_training.exists_in_db"))

    stmt = update(DataTraining).where(and_(DataTraining.id == info.id)).values(
        question=info.question,
        description=info.description,
        datasource=info.datasource,
        enabled=info.enabled,
        advanced_application=info.advanced_application,
    )
    session.execute(stmt)
    session.commit()

    # embedding
    run_save_data_training_embeddings([info.id])

    return info.id


def delete_training(session: SessionDep, ids: list[int]):
    stmt = delete(DataTraining).where(and_(DataTraining.id.in_(ids)))
    session.execute(stmt)
    session.commit()


def enable_training(session: SessionDep, id: int, enabled: bool, trans: Trans):
    count = session.query(DataTraining).filter(
        DataTraining.id == id
    ).count()
    if count == 0:
        raise Exception(trans('i18n_data_training.data_training_not_exists'))

    stmt = update(DataTraining).where(and_(DataTraining.id == id)).values(
        enabled=enabled,
    )
    session.execute(stmt)
    session.commit()


# def run_save_embeddings(ids: List[int]):
#     executor.submit(save_embeddings, ids)
#
#
# def fill_empty_embeddings():
#     executor.submit(run_fill_empty_embeddings)


def run_fill_empty_embeddings(session_maker):
    try:
        if not settings.EMBEDDING_ENABLED:
            return

        session = session_maker()
        stmt = select(DataTraining.id).where(and_(DataTraining.embedding.is_(None)))
        results = session.execute(stmt).scalars().all()

        save_embeddings(session_maker, results)
    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


def save_embeddings(session_maker, ids: List[int]):
    if not settings.EMBEDDING_ENABLED:
        return

    if not ids or len(ids) == 0:
        return
    try:
        session = session_maker()
        _list = session.query(DataTraining).filter(and_(DataTraining.id.in_(ids))).all()

        _question_list = [item.question for item in _list]

        model = EmbeddingModelCache.get_model()

        results = model.embed_documents(_question_list)

        for index in range(len(results)):
            item = results[index]
            stmt = update(DataTraining).where(and_(DataTraining.id == _list[index].id)).values(embedding=item)
            session.execute(stmt)
            session.commit()

    except Exception:
        traceback.print_exc()
    finally:
        session_maker.remove()


embedding_sql = f"""
SELECT id, datasource, question, similarity
FROM
(SELECT id, datasource, question, oid, enabled,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM data_training AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_DATA_TRAINING_SIMILARITY} and oid = :oid and datasource = :datasource and enabled = true
ORDER BY similarity DESC
LIMIT {settings.EMBEDDING_DATA_TRAINING_TOP_COUNT}
"""
embedding_sql_in_advanced_application = f"""
SELECT id, advanced_application, question, similarity
FROM
(SELECT id, advanced_application, question, oid, enabled,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM data_training AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_DATA_TRAINING_SIMILARITY} and oid = :oid and advanced_application = :advanced_application and enabled = true
ORDER BY similarity DESC
LIMIT {settings.EMBEDDING_DATA_TRAINING_TOP_COUNT}
"""


def select_training_by_question(session: SessionDep, question: str, oid: int, datasource: Optional[int] = None,
                                advanced_application_id: Optional[int] = None):
    if question.strip() == "":
        return []

    _list: List[DataTraining] = []

    # maybe use label later?
    stmt = (
        select(
            DataTraining.id,
            DataTraining.question,
        )
        .where(
            and_(or_(text(":sentence ILIKE '%' || question || '%'"), text("question ILIKE '%' || :sentence || '%'")),
                 DataTraining.oid == oid,
                 DataTraining.enabled == True)
        )
    )
    if advanced_application_id is not None:
        stmt = stmt.where(and_(DataTraining.advanced_application == advanced_application_id))
    else:
        stmt = stmt.where(and_(DataTraining.datasource == datasource))

    results = session.execute(stmt, {'sentence': question}).fetchall()

    for row in results:
        _list.append(DataTraining(id=row.id, question=row.question))

    if settings.EMBEDDING_ENABLED:
        with session.begin_nested():
            try:
                model = EmbeddingModelCache.get_model()

                embedding = model.embed_query(question)

                if advanced_application_id is not None:
                    results = session.execute(text(embedding_sql_in_advanced_application),
                                              {'embedding_array': str(embedding), 'oid': oid,
                                               'advanced_application': advanced_application_id})
                else:
                    results = session.execute(text(embedding_sql),
                                              {'embedding_array': str(embedding), 'oid': oid, 'datasource': datasource})

                for row in results:
                    _list.append(DataTraining(id=row.id, question=row.question))

            except Exception:
                traceback.print_exc()
                session.rollback()

    _map: dict = {}
    _ids: list[int] = []
    for row in _list:
        if row.id in _ids:
            continue
        else:
            _ids.append(row.id)

    if len(_ids) == 0:
        return []

    t_list = session.query(DataTraining.id, DataTraining.question, DataTraining.description).filter(
        and_(DataTraining.id.in_(_ids))).all()

    for row in t_list:
        _map[row.id] = {'question': row.question, 'suggestion-answer': row.description}

    _results: list[dict] = []
    for key in _map.keys():
        _results.append(_map.get(key))

    return _results


def to_xml_string(_dict: list[dict] | dict, root: str = 'sql-examples') -> str:
    item_name_func = lambda x: 'sql-example' if x == 'sql-examples' else 'item'
    dicttoxml.LOG.setLevel(logging.ERROR)
    xml = dicttoxml.dicttoxml(_dict,
                              cdata=['question', 'suggestion-answer'],
                              custom_root=root,
                              item_func=item_name_func,
                              xml_declaration=False,
                              encoding='utf-8',
                              attr_type=False).decode('utf-8')
    pretty_xml = parseString(xml).toprettyxml()

    if pretty_xml.startswith('<?xml'):
        end_index = pretty_xml.find('>') + 1
        pretty_xml = pretty_xml[end_index:].lstrip()

    # 替换所有 XML 转义字符
    escape_map = {
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&',
        '&quot;': '"',
        '&apos;': "'"
    }
    for escaped, original in escape_map.items():
        pretty_xml = pretty_xml.replace(escaped, original)

    return pretty_xml


def get_training_template(session: SessionDep, question: str, oid: Optional[int] = 1, datasource: Optional[int] = None,
                          advanced_application_id: Optional[int] = None) -> str:
    if not oid:
        oid = 1
    if not datasource and not advanced_application_id:
        return ''
    _results = select_training_by_question(session, question, oid, datasource, advanced_application_id)
    if _results and len(_results) > 0:
        data_training = to_xml_string(_results)
        template = get_base_data_training_template().format(data_training=data_training)
        return template
    else:
        return ''
