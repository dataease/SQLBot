# ruff: noqa: F811
"""Metadata save, generation and candidate selection at the service boundary."""

from types import SimpleNamespace

from sqlmodel import Session
from test_datasource_lifecycle import environment, run_jobs  # noqa: F401

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.crud.datasource import updateField
from apps.datasource.crud.table import get_tables_by_ds_id
from apps.datasource.embedding.table_embedding import calc_table_embedding
from apps.datasource.models.datasource import CoreField
from common.core.embedding_config import load_embedding_config


class BoundaryModel:
    """Offline provider whose preprocessor truncates at a known input boundary."""

    def __init__(self):
        self.inputs = []
        self._client = SimpleNamespace(
            _first_module=lambda: SimpleNamespace(
                max_seq_length=48,
                do_lower_case=False,
                tokenizer=lambda text, **kwargs: {"input_ids": [0, *list(text), 1]},
            )
        )

    def embed_documents(self, texts):
        self.inputs.extend(texts)
        return [[1.0, 0.0] if "TAIL" in text else [0.0, 1.0] for text in texts]

    def embed_query(self, text):
        return [1.0, 0.0]


def test_saved_wide_table_publishes_all_chunks_and_uses_tail_for_selection(
    environment, monkeypatch
):
    from apps.datasource.models.metadata_embedding import MetadataEmbedding

    database, _client, jobs = environment
    MetadataEmbedding.__table__.create(database, checkfirst=True)
    model = BoundaryModel()
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: model)
    with Session(database) as session:
        for index in range(2, 122):
            session.add(
                CoreField(
                    id=index,
                    ds_id=1,
                    table_id=1,
                    field_name=f"field_{index}",
                    field_type="INT",
                    field_index=index,
                )
            )
        session.commit()
        updateField(
            session,
            CoreField(id=121, ds_id=1, table_id=1, checked=True, custom_comment="TAIL"),
        )
    run_jobs(jobs)
    assert len(model.inputs) > 1
    assert all(len(text.replace("\n", " ").strip()) + 2 <= 48 for text in model.inputs)
    assert "TAIL" in "".join(model.inputs)
    assert all(f"field_{index}" in "".join(model.inputs) for index in range(2, 122))
    with Session(database) as session:
        tables = get_tables_by_ds_id(session, 1)
        assert "vectors" not in tables[0].model_dump()
        result = calc_table_embedding(
            [{"id": 1, "table_name": "sales", "schema_table": "sales"}],
            "tail synonym",
            session=session,
            config=load_embedding_config(session),
        )
        assert result[0]["cosine_similarity"] == 1.0
        assert "chunks" not in result[0]


def test_chunk_sets_rank_distinct_allowed_tables_and_invalid_sets_skip_pruning(
    environment, monkeypatch
):
    from dataclasses import replace

    from apps.datasource.crud.table import save_table_embedding
    from apps.datasource.models.datasource import CoreTable
    from apps.datasource.models.metadata_embedding import MetadataEmbedding
    from common.utils import embedding_threads

    database, _client, _jobs = environment
    model = BoundaryModel()
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: model)
    with Session(database) as session:
        for key in range(2, 14):
            session.add(
                CoreTable(
                    id=key,
                    ds_id=1,
                    table_name=f"table_{key}",
                    custom_comment=("TAIL" if key == 12 else "ordinary") + " note" * 30,
                )
            )
        session.commit()
    save_table_embedding(embedding_threads.session_maker, list(range(1, 14)))
    candidates = [
        {"id": key, "table_name": f"table_{key}", "schema_table": f"table_{key}"}
        for key in range(1, 13)
    ]
    with Session(database) as session:
        config = replace(load_embedding_config(session), table_count=10)
        result = calc_table_embedding(
            candidates, "synonym", session=session, config=config
        )
        assert len(result) == len({table["id"] for table in result}) == 10
        assert result[0]["id"] == 12
        assert 13 not in {table["id"] for table in result}
        # A missing block must invalidate the whole layer, even if others match.
        representation = session.get(MetadataEmbedding, ("table", 1))
        representation.chunk_count += 1
        session.commit()
        result = calc_table_embedding(
            candidates, "synonym", session=session, config=config
        )
        assert {table["id"] for table in result} == set(range(1, 13))


def test_edit_invalidates_complete_representation_even_with_switch_disabled(
    environment, monkeypatch
):
    from dataclasses import replace

    from test_embedding_parameters import save

    from apps.datasource.crud.table import save_table_embedding
    from apps.datasource.models.datasource import CoreTable
    from common.utils import embedding_threads

    database, client, _jobs = environment
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: BoundaryModel())
    with Session(database) as session:
        session.add(CoreTable(id=2, ds_id=1, table_name="other"))
        session.commit()
    save_table_embedding(embedding_threads.session_maker, [1, 2])
    candidates = [
        {"id": key, "table_name": str(key), "schema_table": str(key)} for key in (1, 2)
    ]
    with Session(database) as session:
        config = replace(load_embedding_config(session), table_count=1)
        assert (
            len(calc_table_embedding(candidates, "q", session=session, config=config))
            == 1
        )
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    with Session(database) as session:
        updateField(
            session,
            CoreField(
                id=1,
                ds_id=1,
                table_id=1,
                checked=True,
                custom_comment="changed while disabled",
            ),
        )
        assert (
            len(calc_table_embedding(candidates, "q", session=session, config=config))
            == 2
        )


def test_incomplete_provider_batch_is_not_published_and_later_task_recovers(
    environment, monkeypatch
):
    import pytest
    from metadata_test_support import read_table_vectors

    from apps.datasource.crud.table import save_table_embedding
    from common.utils import embedding_threads
    from common.utils.embedding_lifecycle import EmbeddingGenerationError

    database, _client, _jobs = environment
    model = BoundaryModel()
    with Session(database) as session:
        for index in range(2, 122):
            session.add(
                CoreField(
                    id=index,
                    ds_id=1,
                    table_id=1,
                    field_name=f"field_{index}",
                    field_type="INT",
                    field_index=index,
                )
            )
        session.commit()
    original = model.embed_documents

    def incomplete(texts):
        vectors = original(texts)
        return vectors if len(model.inputs) <= 32 else vectors[:-1]

    model.embed_documents = incomplete
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: model)
    with pytest.raises(EmbeddingGenerationError):
        save_table_embedding(embedding_threads.session_maker, [1])
    with Session(database) as session:
        with pytest.raises(ValueError):
            read_table_vectors(session, 1)
    model.embed_documents = original
    save_table_embedding(embedding_threads.session_maker, [1])
    with Session(database) as session:
        assert len(read_table_vectors(session, 1)) > 32
