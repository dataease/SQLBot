"""Offline lifecycle regressions through parameter and metadata business entries."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import JSON, Integer, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine
from test_embedding_parameters import parameter_app, save, values

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.crud.datasource import get_ds, updateField
from apps.datasource.crud.table import get_tables_by_ds_id
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from common.core.config import settings
from common.utils import embedding_threads


@pytest.fixture
def environment(monkeypatch):
    database = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    metadata = MetaData()
    for model in (CoreDatasource, CoreTable, CoreField):
        table = model.__table__.to_metadata(metadata)
        table.c.id.type = Integer()
        if model is CoreDatasource:
            table.c.table_relation.type = JSON()
    metadata.create_all(database)
    maker = scoped_session(sessionmaker(bind=database, class_=Session))
    jobs = []
    monkeypatch.setattr(embedding_threads, "session_maker", maker)
    monkeypatch.setattr(
        embedding_threads,
        "executor",
        SimpleNamespace(submit=lambda function, *args: jobs.append((function, args))),
    )
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_ENABLED", True)
    with TestClient(
        parameter_app(database, monkeypatch), raise_server_exceptions=False
    ) as client:
        with Session(database) as session:
            session.add(CoreDatasource(id=1, name="test", type="pg", embedding="[1,0]"))
            session.add(CoreTable(id=1, ds_id=1, table_name="sales", embedding="[1,0]"))
            session.add(
                CoreField(
                    id=1, ds_id=1, table_id=1, field_name="id", field_type="INTEGER"
                )
            )
            session.commit()
        yield database, client, jobs
    maker.remove()
    database.dispose()


def run_jobs(jobs):
    while jobs:
        function, args = jobs.pop(0)
        function(*args)


def test_queued_metadata_task_observes_switch_at_actual_start(environment, monkeypatch):
    database, client, jobs = environment
    with Session(database) as session:
        updateField(
            session,
            CoreField(
                id=1, ds_id=1, table_id=1, checked=True, custom_comment="updated"
            ),
        )
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: pytest.fail("disabled worker contacted provider"),
    )
    run_jobs(jobs)
    with Session(database) as session:
        assert get_ds(session, 1).embedding is None
        assert get_tables_by_ds_id(session, 1)[0].embedding is None
    assert settings.TABLE_EMBEDDING_ENABLED is True
    assert values(client)["embedding.table_enabled"] == "false"
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_query=lambda _: [0.6, 0.8]),
    )
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": True}]).status_code
        == 200
    )
    run_jobs(jobs)
    with Session(database) as session:
        assert get_ds(session, 1).embedding == "[0.6, 0.8]"
        assert get_tables_by_ds_id(session, 1)[0].embedding == "[0.6, 0.8]"


@pytest.mark.parametrize("value", [0, 1, "yes", "0", None, [], 0.5])
def test_invalid_table_switch_rejects_entire_save(environment, value):
    _database, client, _jobs = environment
    before = values(client)
    response = save(
        client,
        [
            {"pkey": "embedding.table_enabled", "pval": value},
            {"pkey": "embedding.table_count", "pval": 99},
        ],
    )
    assert response.status_code >= 400
    assert values(client) == before
