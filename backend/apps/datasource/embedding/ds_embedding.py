# Author: Junjun
# Date: 2025/9/18
import json
import math
import traceback

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.crud.datasource import get_table_schema
from apps.datasource.models.datasource import CoreDatasource
from common.core.deps import SessionDep, CurrentUser


def cosine_similarity(vec_a, vec_b):
    if len(vec_a) != len(vec_b):
        raise ValueError("The vector dimension must be the same")

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))

    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def get_ds_embedding(session: SessionDep, current_user: CurrentUser, _ds_list, question: str):
    _list = []
    for _ds in _ds_list:
        if _ds.get('id'):
            ds = session.get(CoreDatasource, _ds.get('id'))

            table_schema = get_table_schema(session, current_user, ds)
            ds_info = f"{ds.name}, {ds.description}\n"
            ds_schema = ds_info + table_schema

            _list.append({"id": ds.id, "ds_schema": ds_schema, "cosine_similarity": 0.0, "ds": ds})

    if _list:
        try:
            text = [s.get('ds_schema') for s in _list]

            model = EmbeddingModelCache.get_model()
            results = model.embed_documents(text)

            q_embedding = model.embed_query(question)
            for index in range(len(results)):
                item = results[index]
                _list[index]['cosine_similarity'] = cosine_similarity(q_embedding, item)

            _list.sort(key=lambda x: x['cosine_similarity'], reverse=True)
            print(len(_list))
            ds = _list[0].get('ds')
            return {"id": ds.id, "name": ds.name, "description": ds.description}
        except Exception:
            traceback.print_exc()
