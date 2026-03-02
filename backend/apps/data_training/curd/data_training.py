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
from common.utils.milvus_client import milvus_client
from common.utils.utils import SQLBotLogUtil


def get_data_training_base_query(oid: int, name: Optional[str] = None):
    """
    获取数据训练查询的基础查询结构
    """
    if name and name.strip() != "":
        keyword_pattern = f"%{name.strip()}%"
        parent_ids_subquery = (
            select(DataTraining.id)
            .where(and_(DataTraining.question.ilike(keyword_pattern), DataTraining.oid == oid))
        )
    else:
        parent_ids_subquery = (
            select(DataTraining.id).where(and_(DataTraining.oid == oid))
        )

    return parent_ids_subquery


def build_data_training_query(session: SessionDep, oid: int, name: Optional[str] = None,
                              paginate: bool = True, current_page: int = 1, page_size: int = 10):
    """
    构建数据训练查询的通用方法
    """
    parent_ids_subquery = get_data_training_base_query(oid, name)

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
            .order_by(DataTraining.create_time.desc())
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
            .order_by(DataTraining.create_time.desc())
            .subquery()
        )

    # 构建主查询
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

    return stmt, total_count, total_pages, current_page, page_size


def execute_data_training_query(session: SessionDep, stmt) -> List[DataTrainingInfoResult]:
    """
    执行查询并返回数据训练信息列表
    """
    _list = []
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

    return _list


def page_data_training(session: SessionDep, current_page: int = 1, page_size: int = 10,
                       name: Optional[str] = None, oid: Optional[int] = 1):
    """
    分页查询数据训练（原方法保持不变）
    """
    stmt, total_count, total_pages, current_page, page_size = build_data_training_query(
        session, oid, name, True, current_page, page_size
    )
    _list = execute_data_training_query(session, stmt)

    return current_page, page_size, total_count, total_pages, _list


def get_all_data_training(session: SessionDep, name: Optional[str] = None, oid: Optional[int] = 1):
    """
    获取所有数据训练（不分页）
    """
    stmt, total_count, total_pages, current_page, page_size = build_data_training_query(
        session, oid, name, False
    )
    _list = execute_data_training_query(session, stmt)

    return _list


def create_training(session: SessionDep, info: DataTrainingInfo, oid: int, trans: Trans, skip_embedding: bool = False):
    """
    创建单个数据训练记录
    Args:
        skip_embedding: 是否跳过embedding处理（用于批量插入）
    """
    # 基本验证
    if not info.question or not info.question.strip():
        raise Exception(trans("i18n_data_training.question_cannot_be_empty"))

    if not info.description or not info.description.strip():
        raise Exception(trans("i18n_data_training.description_cannot_be_empty"))

    create_time = datetime.datetime.now()

    # 检查数据源和高级应用不能同时为空
    if info.datasource is None and info.advanced_application is None:
        if oid == 1:
            raise Exception(trans("i18n_data_training.datasource_assistant_cannot_be_none"))
        else:
            raise Exception(trans("i18n_data_training.datasource_cannot_be_none"))

    # 检查重复记录
    stmt = select(DataTraining.id).where(
        and_(DataTraining.question == info.question.strip(), DataTraining.oid == oid)
    )

    if info.datasource is not None and info.advanced_application is not None:
        stmt = stmt.where(
            or_(
                DataTraining.datasource == info.datasource,
                DataTraining.advanced_application == info.advanced_application
            )
        )
    elif info.datasource is not None and info.advanced_application is None:
        stmt = stmt.where(DataTraining.datasource == info.datasource)
    elif info.datasource is None and info.advanced_application is not None:
        stmt = stmt.where(DataTraining.advanced_application == info.advanced_application)

    exists = session.query(stmt.exists()).scalar()

    if exists:
        raise Exception(trans("i18n_data_training.exists_in_db"))

    # 创建记录
    data_training = DataTraining(
        question=info.question.strip(),
        description=info.description.strip(),
        oid=oid,
        datasource=info.datasource,
        advanced_application=info.advanced_application,
        create_time=create_time,
        enabled=info.enabled if info.enabled is not None else True,
        embedded=False  # 新创建的SQL示例需要向量化
    )

    session.add(data_training)
    session.flush()
    session.refresh(data_training)
    session.commit()

    # 处理embedding（批量插入时跳过）
    if not skip_embedding:
        run_save_data_training_embeddings([data_training.id])

    return data_training.id


def update_training(session: SessionDep, info: DataTrainingInfo, oid: int, trans: Trans):
    # 基本验证
    if not info.question or not info.question.strip():
        raise Exception(trans("i18n_data_training.question_cannot_be_empty"))

    if not info.description or not info.description.strip():
        raise Exception(trans("i18n_data_training.description_cannot_be_empty"))

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
        question=info.question.strip(),
        description=info.description.strip(),
        datasource=info.datasource,
        advanced_application=info.advanced_application,
        enabled=info.enabled if info.enabled is not None else True,
        embedded=False  # 更新SQL示例后需要重新向量化
    )
    session.execute(stmt)
    session.commit()

    # embedding
    run_save_data_training_embeddings([info.id])

    return info.id


