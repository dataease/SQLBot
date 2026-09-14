# Author: Junjun
# Date: 2025/9/23
import json
import re
import time
import traceback

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import batch_cosine_similarity, cosine_similarity
from common.core.config import settings
from common.utils.utils import SQLBotLogUtil


def _parse_embedding(embedding):
    """解析 embedding，兼容 JSON 字符串和原生列表两种格式。"""
    if isinstance(embedding, list):
        return embedding
    if isinstance(embedding, str):
        return json.loads(embedding)
    return None


def get_table_embedding(tables: list[dict], question: str):
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

            q_embedding = model.embed_query(question)
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


def calc_keyword_score(
    question: str,
    table_name: str,
    table_comment: str,
    fields: list[dict]
) -> float:
    """计算关键词与表的匹配分数。

    综合考虑所有关键词的匹配情况：
    - 表名完整匹配：1.0
    - 表注释完整匹配：0.9
    - 部分匹配时，按匹配质量 * 关键词覆盖率计算

    Args:
        question: 提取后的关键词（逗号分隔）或原始问题
        table_name: 表名
        table_comment: 表注释（已合并 custom_comment 优先）
        fields: 字段列表，每个 dict 包含 field_name, field_comment, custom_comment

    Returns:
        0.0~1.0 的匹配分数
    """
    if not question:
        return 0.0

    keywords = [kw.strip().lower() for kw in question.split(',') if kw.strip()]
    if not keywords:
        return 0.0

    tn = table_name.lower()
    tc = (table_comment or '').lower()
    total_kw = len(keywords)

    # 表名只分割一次，后续复用
    tn_parts = set(re.split(r'[_\s]+', tn))
    tn_parts.discard('')

    # 预处理字段：只 strip/lower 一次
    field_comments = []
    field_name_parts = []
    for field in fields:
        fc = ''
        if field.get('custom_comment'):
            fc = field['custom_comment'].strip().lower()
        if not fc and field.get('field_comment'):
            fc = field['field_comment'].strip().lower()
        field_comments.append(fc)

        fname = field.get('field_name', '').lower()
        if fname:
            field_name_parts.append(set(re.split(r'[_\s]+', fname)) - {''})
        else:
            field_name_parts.append(set())

    # 收集每个关键词的最佳匹配分数
    kw_scores = {}  # keyword -> best_score

    for kw in keywords:
        # 1. 表名完整匹配：1.0
        if kw == tn:
            kw_scores[kw] = 1.0
            continue

        # 2. 表注释完整匹配：0.9
        if tc and kw == tc:
            kw_scores[kw] = max(kw_scores.get(kw, 0), 0.9)
            continue

        # 3. 表注释子串匹配：0.7（关键词是注释的子串，如 "用户" 匹配 "用户表"）
        if tc and kw in tc:
            kw_scores[kw] = max(kw_scores.get(kw, 0), 0.7)
            continue

        # 4. 表名部分匹配：收集匹配的关键词
        if kw in tn_parts:
            kw_scores[kw] = max(kw_scores.get(kw, 0), 0)  # 标记匹配，分数稍后计算

        # 5. 字段注释匹配：0.5（精确）/ 0.4（子串）
        for fc in field_comments:
            if fc:
                if kw == fc:
                    kw_scores[kw] = max(kw_scores.get(kw, 0), 0.5)
                    break
                elif kw in fc:
                    kw_scores[kw] = max(kw_scores.get(kw, 0), 0.4)

        # 6. 字段名匹配：0.3
        if kw not in kw_scores or kw_scores[kw] < 0.3:
            for fparts in field_name_parts:
                if kw in fparts:
                    kw_scores[kw] = max(kw_scores.get(kw, 0), 0.3)
                    break

    if not kw_scores:
        return 0.0

    # 表名/注释完整匹配 → 直接返回 1.0 或 0.9
    if kw_scores.get(tn) == 1.0:
        return 1.0
    if tc and kw_scores.get(tc) == 0.9:
        return 0.9
    if tn_parts:
        matched_parts = {kw for kw in keywords if kw in tn_parts}
        if matched_parts:
            coverage = len(matched_parts) / len(tn_parts)
            tn_score = round(0.25 + 0.25 * coverage, 2)
            # 更新这些关键词的分数为表名匹配分数
            for kw in matched_parts:
                kw_scores[kw] = max(kw_scores.get(kw, 0), tn_score)

    # 综合评分：最佳匹配分数 * 关键词覆盖率
    best_score = max(kw_scores.values())
    match_rate = len(kw_scores) / total_kw
    return round(best_score * match_rate, 2)


