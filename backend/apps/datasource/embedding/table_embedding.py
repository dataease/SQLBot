# Author: Junjun
# Date: 2025/9/23
import json
import traceback

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.embedding.utils import cosine_similarity
from common.core.config import settings
from common.core.deps import SessionDep, CurrentUser
from common.utils.utils import SQLBotLogUtil


def get_table_embedding(session: SessionDep, current_user: CurrentUser, tables: list[str], question: str):
    _list = []
    for table_schema in tables:
        _list.append({"table_schema": table_schema, "cosine_similarity": 0.0})

    if _list:
        try:
            text = [s.get('table_schema') for s in _list]

            model = EmbeddingModelCache.get_model()
            results = model.embed_documents(text)

            q_embedding = model.embed_query(question)
            for index in range(len(results)):
                item = results[index]
                _list[index]['cosine_similarity'] = cosine_similarity(q_embedding, item)

            _list.sort(key=lambda x: x['cosine_similarity'], reverse=True)
            _list = _list[:settings.TABLE_EMBEDDING_COUNT]
            # print(len(_list))
            SQLBotLogUtil.info(json.dumps(_list))
            return [t.get("table_schema") for t in _list]
        except Exception:
            traceback.print_exc()
    return _list
