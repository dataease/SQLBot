import datetime
import logging
import traceback
from typing import List, Optional, Any
from xml.dom.minidom import parseString

import dicttoxml
from sqlalchemy import and_, or_, select, func, delete, update, union, text, BigInteger
from sqlalchemy.orm import aliased

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.models.datasource import CoreDatasource
from apps.template.generate_chart.generator import get_base_terminology_template
from apps.terminology.models.terminology_model import Terminology, TerminologyInfo
from common.core.config import settings
from common.core.deps import SessionDep, Trans
from common.utils.embedding_threads import run_save_terminology_embeddings


def get_terminology_base_query(oid: int, name: Optional[str] = None):
    """
    获取术语查询的基础查询结构
    """
    child = aliased(Terminology)

    if name and name.strip() != "":
        keyword_pattern = f"%{name.strip()}%"
        # 步骤1：先找到所有匹配的节点ID（无论是父节点还是子节点）
        matched_ids_subquery = (
            select(Terminology.id)
            .where(and_(Terminology.word.ilike(keyword_pattern), Terminology.oid == oid))
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
    else:
        parent_ids_subquery = (
            select(Terminology.id)
            .where(and_(Terminology.pid.is_(None), Terminology.oid == oid))
        )

    return parent_ids_subquery, child


def build_terminology_query(session: SessionDep, oid: int, name: Optional[str] = None,
                            paginate: bool = True, current_page: int = 1, page_size: int = 10,
                            dslist: Optional[list[int]] = None):
    """
    构建术语查询的通用方法
    """
    parent_ids_subquery, child = get_terminology_base_query(oid, name)

    # 添加数据源筛选条件
    if dslist is not None and len(dslist) > 0:
        datasource_conditions = []
        # datasource_ids 与 dslist 中的任一元素有交集
        for ds_id in dslist:
            # 使用 JSONB 包含操作符，但需要确保类型正确
            datasource_conditions.append(
                Terminology.datasource_ids.contains([ds_id])
            )

        # datasource_ids 为空数组
        empty_array_condition = Terminology.datasource_ids == []

        ds_filter_condition = or_(
            *datasource_conditions,
            empty_array_condition
        )
        parent_ids_subquery = parent_ids_subquery.where(ds_filter_condition)

    # 计算总数
    count_stmt = select(func.count()).select_from(parent_ids_subquery.subquery())
    total_count = session.execute(count_stmt).scalar()

    if paginate:
        # 分页处理
        page_size = max(10, page_size)
        total_pages = (total_count + page_size - 1) // page_size
        current_page = max(1, min(current_page, total_pages)) if total_pages > 0 else 1

        paginated_parent_ids = (
            parent_ids_subquery
            .order_by(Terminology.create_time.desc())
            .offset((current_page - 1) * page_size)
            .limit(page_size)
            .subquery()
        )
    else:
        # 不分页，获取所有数据
        total_pages = 1
        current_page = 1
        page_size = total_count if total_count > 0 else 1

        paginated_parent_ids = (
            parent_ids_subquery
            .order_by(Terminology.create_time.desc())
            .subquery()
        )

    # 构建公共查询部分
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
            func.jsonb_agg(CoreDatasource.name).filter(CoreDatasource.id.isnot(None)).label('datasource_names'),
            Terminology.enabled
        )
        .outerjoin(
            children_subquery,
            Terminology.id == children_subquery.c.pid
        )
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
            children_subquery.c.other_words,
            Terminology.enabled
        )
        .order_by(Terminology.create_time.desc())
    )

    return stmt, total_count, total_pages, current_page, page_size


def execute_terminology_query(session: SessionDep, stmt) -> List[TerminologyInfo]:
    """
    执行查询并返回术语信息列表
    """
    _list = []
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
            enabled=row.enabled if row.enabled is not None else False,
        ))

    return _list


