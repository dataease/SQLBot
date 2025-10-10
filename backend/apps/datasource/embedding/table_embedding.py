# Author: Junjun
# Date: 2025/9/23
import json
import time
import traceback

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import cosine_similarity
from common.core.config import settings
from common.utils.utils import SQLBotLogUtil


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


def calc_table_embedding(tables: list[dict], question: str):
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

            q_embedding = model.embed_query(question)
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
