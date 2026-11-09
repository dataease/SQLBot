# ruff: noqa: F811
"""Datasource save/generate/preselect contracts with an offline provider boundary."""

from dataclasses import replace

import pytest
from sqlmodel import Session
from test_datasource_lifecycle import environment, run_jobs  # noqa: F401
from test_metadata_table_chunks import BoundaryModel

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.crud.datasource import updateField
from apps.datasource.crud.table import save_ds_embedding
from apps.datasource.embedding.ds_embedding import get_ds_embedding
from apps.datasource.models.datasource import CoreDatasource, CoreField
from common.core.embedding_config import load_embedding_config
from common.utils import embedding_threads


def test_saved_datasource_tail_ranks_allowed_candidates_using_complete_chunks(
    environment, monkeypatch
):
    from apps.datasource.crud.table import _resource_input
    from apps.datasource.embedding.metadata_chunks import read_metadata

    database, _client, jobs = environment
    model = BoundaryModel()
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: model)
    with Session(database) as session:
        for key in range(2, 14):
            session.add(
                CoreDatasource(
                    id=key, name=f"source_{key}", type="pg", embedding="[1,0]"
                )
            )
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
    save_ds_embedding(embedding_threads.session_maker, list(range(2, 14)))
    candidates = [{"id": key, "name": f"source_{key}"} for key in range(12, 0, -1)]
    with Session(database) as session:
        source = session.get(CoreDatasource, 1)
        vectors = read_metadata(
            session, "datasource", 1, _resource_input(session, source)
        )
        assert len(vectors) > 1
        selected = get_ds_embedding(
            session,
            candidates,
            None,
            "tail synonym",
            config=replace(load_embedding_config(session), datasource_count=10),
        )
        assert len(selected) == 10
        assert selected[0] is candidates[-1]
        assert 13 not in {item["id"] for item in selected}
        assert all(set(item) == {"id", "name"} for item in selected)
        assert "vectors" not in source.model_dump()


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "count",
        "json",
        "zero",
        "nonfinite",
        "dimension",
        "version",
        "model",
        "input",
        "checksum",
    ],
)
def test_any_invalid_datasource_skips_entire_layer_even_with_valid_legacy_vector(
    environment, monkeypatch, damage
):
    from apps.datasource.embedding.metadata_chunks import fingerprint
    from apps.datasource.models.metadata_embedding import MetadataEmbedding

    database, _client, _jobs = environment
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: BoundaryModel())
    with Session(database) as session:
        session.add(CoreDatasource(id=2, name="other", type="pg", embedding="[0,1]"))
        session.commit()
    save_ds_embedding(embedding_threads.session_maker, [1, 2])
    candidates = [{"id": 1, "name": "test"}, {"id": 2, "name": "other"}]
    with Session(database) as session:
        config = replace(load_embedding_config(session), datasource_count=1)
        assert len(get_ds_embedding(session, candidates, None, "q", config=config)) == 1
        record = session.get(MetadataEmbedding, ("datasource", 2))
        if damage == "missing":
            session.delete(record)
        elif damage == "count":
            record.chunk_count += 1
        elif damage in ("json", "zero", "nonfinite", "dimension"):
            record.vectors = {
                "json": "broken",
                "zero": "[[0,0]]",
                "nonfinite": "[[NaN,1]]",
                "dimension": "[[1,0,0]]",
            }[damage]
            record.chunk_count = 1
            record.dimension = 3 if damage == "dimension" else 2
            record.vectors_hash = fingerprint(record.vectors)
        elif damage == "version":
            record.format_version += 1
        elif damage == "model":
            record.model_id = "stale-model"
        elif damage == "input":
            session.get(CoreDatasource, 2).description = "new content"
        else:
            record.vectors_hash = "bad"
        session.commit()
        assert (
            get_ds_embedding(session, candidates, None, "q", config=config)
            is candidates
        )


def test_single_datasource_skips_provider_and_missing_representation(
    environment, monkeypatch
):
    database, _client, _jobs = environment
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: pytest.fail("single datasource must skip vectors"),
    )
    candidates = [{"id": 1, "name": "test"}]
    with Session(database) as session:
        assert get_ds_embedding(session, candidates, None, "q") is candidates
