# ruff: noqa: F811
"""Opt-in real tokenizer/model + PostgreSQL table-save acceptance.

Uses only synthetic metadata and the local deployed model. Run with the same
explicit disposable-PostgreSQL opt-in as the other embedding integration tests.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import local
from types import SimpleNamespace

import pytest
from metadata_test_support import read_datasource_vectors, read_table_vectors
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)
from test_table_parameters_integration import table_environment  # noqa: F401

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.crud.datasource import updateField
from apps.datasource.crud.table import _resource_input, _table_input
from apps.datasource.embedding.table_embedding import calc_table_embedding
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from common.core.embedding_config import load_embedding_config
from common.utils import embedding_threads


@pytest.fixture(scope="module")
def local_model():
    import torch

    torch.set_num_threads(4)
    return EmbeddingModelCache._new_instance()


@pytest.mark.parametrize("shape", ["short", "wide", "long_comment", "long_identifier"])
def test_saved_metadata_covers_all_actual_model_inputs(
    table_environment, monkeypatch, local_model, shape
):
    database, _client, ds_id = table_environment
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    monkeypatch.setattr(embedding_threads, "session_maker", sessions)
    recorded_inputs = {"save_table_embedding": [], "save_ds_embedding": []}
    futures = []
    job = local()

    def embed_documents(texts):
        recorded_inputs[job.name].extend(texts)
        return local_model.embed_documents(texts)

    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(
            _client=local_model._client,
            embed_documents=embed_documents,
            embed_query=local_model.embed_query,
        ),
    )
    with ThreadPoolExecutor(max_workers=2) as executor:

        def submit(function, *args):
            def observed_job():
                job.name = function.__name__
                return function(*args)

            future = executor.submit(observed_job)
            futures.append(future)
            return future

        monkeypatch.setattr(
            embedding_threads, "executor", SimpleNamespace(submit=submit)
        )
        with Session(database) as session:
            table = session.query(CoreTable).filter(CoreTable.ds_id == ds_id).first()
            table_id = table.id
            table.table_name = "业务表" + (
                "超长表标识" * 160 if shape == "long_identifier" else ""
            )
            session.add(table)
            session.query(CoreField).filter(CoreField.table_id == table_id).delete()
            for index in range(120 if shape == "wide" else 1):
                field = CoreField(
                    ds_id=ds_id,
                    table_id=table_id,
                    field_index=index,
                    field_name=f"字段{index}"
                    + ("超长字段标识" * 160 if shape == "long_identifier" else ""),
                    field_type="INT",
                    custom_comment=f"业务指标{index}",
                )
                session.add(field)
            session.flush()
            field_id = field.id
            session.commit()
            updateField(
                session,
                CoreField(
                    id=field_id,
                    ds_id=ds_id,
                    table_id=table_id,
                    checked=True,
                    custom_comment="TAIL尾部指标"
                    + ("超长字段注释" * 300 if shape == "long_comment" else ""),
                ),
            )
            originals = {
                "save_table_embedding": _table_input(
                    session, session.get(CoreTable, table_id)
                ),
                "save_ds_embedding": _resource_input(
                    session, session.get(CoreDatasource, ds_id)
                ),
            }
        for future in futures:
            future.result(timeout=30)
    for job_name, inputs in recorded_inputs.items():
        original = originals[job_name]
        assert inputs
        first = local_model._client._first_module()
        first_line = original.splitlines(keepends=True)[0]
        # Remove only the permitted repeated table context to reconstruct the body.
        reconstructed = inputs[0] + "".join(
            chunk[len(first_line) :] if chunk.startswith(first_line) else chunk
            for chunk in inputs[1:]
        )
        assert reconstructed == original
        for chunk in inputs:
            prepared = chunk.replace("\n", " ")
            actual = local_model._client.tokenize([prepared])["input_ids"][0].tolist()
            complete = first.tokenizer(
                prepared, add_special_tokens=True, truncation=False
            )["input_ids"]
            assert actual == complete
            assert len(actual) <= first.max_seq_length
        if shape != "short":
            assert len(inputs) > 1
            assert (
                len(
                    first.tokenizer(original.replace("\n", " "), truncation=False)[
                        "input_ids"
                    ]
                )
                > first.max_seq_length
            )
            assert (
                len(
                    local_model._client.tokenize([original.replace("\n", " ")])[
                        "input_ids"
                    ][0]
                )
                == first.max_seq_length
            )
    with Session(database) as session:
        assert len(read_table_vectors(session, table_id)) == len(
            recorded_inputs["save_table_embedding"]
        )
        assert len(read_datasource_vectors(session, ds_id)) == len(
            recorded_inputs["save_ds_embedding"]
        )
        selected = calc_table_embedding(
            [{"id": table_id, "table_name": "业务表", "schema_table": "allowed"}],
            "TAIL尾部指标",
            session=session,
            config=load_embedding_config(session),
        )
        assert selected[0]["cosine_similarity"] > 0
        assert "vectors" not in session.get(CoreTable, table_id).model_dump()
    sessions.remove()
