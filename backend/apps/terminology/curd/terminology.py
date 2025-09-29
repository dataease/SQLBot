import datetime
import logging
import traceback
from typing import List, Optional, Any
from xml.dom.minidom import parseString

import dicttoxml
from sqlalchemy import and_, or_, select, func, delete, update, union, text, BigInteger
from sqlalchemy.orm import aliased
from sqlalchemy.orm.session import Session

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.models.datasource import CoreDatasource
from apps.template.generate_chart.generator import get_base_terminology_template
from apps.terminology.models.terminology_model import Terminology, TerminologyInfo
from common.core.config import settings
from common.core.deps import SessionDep, Trans
from common.utils.embedding_threads import run_save_terminology_embeddings


def page_terminology(session: SessionDep, current_page: int = 1, page_size: int = 10, name: Optional[str] = None,
                     oid: Optional[int] = 1):
    _list: List[TerminologyInfo] = []

    child = aliased(Terminology)

    current_page = max(1, current_page)
    page_size = max(10, page_size)

    total_count = 0
    total_pages = 0

    if name and name.strip() != "":
        keyword_pattern = f"%{name.strip()}%"
        # 步骤1：先找到所有匹配的节点ID（无论是父节点还是子节点）
        matched_ids_subquery = (
            select(Terminology.id)
            .where(and_(Terminology.word.ilike(keyword_pattern), Terminology.oid == oid))  # LIKE查询条件
            .subquery()
        )

        # 步骤2：找到这些匹配节点的所有父节点（包括自身如果是父节点）
        parent_ids_subquery = (
            select(Terminology.id)
            .where(
                (Terminology.id.in_(matched_ids_subquery)) |
                (Terminology.id.in_(
                    select(Terminology.pid)
                    .where(Terminology.id.in_(matched_ids_subquery))
                    .where(Terminology.pid.isnot(None))
                ))
            )
            .where(Terminology.pid.is_(None))  # 只取父节点
        )

        count_stmt = select(func.count()).select_from(parent_ids_subquery.subquery())
        total_count = session.execute(count_stmt).scalar()
        total_pages = (total_count + page_size - 1) // page_size

        if current_page > total_pages:
            current_page = 1

        # 步骤3：获取分页后的父节点ID
        paginated_parent_ids = (
            parent_ids_subquery
            .order_by(Terminology.create_time.desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )

        # 步骤4：获取这些父节点的childrenNames
        children_subquery = (
            select(
                child.pid,
                func.jsonb_agg(child.word).filter(child.word.isnot(None)).label('other_words')
            )
            .where(child.pid.isnot(None))
            .group_by(child.pid)
            .subquery()
        )

        # 创建子查询来获取数据源名称，添加类型转换
        datasource_names_subquery = (
            select(
                func.jsonb_array_elements(Terminology.datasource_ids).cast(BigInteger).label('ds_id'),
                Terminology.id.label('term_id')
            )
            .where(Terminology.id.in_(paginated_parent_ids))
            .subquery()
        )

        # 主查询
        stmt = (
            select(
                Terminology.id,
                Terminology.word,
                Terminology.create_time,
                Terminology.description,
                Terminology.specific_ds,
                Terminology.datasource_ids,
                children_subquery.c.other_words,
                func.jsonb_agg(CoreDatasource.name).filter(CoreDatasource.id.isnot(None)).label('datasource_names')
            )
            .outerjoin(
                children_subquery,
                Terminology.id == children_subquery.c.pid
            )
            # 关联数据源名称子查询和 CoreDatasource 表
            .outerjoin(
                datasource_names_subquery,
                datasource_names_subquery.c.term_id == Terminology.id
            )
            .outerjoin(
                CoreDatasource,
                CoreDatasource.id == datasource_names_subquery.c.ds_id
            )
            .where(and_(Terminology.id.in_(paginated_parent_ids), Terminology.oid == oid))
            .group_by(
                Terminology.id,
                Terminology.word,
                Terminology.create_time,
                Terminology.description,
                Terminology.specific_ds,
                Terminology.datasource_ids,
                children_subquery.c.other_words
            )
            .order_by(Terminology.create_time.desc())
        )
    else:
        parent_ids_subquery = (
            select(Terminology.id)
            .where(and_(Terminology.pid.is_(None), Terminology.oid == oid))  # 只取父节点
        )
        count_stmt = select(func.count()).select_from(parent_ids_subquery.subquery())
        total_count = session.execute(count_stmt).scalar()
        total_pages = (total_count + page_size - 1) // page_size

        if current_page > total_pages:
            current_page = 1

        paginated_parent_ids = (
            parent_ids_subquery
            .order_by(Terminology.create_time.desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )

        children_subquery = (
            select(
                child.pid,
                func.jsonb_agg(child.word).filter(child.word.isnot(None)).label('other_words')
            )
            .where(child.pid.isnot(None))
            .group_by(child.pid)
            .subquery()
        )

        # 创建子查询来获取数据源名称
        datasource_names_subquery = (
            select(
                func.jsonb_array_elements(Terminology.datasource_ids).cast(BigInteger).label('ds_id'),
                Terminology.id.label('term_id')
            )
            .where(Terminology.id.in_(paginated_parent_ids))
            .subquery()
        )

        stmt = (
            select(
                Terminology.id,
                Terminology.word,
                Terminology.create_time,
                Terminology.description,
                Terminology.specific_ds,
                Terminology.datasource_ids,
                children_subquery.c.other_words,
                func.jsonb_agg(CoreDatasource.name).filter(CoreDatasource.id.isnot(None)).label('datasource_names')
            )
            .outerjoin(
                children_subquery,
                Terminology.id == children_subquery.c.pid
            )
            # 关联数据源名称子查询和 CoreDatasource 表
            .outerjoin(
                datasource_names_subquery,
                datasource_names_subquery.c.term_id == Terminology.id
            )
            .outerjoin(
                CoreDatasource,
                CoreDatasource.id == datasource_names_subquery.c.ds_id
            )
            .where(and_(Terminology.id.in_(paginated_parent_ids), Terminology.oid == oid))
            .group_by(Terminology.id,
                      Terminology.word,
                      Terminology.create_time,
                      Terminology.description,
                      Terminology.specific_ds,
                      Terminology.datasource_ids,
                      children_subquery.c.other_words
                      )
            .order_by(Terminology.create_time.desc())
        )

    result = session.execute(stmt)

    for row in result:
        _list.append(TerminologyInfo(
            id=row.id,
            word=row.word,
            create_time=row.create_time,
            description=row.description,
            other_words=row.other_words if row.other_words else [],
            specific_ds=row.specific_ds if row.specific_ds is not None else False,
            datasource_ids=row.datasource_ids if row.datasource_ids is not None else [],
            datasource_names=row.datasource_names if row.datasource_names is not None else [],
        ))

    return current_page, page_size, total_count, total_pages, _list


def create_terminology(session: SessionDep, info: TerminologyInfo, oid: int, trans: Trans):
    create_time = datetime.datetime.now()

    specific_ds = info.specific_ds if info.specific_ds is not None else False
    datasource_ids = info.datasource_ids if info.datasource_ids is not None else []

    if specific_ds:
        if not datasource_ids:
            raise Exception(trans("i18n_terminology.datasource_cannot_be_none"))

    parent = Terminology(word=info.word, create_time=create_time, description=info.description, oid=oid,
                         specific_ds=specific_ds,
                         datasource_ids=datasource_ids)

    words = [info.word]
    for child in info.other_words:
        if child in words:
            raise Exception(trans("i18n_terminology.cannot_be_repeated"))
        else:
            words.append(child)

    # 基础查询条件（word 和 oid 必须满足）
    base_query = and_(
        Terminology.word.in_(words),
        Terminology.oid == oid
    )

    # 构建查询
    query = session.query(Terminology).filter(base_query)

    if specific_ds:
        # 仅当 specific_ds=False 时，检查数据源条件
        query = query.where(
            or_(
                or_(Terminology.specific_ds == False, Terminology.specific_ds.is_(None)),
                and_(
                    Terminology.specific_ds == True,
                    Terminology.datasource_ids.isnot(None),
                    text("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(datasource_ids) AS elem
                            WHERE elem::text::int = ANY(:datasource_ids)
                        )
                    """)  # 检查是否包含任意目标值
                )
            )
        )
        query = query.params(datasource_ids=datasource_ids)

    # 转换为 EXISTS 查询并获取结果
    exists = session.query(query.exists()).scalar()

    if exists:
        raise Exception(trans("i18n_terminology.exists_in_db"))

    result = Terminology(**parent.model_dump())

    session.add(parent)
    session.flush()
    session.refresh(parent)

    result.id = parent.id
    session.commit()

    _list: List[Terminology] = []
    if info.other_words:
        for other_word in info.other_words:
            if other_word.strip() == "":
                continue
            _list.append(
                Terminology(pid=result.id, word=other_word, create_time=create_time, oid=oid,
                            specific_ds=specific_ds, datasource_ids=datasource_ids))
    session.bulk_save_objects(_list)
    session.flush()
    session.commit()

    # embedding
    run_save_terminology_embeddings([result.id])

    return result.id


def update_terminology(session: SessionDep, info: TerminologyInfo, oid: int, trans: Trans):
    count = session.query(Terminology).filter(
        Terminology.oid == oid,
        Terminology.id == info.id
    ).count()
    if count == 0:
        raise Exception(trans('i18n_terminology.terminology_not_exists'))

    specific_ds = info.specific_ds if info.specific_ds is not None else False
    datasource_ids = info.datasource_ids if info.datasource_ids is not None else []

    if specific_ds:
        if not datasource_ids:
            raise Exception(trans("i18n_terminology.datasource_cannot_be_none"))

    words = [info.word]
    for child in info.other_words:
        if child in words:
            raise Exception(trans("i18n_terminology.cannot_be_repeated"))
        else:
            words.append(child)

    # 基础查询条件（word 和 oid 必须满足）
    base_query = and_(
        Terminology.word.in_(words),
        Terminology.oid == oid,
        or_(
            Terminology.pid != info.id,
            and_(Terminology.pid.is_(None), Terminology.id != info.id)
        ),
        Terminology.id != info.id
    )

    # 构建查询
    query = session.query(Terminology).filter(base_query)

    if specific_ds:
        # 仅当 specific_ds=False 时，检查数据源条件
        query = query.where(
            or_(
                or_(Terminology.specific_ds == False, Terminology.specific_ds.is_(None)),
                and_(
                    Terminology.specific_ds == True,
                    Terminology.datasource_ids.isnot(None),
                    text("""
                        EXISTS (
                            SELECT 1 FROM jsonb_array_elements(datasource_ids) AS elem
                            WHERE elem::text::int = ANY(:datasource_ids)
                        )
                    """)  # 检查是否包含任意目标值
                )
            )
        )
        query = query.params(datasource_ids=datasource_ids)

    # 转换为 EXISTS 查询并获取结果
    exists = session.query(query.exists()).scalar()

    if exists:
        raise Exception(trans("i18n_terminology.exists_in_db"))

    stmt = update(Terminology).where(and_(Terminology.id == info.id)).values(
        word=info.word,
        description=info.description,
        specific_ds=specific_ds,
        datasource_ids=datasource_ids
    )
    session.execute(stmt)
    session.commit()

    stmt = delete(Terminology).where(and_(Terminology.pid == info.id))
    session.execute(stmt)
    session.commit()

    create_time = datetime.datetime.now()
    _list: List[Terminology] = []
    if info.other_words:
        for other_word in info.other_words:
            if other_word.strip() == "":
                continue
            _list.append(
                Terminology(pid=info.id, word=other_word, create_time=create_time, oid=oid,
                            specific_ds=specific_ds, datasource_ids=datasource_ids))
    session.bulk_save_objects(_list)
    session.flush()
    session.commit()

    # embedding
    run_save_terminology_embeddings([info.id])

    return info.id


def delete_terminology(session: SessionDep, ids: list[int]):
    stmt = delete(Terminology).where(or_(Terminology.id.in_(ids), Terminology.pid.in_(ids)))
    session.execute(stmt)
    session.commit()


# def run_save_embeddings(ids: List[int]):
#     executor.submit(save_embeddings, ids)
#
#
# def fill_empty_embeddings():
#     executor.submit(run_fill_empty_embeddings)


def run_fill_empty_embeddings(session: Session):
    if not settings.EMBEDDING_ENABLED:
        return
    stmt1 = select(Terminology.id).where(and_(Terminology.embedding.is_(None), Terminology.pid.is_(None)))
    stmt2 = select(Terminology.pid).where(and_(Terminology.embedding.is_(None), Terminology.pid.isnot(None))).distinct()
    combined_stmt = union(stmt1, stmt2)
    results = session.execute(combined_stmt).scalars().all()
    save_embeddings(session, results)


def save_embeddings(session: Session, ids: List[int]):
    if not settings.EMBEDDING_ENABLED:
        return

    if not ids or len(ids) == 0:
        return
    try:

        _list = session.query(Terminology).filter(or_(Terminology.id.in_(ids), Terminology.pid.in_(ids))).all()

        _words_list = [item.word for item in _list]

        model = EmbeddingModelCache.get_model()

        results = model.embed_documents(_words_list)

        for index in range(len(results)):
            item = results[index]
            stmt = update(Terminology).where(and_(Terminology.id == _list[index].id)).values(embedding=item)
            session.execute(stmt)
            session.commit()

    except Exception:
        traceback.print_exc()


embedding_sql = f"""
SELECT id, pid, word, similarity
FROM
(SELECT id, pid, word, oid, specific_ds, datasource_ids,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM terminology AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_TERMINOLOGY_SIMILARITY} AND oid = :oid
AND (specific_ds = false OR specific_ds IS NULL)
ORDER BY similarity DESC
LIMIT {settings.EMBEDDING_TERMINOLOGY_TOP_COUNT}
"""

embedding_sql_with_datasource = f"""
SELECT id, pid, word, similarity
FROM
(SELECT id, pid, word, oid, specific_ds, datasource_ids,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM terminology AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_TERMINOLOGY_SIMILARITY} AND oid = :oid
AND (
    (specific_ds = false OR specific_ds IS NULL)
     OR
    (specific_ds = true AND datasource_ids IS NOT NULL AND datasource_ids @> jsonb_build_array(:datasource))
)
ORDER BY similarity DESC
LIMIT {settings.EMBEDDING_TERMINOLOGY_TOP_COUNT}
"""


def select_terminology_by_word(session: SessionDep, word: str, oid: int, datasource: int = None):
    if word.strip() == "":
        return []

    _list: List[Terminology] = []

    stmt = (
        select(
            Terminology.id,
            Terminology.pid,
            Terminology.word,
        )
        .where(
            and_(text(":sentence ILIKE '%' || word || '%'"), Terminology.oid == oid)
        )
    )

    if datasource is not None:
        stmt = stmt.where(
            or_(
                or_(Terminology.specific_ds == False, Terminology.specific_ds.is_(None)),
                and_(
                    Terminology.specific_ds == True,
                    Terminology.datasource_ids.isnot(None),
                    text("datasource_ids @> jsonb_build_array(:datasource)")
                )
            )
        )
    else:
        stmt = stmt.where(or_(Terminology.specific_ds == False, Terminology.specific_ds.is_(None)))

    # 执行查询
    params: dict[str, Any] = {'sentence': word}
    if datasource is not None:
        params['datasource'] = datasource

    results = session.execute(stmt, params).fetchall()

    for row in results:
        _list.append(Terminology(id=row.id, word=row.word, pid=row.pid))

    if settings.EMBEDDING_ENABLED:
        with session.begin_nested():
            try:
                model = EmbeddingModelCache.get_model()

                embedding = model.embed_query(word)

                if datasource is not None:
                    results = session.execute(text(embedding_sql_with_datasource),
                                              {'embedding_array': str(embedding), 'oid': oid,
                                               'datasource': datasource}).fetchall()
                else:
                    results = session.execute(text(embedding_sql),
                                              {'embedding_array': str(embedding), 'oid': oid}).fetchall()

                for row in results:
                    _list.append(Terminology(id=row.id, word=row.word, pid=row.pid))

            except Exception:
                traceback.print_exc()
                session.rollback()

    _map: dict = {}
    _ids: list[int] = []
    for row in _list:
        if row.id in _ids or row.pid in _ids:
            continue
        if row.pid is not None:
            _ids.append(row.pid)
        else:
            _ids.append(row.id)

    if len(_ids) == 0:
        return []

    t_list = session.query(Terminology.id, Terminology.pid, Terminology.word, Terminology.description).filter(
        or_(Terminology.id.in_(_ids), Terminology.pid.in_(_ids))).all()
    for row in t_list:
        pid = str(row.pid) if row.pid is not None else str(row.id)
        if _map.get(pid) is None:
            _map[pid] = {'words': [], 'description': row.description}
        _map[pid]['words'].append(row.word)

    _results: list[dict] = []
    for key in _map.keys():
        _results.append(_map.get(key))

    return _results


def get_example():
    _obj = {
        'terminologies': [
            {'words': ['GDP', '国内生产总值'],
             'description': '指在一个季度或一年，一个国家或地区的经济中所生产出的全部最终产品和劳务的价值。'},
        ]
    }
    return to_xml_string(_obj, 'example')


def to_xml_string(_dict: list[dict] | dict, root: str = 'terminologies') -> str:
    item_name_func = lambda x: 'terminology' if x == 'terminologies' else 'word' if x == 'words' else 'item'
    dicttoxml.LOG.setLevel(logging.ERROR)
    xml = dicttoxml.dicttoxml(_dict,
                              cdata=['word', 'description'],
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


def get_terminology_template(session: SessionDep, question: str, oid: Optional[int] = 1,
                             datasource: Optional[int] = None) -> str:
    if not oid:
        oid = 1
    _results = select_terminology_by_word(session, question, oid, datasource)
    if _results and len(_results) > 0:
        terminology = to_xml_string(_results)
        template = get_base_terminology_template().format(terminologies=terminology)
        return template
    else:
        return ''