def page_terminology(session: SessionDep, current_page: int = 1, page_size: int = 10,
                     name: Optional[str] = None, oid: Optional[int] = 1, dslist: Optional[list[int]] = None):
    """
    分页查询术语（原方法保持不变）
    """
    stmt, total_count, total_pages, current_page, page_size = build_terminology_query(
        session, oid, name, True, current_page, page_size, dslist
    )
    _list = execute_terminology_query(session, stmt)

    return current_page, page_size, total_count, total_pages, _list


def get_all_terminology(session: SessionDep, name: Optional[str] = None, oid: Optional[int] = 1):
    """
    获取所有术语（不分页）
    """
    stmt, total_count, total_pages, current_page, page_size = build_terminology_query(
        session, oid, name, False
    )
    _list = execute_terminology_query(session, stmt)

    return _list


def create_terminology(session: SessionDep, info: TerminologyInfo, oid: int, trans: Trans,
                       skip_embedding: bool = False):
    """
    创建单个术语记录
    Args:
        skip_embedding: 是否跳过embedding处理（用于批量插入）
    """
    # 基本验证
    if not info.word or not info.word.strip():
        raise Exception(trans("i18n_terminology.word_cannot_be_empty"))

    if not info.description or not info.description.strip():
        raise Exception(trans("i18n_terminology.description_cannot_be_empty"))

    create_time = datetime.datetime.now()

    specific_ds = info.specific_ds if info.specific_ds is not None else False
    datasource_ids = info.datasource_ids if info.datasource_ids is not None else []

    if specific_ds:
        if not datasource_ids:
            raise Exception(trans("i18n_terminology.datasource_cannot_be_none"))

    parent = Terminology(
        word=info.word.strip(),
        create_time=create_time,
        description=info.description.strip(),
        oid=oid,
        specific_ds=specific_ds,
        enabled=info.enabled,
        datasource_ids=datasource_ids
    )

    words = [info.word.strip()]
    for child_word in info.other_words:
        # 先检查是否为空字符串
        if not child_word or child_word.strip() == "":
            continue

        if child_word in words:
            raise Exception(trans("i18n_terminology.cannot_be_repeated"))
        else:
            words.append(child_word.strip())

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
                    """)
                )
            )
        )
        query = query.params(datasource_ids=datasource_ids)

    # 转换为 EXISTS 查询并获取结果
    exists = session.query(query.exists()).scalar()

    if exists:
        raise Exception(trans("i18n_terminology.exists_in_db"))

    session.add(parent)
    session.flush()
    session.refresh(parent)

    # 插入子记录（其他词）
    child_list = []
    if info.other_words:
        for other_word in info.other_words:
            if other_word.strip() == "":
                continue
            child_list.append(
                Terminology(
                    pid=parent.id,
                    word=other_word.strip(),
                    create_time=create_time,
                    oid=oid,
                    enabled=info.enabled,
                    specific_ds=specific_ds,
                    datasource_ids=datasource_ids
                )
            )

    if child_list:
        session.bulk_save_objects(child_list)
        session.flush()

    session.commit()

    # 处理embedding（批量插入时跳过）
    if not skip_embedding:
        run_save_terminology_embeddings([parent.id])

    return parent.id


def batch_create_terminology(session: SessionDep, info_list: List[TerminologyInfo], oid: int, trans: Trans):
    """
    批量创建术语记录（复用单条插入逻辑）
    """
    if not info_list:
        return {
            'success_count': 0,
            'failed_records': [],
            'duplicate_count': 0,
            'original_count': 0,
            'deduplicated_count': 0
        }

    failed_records = []
    success_count = 0
    inserted_ids = []

    # 第一步：数据去重（根据新的唯一性规则）
    unique_records = {}
    duplicate_records = []

    for info in info_list:
        # 过滤掉空的其他词
        filtered_other_words = [w.strip().lower() for w in info.other_words if w and w.strip()]

        # 根据specific_ds决定是否处理datasource_names
        specific_ds = info.specific_ds if info.specific_ds is not None else False
        filtered_datasource_names = []

        if specific_ds and info.datasource_names:
            # 只有当specific_ds为True时才考虑数据源名称
            filtered_datasource_names = [d.strip().lower() for d in info.datasource_names if d and d.strip()]

        # 创建唯一标识（根据新的规则）
        # 1. word和other_words合并并排序（考虑顺序不同）
        all_words = [info.word.strip().lower()] if info.word else []
        all_words.extend(filtered_other_words)
        all_words_sorted = sorted(all_words)

        # 2. datasource_names排序（考虑顺序不同）
        datasource_names_sorted = sorted(filtered_datasource_names)

        unique_key = (
            ','.join(all_words_sorted),  # 合并后的所有词（排序）
            ','.join(datasource_names_sorted),  # 数据源名称（排序）
            str(specific_ds)  # specific_ds状态
        )

        if unique_key in unique_records:
            duplicate_records.append(info)
        else:
            unique_records[unique_key] = info

    # 将去重后的数据转换为列表
    deduplicated_list = list(unique_records.values())

    # 预加载数据源名称到ID的映射
    datasource_name_to_id = {}
    datasource_stmt = select(CoreDatasource.id, CoreDatasource.name).where(CoreDatasource.oid == oid)
    datasource_result = session.execute(datasource_stmt).all()
    for ds in datasource_result:
        datasource_name_to_id[ds.name.strip()] = ds.id

    # 验证和转换数据源名称
    valid_records = []
    for info in deduplicated_list:
        error_messages = []

        # 基本验证
        if not info.word or not info.word.strip():
            error_messages.append(trans("i18n_terminology.word_cannot_be_empty"))

        if not info.description or not info.description.strip():
            error_messages.append(trans("i18n_terminology.description_cannot_be_empty"))

        # 根据specific_ds决定是否验证数据源
        specific_ds = info.specific_ds if info.specific_ds is not None else False
        datasource_ids = []

        if specific_ds:
            # specific_ds为True时需要验证数据源
            if info.datasource_names:
                for ds_name in info.datasource_names:
                    if not ds_name or not ds_name.strip():
                        continue  # 跳过空的数据源名称

                    if ds_name.strip() in datasource_name_to_id:
                        datasource_ids.append(datasource_name_to_id[ds_name.strip()])
                    else:
                        error_messages.append(trans("i18n_terminology.datasource_not_found").format(ds_name))

            # 检查specific_ds为True时必须有数据源
            if not datasource_ids:
                error_messages.append(trans("i18n_terminology.datasource_cannot_be_none"))
        else:
            # specific_ds为False时忽略数据源名称
            datasource_ids = []

        # 检查主词和其他词是否重复（过滤空字符串）
        words = [info.word.strip().lower()]
        if info.other_words:
            for other_word in info.other_words:
                # 先检查是否为空字符串
                if not other_word or other_word.strip() == "":
                    continue

                word_lower = other_word.strip().lower()
                if word_lower in words:
                    error_messages.append(trans("i18n_terminology.cannot_be_repeated"))
                else:
                    words.append(word_lower)

        if error_messages:
            failed_records.append({
                'data': info,
                'errors': error_messages
            })
            continue

        # 创建新的TerminologyInfo对象
        processed_info = TerminologyInfo(
            word=info.word.strip(),
            description=info.description.strip(),
            other_words=[w for w in info.other_words if w and w.strip()],  # 过滤空字符串
            datasource_ids=datasource_ids,
            datasource_names=info.datasource_names,
            specific_ds=specific_ds,
            enabled=info.enabled if info.enabled is not None else True
        )

        valid_records.append(processed_info)

    # 使用事务批量处理有效记录
    if valid_records:
        for info in valid_records:
            try:
                # 直接复用create_terminology方法，跳过embedding处理
                terminology_id = create_terminology(session, info, oid, trans, skip_embedding=True)
                inserted_ids.append(terminology_id)
                success_count += 1

            except Exception as e:
                # 如果单条插入失败，回滚当前记录
                session.rollback()
                failed_records.append({
                    'data': info,
                    'errors': [str(e)]
                })

        # 批量处理embedding（只在最后执行一次）
        if success_count > 0 and inserted_ids:
            try:
                run_save_terminology_embeddings(inserted_ids)
            except Exception as e:
                # 如果embedding处理失败，记录错误但不回滚数据
                print(f"Terminology embedding processing failed: {str(e)}")
                # 可以选择将embedding失败的信息记录到日志或返回给调用方

    return {
        'success_count': success_count,
        'failed_records': failed_records,
        'duplicate_count': len(duplicate_records),
        'original_count': len(info_list),
        'deduplicated_count': len(deduplicated_list)
    }


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

    words = [info.word.strip()]
    for child in info.other_words:
        if child in words:
            raise Exception(trans("i18n_terminology.cannot_be_repeated"))
        else:
            words.append(child.strip())

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
        word=info.word.strip(),
        description=info.description.strip(),
        specific_ds=specific_ds,
        datasource_ids=datasource_ids,
        enabled=info.enabled,
    )
    session.execute(stmt)
    session.commit()

    stmt = delete(Terminology).where(and_(Terminology.pid == info.id))
    session.execute(stmt)
    session.commit()

    create_time = datetime.datetime.now()
    # 插入子记录（其他词）
    child_list = []
    if info.other_words:
        for other_word in info.other_words:
            if other_word.strip() == "":
                continue
            child_list.append(
                Terminology(
                    pid=info.id,
                    word=other_word.strip(),
                    create_time=create_time,
                    oid=oid,
                    enabled=info.enabled,
                    specific_ds=specific_ds,
                    datasource_ids=datasource_ids
                )
            )

    if child_list:
        session.bulk_save_objects(child_list)
        session.flush()
    session.commit()

    # embedding
    run_save_terminology_embeddings([info.id])

    return info.id


def delete_terminology(session: SessionDep, ids: list[int]):
    stmt = delete(Terminology).where(or_(Terminology.id.in_(ids), Terminology.pid.in_(ids)))
    session.execute(stmt)
    session.commit()


def enable_terminology(session: SessionDep, id: int, enabled: bool, trans: Trans):
    count = session.query(Terminology).filter(
        Terminology.id == id
    ).count()
    if count == 0:
        raise Exception(trans('i18n_terminology.terminology_not_exists'))

    stmt = update(Terminology).where(or_(Terminology.id == id, Terminology.pid == id)).values(
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
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker,scoped_session
# engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))
# session_maker = scoped_session(sessionmaker(bind=engine))

def run_fill_empty_embeddings(session_maker):
    try:
        if not settings.EMBEDDING_ENABLED:
            return
        session = session_maker()
        stmt1 = select(Terminology.id).where(and_(Terminology.embedding.is_(None), Terminology.pid.is_(None)))
        stmt2 = select(Terminology.pid).where(
            and_(Terminology.embedding.is_(None), Terminology.pid.isnot(None))).distinct()
        combined_stmt = union(stmt1, stmt2)
        results = session.execute(combined_stmt).scalars().all()
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
    finally:
        session_maker.remove()


embedding_sql = f"""
SELECT id, pid, word, similarity
FROM
(SELECT id, pid, word, oid, specific_ds, datasource_ids, enabled,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM terminology AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_TERMINOLOGY_SIMILARITY} AND oid = :oid AND enabled = true
AND (specific_ds = false OR specific_ds IS NULL)
ORDER BY similarity DESC
LIMIT {settings.EMBEDDING_TERMINOLOGY_TOP_COUNT}
"""

embedding_sql_with_datasource = f"""
SELECT id, pid, word, similarity
FROM
(SELECT id, pid, word, oid, specific_ds, datasource_ids, enabled,
( 1 - (embedding <=> :embedding_array) ) AS similarity
FROM terminology AS child
) TEMP
WHERE similarity > {settings.EMBEDDING_TERMINOLOGY_SIMILARITY} AND oid = :oid AND enabled = true
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
            and_(text(":sentence ILIKE '%' || word || '%'"), Terminology.oid == oid, Terminology.enabled == True)
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
            _map[pid] = {'words': [], 'description': ''}
        if row.pid is None:
            _map[pid]['description'] = row.description
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
