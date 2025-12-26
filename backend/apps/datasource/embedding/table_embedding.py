# Author: Junjun
# Date: 2025/9/23
import json
import time
import traceback
from typing import List

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import cosine_similarity
from common.core.config import settings
from common.utils.utils import SQLBotLogUtil


def build_context_query(current_question: str, history_questions: List[str] = None) -> str:
    """
    构建包含上下文的查询文本

    Args:
        current_question: 当前问题
        history_questions: 历史问题列表（按时间正序，最旧的在前）

    Returns:
        拼接后的查询文本
    """
    if not settings.MULTI_TURN_EMBEDDING_ENABLED or not history_questions:
        return current_question

    max_history = settings.MULTI_TURN_HISTORY_COUNT
    recent_history = history_questions[-max_history:] if history_questions else []

    if not recent_history:
        return current_question

    # 拼接：历史问题 + 当前问题
    context_parts = recent_history + [current_question]

    # 使用分隔符拼接，保持语义连贯
    context_query = " | ".join(context_parts)

    SQLBotLogUtil.info(f"Context query for embedding: {context_query}")

    return context_query


def get_table_embedding(tables: list[dict], question: str, history_questions: List[str] = None):
    _list = []
    for table in tables:
        _list.append({"id": table.get('id'), "schema_table": table.get('schema_table'), "cosine_similarity": 0.0})

    if _list:
        try:
            text = [s.get('schema_table') for s in _list]

            model = EmbeddingModelCache.get_model()
            start_time = time.time()
            results = model.embed_documents(text)
            end_time = time.time()
            SQLBotLogUtil.info(str(end_time - start_time))

            # 构建包含上下文的查询
            context_query = build_context_query(question, history_questions)
            q_embedding = model.embed_query(context_query)
            for index in range(len(results)):
                item = results[index]
                _list[index]['cosine_similarity'] = cosine_similarity(q_embedding, item)

            _list.sort(key=lambda x: x['cosine_similarity'], reverse=True)
            _list = _list[:settings.TABLE_EMBEDDING_COUNT]
            # print(len(_list))
            SQLBotLogUtil.info(json.dumps(_list))
            return _list
        except Exception:
            traceback.print_exc()
    return _list


def calc_table_embedding(tables: list[dict], question: str, history_questions: List[str] = None):
    """
    计算表结构与问题的embedding相似度

    Args:
        tables: 表结构列表
        question: 当前问题
        history_questions: 历史问题列表（可选，用于多轮对话）

    Returns:
        按相似度排序的表列表
    """
    _list = []
    for table in tables:
        _list.append(
            {"id": table.get('id'), "schema_table": table.get('schema_table'), "embedding": table.get('embedding'),
             "cosine_similarity": 0.0})

    if _list:
        try:
            # text = [s.get('schema_table') for s in _list]
            #
            model = EmbeddingModelCache.get_model()
            start_time = time.time()
            # results = model.embed_documents(text)
            # end_time = time.time()
            # SQLBotLogUtil.info(str(end_time - start_time))
            results = [item.get('embedding') for item in _list]

            # 构建包含上下文的查询
            context_query = build_context_query(question, history_questions)
            q_embedding = model.embed_query(context_query)
            for index in range(len(results)):
                item = results[index]
                if item:
                    _list[index]['cosine_similarity'] = cosine_similarity(q_embedding, json.loads(item))

            _list.sort(key=lambda x: x['cosine_similarity'], reverse=True)
            _list = _list[:settings.TABLE_EMBEDDING_COUNT]
            # print(len(_list))
            end_time = time.time()
            SQLBotLogUtil.info(str(end_time - start_time))
            SQLBotLogUtil.info(json.dumps([{"id": ele.get('id'), "schema_table": ele.get('schema_table'),
                                            "cosine_similarity": ele.get('cosine_similarity')}
                                           for ele in _list]))
            return _list
        except Exception:
            traceback.print_exc()
    return _list