def batch_create_training(session: SessionDep, info_list: List[DataTrainingInfo], oid: int, trans: Trans):
    """
    批量创建数据训练记录（复用单条插入逻辑）
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

    # 第一步：数据去重
    unique_records = {}
    duplicate_records = []

    for info in info_list:
        # 创建唯一标识
        unique_key = (
            info.question.strip().lower() if info.question else "",
            info.datasource_name.strip().lower() if info.datasource_name else "",
            info.advanced_application_name.strip().lower() if info.advanced_application_name else ""
        )

        if unique_key in unique_records:
            duplicate_records.append(info)
        else:
            unique_records[unique_key] = info

    # 将去重后的数据转换为列表
    deduplicated_list = list(unique_records.values())

    # 预加载数据源和高级应用名称到ID的映射
    datasource_name_to_id = {}
    datasource_stmt = select(CoreDatasource.id, CoreDatasource.name).where(CoreDatasource.oid == oid)
    datasource_result = session.execute(datasource_stmt).all()
    for ds in datasource_result:
        datasource_name_to_id[ds.name.strip()] = ds.id

    assistant_name_to_id = {}
    if oid == 1:
        assistant_stmt = select(AssistantModel.id, AssistantModel.name).where(AssistantModel.type == 1)
        assistant_result = session.execute(assistant_stmt).all()
        for assistant in assistant_result:
            assistant_name_to_id[assistant.name.strip()] = assistant.id

    # 验证和转换数据
    valid_records = []
    for info in deduplicated_list:
        error_messages = []

        # 基本验证
        if not info.question or not info.question.strip():
            error_messages.append(trans("i18n_data_training.question_cannot_be_empty"))

        if not info.description or not info.description.strip():
            error_messages.append(trans("i18n_data_training.description_cannot_be_empty"))

        # 数据源验证和转换
        datasource_id = None
        if info.datasource_name and info.datasource_name.strip():
            if info.datasource_name.strip() in datasource_name_to_id:
                datasource_id = datasource_name_to_id[info.datasource_name.strip()]
            else:
                error_messages.append(trans("i18n_data_training.datasource_not_found").format(info.datasource_name))

        # 高级应用验证和转换
        advanced_application_id = None
        if oid == 1 and info.advanced_application_name and info.advanced_application_name.strip():
            if info.advanced_application_name.strip() in assistant_name_to_id:
                advanced_application_id = assistant_name_to_id[info.advanced_application_name.strip()]
            else:
                error_messages.append(
                    trans("i18n_data_training.advanced_application_not_found").format(info.advanced_application_name))

        # 检查数据源和高级应用不能同时为空
        if oid == 1:
            if not datasource_id and not advanced_application_id:
                error_messages.append(trans("i18n_data_training.datasource_assistant_cannot_be_none"))
        else:
            if not datasource_id:
                error_messages.append(trans("i18n_data_training.datasource_cannot_be_none"))

        if error_messages:
            failed_records.append({
                'data': info,
                'errors': error_messages
            })
            continue

        # 创建处理后的DataTrainingInfo对象
        processed_info = DataTrainingInfo(
            question=info.question.strip(),
            description=info.description.strip(),
            datasource=datasource_id,
            datasource_name=info.datasource_name,
            advanced_application=advanced_application_id,
            advanced_application_name=info.advanced_application_name,
            enabled=info.enabled if info.enabled is not None else True
        )

        valid_records.append(processed_info)

    # 使用事务处理有效记录
    if valid_records:
        for info in valid_records:
            try:
                # 直接复用create_training方法，跳过embedding处理
                training_id = create_training(session, info, oid, trans, skip_embedding=True)
                inserted_ids.append(training_id)
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
                run_save_data_training_embeddings(inserted_ids)
            except Exception as e:
                # 如果embedding处理失败，记录错误但不回滚数据
                print(f"Embedding processing failed: {str(e)}")
                # 可以选择将embedding失败的信息记录到日志或返回给调用方

    return {
        'success_count': success_count,
        'failed_records': failed_records,
        'duplicate_count': len(duplicate_records),
        'original_count': len(info_list),
        'deduplicated_count': len(deduplicated_list)
    }


def delete_training(session: SessionDep, ids: list[int]):
    # 先从 Milvus 删除向量
    try:
        if settings.EMBEDDING_ENABLED:
            milvus_client.delete_vectors("data_training", ids)
            SQLBotLogUtil.info(f"Deleted {len(ids)} data training vectors from Milvus")
    except Exception as e:
        # Milvus删除失败不影响数据库删除
        SQLBotLogUtil.warning(f"Failed to delete data training vectors from Milvus: {e}")
    
    # 再从数据库删除
    stmt = delete(DataTraining).where(DataTraining.id.in_(ids))
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
    """
    填充所有SQL示例的 embeddings 到 Milvus
    
    查找 embedded=False 的记录（未向量化的SQL示例）
    """
    try:
        if not settings.EMBEDDING_ENABLED:
            return

        session = session_maker()
        
        # 查找未向量化的SQL示例
        stmt = select(DataTraining.id).where(DataTraining.embedded == False)
        results = session.execute(stmt).scalars().all()

        if results:
            SQLBotLogUtil.info(f"Filling {len(results)} data training embeddings to Milvus")
            save_embeddings(session_maker, results)
        else:
            SQLBotLogUtil.info("No data training to fill embeddings")
            
    except Exception as e:
        SQLBotLogUtil.error(f"Failed to fill empty data training embeddings: {e}")
        traceback.print_exc()
    finally:
        session_maker.remove()


def save_embeddings(session_maker, ids: List[int]):
    """
    保存SQL示例的向量到 Milvus

    1. 从数据库查询指定ID的SQL示例问题
    2. 使用embedding模型生成向量
    3. 先删除Milvus中的旧向量（如果存在）
    4. 将新向量插入Milvus（collection: data_training）
    5. 更新数据库中的embedded状态为True
    """
    if not settings.EMBEDDING_ENABLED:
        return

    if not ids or len(ids) == 0:
        return
    
    try:
        session = session_maker()
        
        # 获取需要向量化的SQL示例
        _list = session.query(DataTraining).filter(DataTraining.id.in_(ids)).all()
        
        if not _list:
            return
        
        # 提取问题列表用于向量化
        _question_list = [item.question for item in _list]

        # 生成 embeddings
        model = EmbeddingModelCache.get_model()
        results = model.embed_documents(_question_list)
        
        milvus_ids = [item.id for item in _list]
        oids = [item.oid for item in _list]
        
        # 先删除旧数据（如果存在）
        try:
            milvus_client.delete_vectors("data_training", milvus_ids)
        except Exception as e:
            SQLBotLogUtil.warning(f"Delete old data training vectors: {e}")
        
        # 插入新数据到 Milvus
        milvus_client.insert_vectors(
            collection_name="data_training",
            ids=milvus_ids,
            embeddings=results,
            oids=oids
        )
        
        # 更新 embedded 状态为 True
        for data_id in milvus_ids:
            stmt = update(DataTraining).where(
                DataTraining.id == data_id
            ).values(embedded=True)
            session.execute(stmt)
        
        session.commit()
        
        SQLBotLogUtil.info(f"Saved {len(milvus_ids)} data training embeddings to Milvus")

    except Exception as e:
        SQLBotLogUtil.error(f"Failed to save data training embeddings: {e}")
        traceback.print_exc()
    finally:
        session_maker.remove()


def select_training_by_question(session: SessionDep, question: str, oid: int, datasource: Optional[int] = None,
                                advanced_application_id: Optional[int] = None):
    if question.strip() == "":
        return []

    _list: List[DataTraining] = []

    # ===== 第一步：SQL 模糊匹配 =====
    stmt = (
        select(
            DataTraining.id,
            DataTraining.question,
        )
        .where(
            and_(or_(text(":sentence LIKE CONCAT('%', question, '%')"), text("question LIKE CONCAT('%', :sentence, '%')")),
                 DataTraining.oid == oid,
                 DataTraining.enabled == True)
        )
    )
    
    # 按数据源或高级应用筛选
    if advanced_application_id is not None:
        stmt = stmt.where(DataTraining.advanced_application == advanced_application_id)
    else:
        stmt = stmt.where(DataTraining.datasource == datasource)

    results = session.execute(stmt, {'sentence': question}).fetchall()

    for row in results:
        _list.append(DataTraining(id=row.id, question=row.question))

    # ===== 第二步：Milvus 向量搜索 =====
    if settings.EMBEDDING_ENABLED:
        try:
            model = EmbeddingModelCache.get_model()
            embedding = model.embed_query(question)

            # Milvus 搜索
            milvus_results = milvus_client.search_vectors(
                collection_name="data_training",
                query_embedding=embedding,
                oid=oid,
                top_k=settings.EMBEDDING_DATA_TRAINING_TOP_COUNT,
                similarity_threshold=settings.EMBEDDING_DATA_TRAINING_SIMILARITY
            )

            # 将 Milvus 结果转换为 DataTraining 对象
            if milvus_results:
                milvus_ids = [r["id"] for r in milvus_results]
                
                # 从数据库获取详细信息并过滤
                milvus_stmt = select(
                    DataTraining.id,
                    DataTraining.question,
                ).where(
                    and_(
                        DataTraining.id.in_(milvus_ids),
                        DataTraining.enabled == True
                    )
                )
                
                # 按数据源或高级应用筛选
                if advanced_application_id is not None:
                    milvus_stmt = milvus_stmt.where(DataTraining.advanced_application == advanced_application_id)
                else:
                    milvus_stmt = milvus_stmt.where(DataTraining.datasource == datasource)
                
                milvus_trainings = session.execute(milvus_stmt).fetchall()
                
                for training in milvus_trainings:
                    _list.append(DataTraining(id=training.id, question=training.question))

        except Exception as e:
            # Milvus 搜索失败不影响基本功能
            SQLBotLogUtil.error(f"Milvus data training search failed: {e}")
            traceback.print_exc()

    # ===== 第三步：去重和格式化结果 =====
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
