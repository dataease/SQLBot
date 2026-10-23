"""Offline API and resource-task regressions; providers never use the network."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Integer, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine
from test_embedding_parameters import parameter_app, save, values

from apps.ai_model.embedding import EmbeddingModelCache
from apps.data_training.curd.data_training import create_training, update_training
from apps.data_training.models.data_training_model import DataTraining, DataTrainingInfo
from common.core.config import settings
from common.utils import embedding_threads
from common.utils.embedding_lifecycle import EmbeddingGenerationError


@pytest.fixture
def environment(monkeypatch):
    database = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    # SQLite's auto-ID spelling differs; the resource/API/task code stays real.
    metadata = MetaData()
    table = DataTraining.__table__.to_metadata(metadata)
    table.c.id.type = Integer()
    metadata.create_all(database)
    maker = scoped_session(sessionmaker(bind=database))
    jobs = []
    monkeypatch.setattr(embedding_threads, "session_maker", maker)
    monkeypatch.setattr(
        embedding_threads,
        "executor",
        SimpleNamespace(submit=lambda function, *args: jobs.append((function, args))),
    )
    monkeypatch.setattr(settings, "EMBEDDING_ENABLED", True)
    with TestClient(
        parameter_app(database, monkeypatch), raise_server_exceptions=False
    ) as client:
        yield database, client, jobs
    maker.remove()
    database.dispose()


def run_jobs(jobs):
    while jobs:
        function, args = jobs.pop(0)
        function(*args)


def add_example(database, question="queued question"):
    with Session(database) as session:
        return create_training(
            session,
            DataTrainingInfo(question=question, description="select 1", datasource=10),
            1,
            lambda key: key,
        )


def test_queued_resource_task_uses_persisted_switch_when_it_starts(
    environment, monkeypatch
):
    database, client, jobs = environment
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: pytest.fail("disabled task contacted provider"),
    )
    resource_id = add_example(database)
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code == 200
    )
    run_jobs(jobs)
    with Session(database) as session:
        assert session.get(DataTraining, resource_id).embedding is None
    assert settings.EMBEDDING_ENABLED is True
    assert values(client)["embedding.enabled"] == "false"


@pytest.mark.parametrize("value", [0, 1, "yes", "0", None, [], 0.5])
def test_invalid_switch_rejects_whole_parameter_save(environment, value):
    _database, client, _jobs = environment
    before = values(client)
    assert (
        save(
            client,
            [
                {"pkey": "embedding.enabled", "pval": value},
                {"pkey": "embedding.terminology_top_count", "pval": 99},
            ],
        ).status_code
        >= 400
    )
    assert values(client) == before


def test_provider_failure_is_visible_and_pending_resource_can_retry(
    environment, monkeypatch
):
    database, _client, jobs = environment
    resource_id = add_example(database)

    def fail(_words):
        raise ConnectionError("controlled provider unavailable")

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: SimpleNamespace(embed_documents=fail)
    )
    with pytest.raises(EmbeddingGenerationError):
        run_jobs(jobs)
    with Session(database) as session:
        assert session.get(DataTraining, resource_id).embedding is None
        update_training(
            session,
            DataTrainingInfo(
                id=resource_id,
                question="queued question",
                description="select 2",
                datasource=10,
            ),
            1,
            lambda key: key,
        )
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_documents=lambda words: [[1, 0] for _ in words]),
    )
    run_jobs(jobs)
    with Session(database) as session:
        assert list(session.get(DataTraining, resource_id).embedding) == [1, 0]


def test_transient_provider_failure_recovers_within_task(environment, monkeypatch):
    database, _client, jobs = environment
    resource_id = add_example(database)
    responses = iter([ConnectionError("temporary"), [[0.6, 0.8]]])

    def embed(_words):
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: SimpleNamespace(embed_documents=embed)
    )
    run_jobs(jobs)
    with Session(database) as session:
        assert list(session.get(DataTraining, resource_id).embedding) == pytest.approx(
            [0.6, 0.8]
        )


@pytest.mark.parametrize("role", ["anonymous", "user", "workspace-admin"])
def test_only_system_admin_can_toggle_knowledge(environment, role):
    _database, client, _jobs = environment
    before = values(client)
    assert (
        save(
            client,
            [{"pkey": "embedding.enabled", "pval": False}],
            headers={"test-role": role},
        ).status_code
        >= 400
    )
    assert values(client) == before


@pytest.mark.parametrize(
    "vector", [[0, 0], [float("nan"), 1], [float("inf"), 1], [True, 0], ["1", 0], []]
)
def test_unusable_provider_vectors_remain_pending(environment, monkeypatch, vector):
    database, _client, jobs = environment
    resource_id = add_example(database)
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_documents=lambda _words: [vector]),
    )
    with pytest.raises(EmbeddingGenerationError):
        run_jobs(jobs)
    with Session(database) as session:
        assert session.get(DataTraining, resource_id).embedding is None