def calc_table_embedding(tables: list[dict], question: str, session=None, oid: int = None,
                         keywords: str = None):
    """使用向量相似度和关键词匹配的融合评分计算表的相关性分数。

    当 keywords 不为空时（已由调用方提取并扩展）：
    1. 用 keywords 计算向量相似度（vec_score）
    2. 计算关键词匹配度（keyword_score）
    3. 融合评分：final_score = α * vec_score + (1-α) * keyword_score
    4. keyword_score=1.0 的表保证排在最前面

    当 keywords 为空或 TABLE_EMBEDDING_KEYWORD_ENABLED 为 False 时，回退到纯向量匹配。

    Args:
        tables: 表列表，每个 dict 包含 id, table_name, schema_table, embedding, table_comment, fields
        question: 原始用户问题（用于纯向量匹配回退）
        session: 数据库会话（预留）
        oid: 组织 ID（预留）
        keywords: 已提取并扩展的关键词（由调用方传入）
    """
    if not keywords or not settings.TABLE_EMBEDDING_KEYWORD_ENABLED:
        # 回退到纯向量匹配
        return _calc_vector_only(tables, question)

    _list = []
    for table in tables:
        _list.append({
            "id": table.get('id'),
            "schema_table": table.get('schema_table'),
            "embedding": table.get('embedding'),
            "cosine_similarity": 0.0,
            "table_name": table.get('table_name'),
            "table_comment": table.get('table_comment', ''),
            "fields": table.get('fields', [])
        })

    if not _list:
        return _list

    try:
        start_time = time.time()

        # 步骤 1：用关键词计算向量相似度（批量向量化）
        model = EmbeddingModelCache.get_model()
        q_embedding = model.embed_query(keywords)

        # 预解析所有 embedding，跳过空的
        parsed_embeddings = []
        valid_indices = []
        for i, item in enumerate(_list):
            emb = item.get('embedding')
            if emb:
                parsed = _parse_embedding(emb)
                if parsed:
                    parsed_embeddings.append(parsed)
                    valid_indices.append(i)

        # 一次性批量计算所有余弦相似度
        if parsed_embeddings:
            similarities = batch_cosine_similarity(q_embedding, parsed_embeddings)
            for idx, sim in zip(valid_indices, similarities):
                _list[idx]['cosine_similarity'] = float(sim)

        # 步骤 2 & 3：计算关键词分数并融合
        alpha = settings.TABLE_EMBEDDING_ALPHA
        for table in _list:
            vec_score = table['cosine_similarity']
            kw_score = calc_keyword_score(
                keywords,
                table.get('table_name', ''),
                table.get('table_comment', ''),
                table.get('fields', [])
            )
            table['keyword_score'] = kw_score
            table['cosine_similarity'] = alpha * vec_score + (1 - alpha) * kw_score

        # 步骤 4：排序 - 精确匹配（keyword_score=1.0）始终排最前
        exact_matches = [t for t in _list if t.get('keyword_score') == 1.0]
        other_tables = [t for t in _list if t.get('keyword_score') != 1.0]

        exact_matches.sort(key=lambda x: x['cosine_similarity'], reverse=True)
        other_tables.sort(key=lambda x: x['cosine_similarity'], reverse=True)

        _list = exact_matches + other_tables
        _list = _list[:settings.TABLE_EMBEDDING_COUNT]

        end_time = time.time()
        SQLBotLogUtil.info(f"融合评分耗时 {end_time - start_time:.3f}s")
        SQLBotLogUtil.info(json.dumps([{
            "id": ele.get('id'),
            "schema_table": ele.get('schema_table'),
            "cosine_similarity": ele.get('cosine_similarity'),
            "keyword_score": ele.get('keyword_score'),
            "table_name": ele.get('table_name')
        } for ele in _list]))

        return _list
    except Exception:
        traceback.print_exc()
        # 异常回退到纯向量匹配
        return _calc_vector_only(tables, question)


def _calc_vector_only(tables: list[dict], question: str):
    """纯向量相似度评分（原始逻辑）。"""
    _list = []
    for table in tables:
        _list.append({
            "id": table.get('id'),
            "schema_table": table.get('schema_table'),
            "embedding": table.get('embedding'),
            "cosine_similarity": 0.0,
            "table_name": table.get('table_name'),
            "table_comment": table.get('table_comment', ''),
            "fields": table.get('fields', [])
        })

    if _list:
        try:
            model = EmbeddingModelCache.get_model()
            start_time = time.time()
            q_embedding = model.embed_query(question)

            # 预解析所有 embedding，跳过空的
            parsed_embeddings = []
            valid_indices = []
            for i, item in enumerate(_list):
                emb = item.get('embedding')
                if emb:
                    parsed = _parse_embedding(emb)
                    if parsed:
                        parsed_embeddings.append(parsed)
                        valid_indices.append(i)

            # 一次性批量计算所有余弦相似度
            if parsed_embeddings:
                similarities = batch_cosine_similarity(q_embedding, parsed_embeddings)
                for idx, sim in zip(valid_indices, similarities):
                    _list[idx]['cosine_similarity'] = float(sim)

            _list.sort(key=lambda x: x['cosine_similarity'], reverse=True)
            _list = _list[:settings.TABLE_EMBEDDING_COUNT]

            end_time = time.time()
            SQLBotLogUtil.info(str(end_time - start_time))
            SQLBotLogUtil.info(json.dumps([{
                "id": ele.get('id'),
                "schema_table": ele.get('schema_table'),
                "cosine_similarity": ele.get('cosine_similarity'),
                "table_name": ele.get('table_name')
            } for ele in _list]))
            return _list
        except Exception:
            traceback.print_exc()
    return _list
