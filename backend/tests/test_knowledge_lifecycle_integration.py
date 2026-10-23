"""Opt-in knowledge resource/task regressions on disposable PG/pgvector."""

import os
from concurrent.futures import Future

import pytest
import test_embedding_parameters_integration as parameter_contracts
from sqlmodel import Session, select
from test_embedding_parameters import save, values
from test_embedding_parameters_integration import (
    question_task,
    recall,
)

from apps.data_training.curd.data_training import update_training
from apps.data_training.models.data_training_model import DataTraining, DataTrainingInfo
from apps.terminology.curd.terminology import update_terminology
from apps.terminology.models.terminology_model import Terminology, TerminologyInfo
from common.utils import embedding_threads

knowledge_environment = parameter_contracts.knowledge_environment

pytestmark = pytest.mark.skipif(
    os.environ.get("SQLBOT_RUN_EMBEDDING_INTEGRATION") != "1",
    reason="explicit disposable PostgreSQL integration opt-in required",
)


class QueuedExecutor:
    """Controllable scheduling boundary; jobs run only when the test starts them."""

    def __init__(self):
        self.jobs = []

    def submit(self, function, *args, **kwargs):
        result = Future()
        self.jobs.append((function, args, kwargs, result))
        return result

    def drain(self):
        while self.jobs:
            function, args, kwargs, result = self.jobs.pop(0)
            try:
                result.set_result(function(*args, **kwargs))
            except Exception as exc:
                result.set_exception(exc)
                raise


@pytest.fixture
def lifecycle_environment(knowledge_environment, monkeypatch):
    from sqlalchemy.orm import scoped_session, sessionmaker

    database, client, chat_id = knowledge_environment
    queue = QueuedExecutor()
    maker = scoped_session(sessionmaker(bind=database))
    monkeypatch.setattr(embedding_threads, "executor", queue)
    monkeypatch.setattr(embedding_threads, "session_maker", maker)
    yield database, client, chat_id, queue
    maker.remove()


def test_disabled_knowledge_keeps_literal_recall_and_invalidates_edited_inputs(
    lifecycle_environment,
):
    database, client, chat_id, queue = lifecycle_environment
    with Session(database) as session:
        old_task = question_task(session, chat_id)
        before = recall(old_task, session)
        assert "term-alpha" in before[0]
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code == 200
    )
    assert values(client)["embedding.enabled"] == "false"
    with Session(database) as session:
        assert recall(old_task, session) == before
        result = recall(question_task(session, chat_id), session)
        assert "alpha" not in "".join(result)
        assert "literal" in result[0] and "literal" in result[1]
        term = session.exec(
            select(Terminology).where(
                Terminology.word == "alpha",
                Terminology.oid == 1,
                Terminology.advanced_application.is_(None),
            )
        ).first()
        example = session.exec(
            select(DataTraining).where(
                DataTraining.question == "alpha",
                DataTraining.oid == 1,
                DataTraining.datasource == 10,
            )
        ).first()
        term_id, example_id = term.id, example.id
        update_terminology(
            session,
            TerminologyInfo(
                id=term_id,
                word="new term",
                description="edited",
                other_words=["new synonym"],
                specific_ds=True,
                datasource_ids=[10],
                enabled=True,
            ),
            1,
            lambda key: key,
        )
        update_training(
            session,
            DataTrainingInfo(
                id=example_id,
                question="new question",
                description="select 1",
                datasource=10,
                enabled=True,
            ),
            1,
            lambda key: key,
        )
    queue.drain()
    with Session(database) as session:
        assert session.get(Terminology, term_id).embedding is None
        assert session.get(DataTraining, example_id).embedding is None
        synonym = session.exec(
            select(Terminology).where(Terminology.pid == term_id)
        ).one()
        assert synonym.embedding is None


def test_reenable_fills_missing_vectors_and_keeps_valid_vectors(
    lifecycle_environment, monkeypatch
):
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.data_training.curd.data_training import create_training
    from apps.terminology.curd.terminology import create_terminology

    database, client, _chat_id, queue = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code == 200
    )
    with Session(database) as session:
        term_id = create_terminology(
            session,
            TerminologyInfo(
                word="missing term",
                description="meaning",
                other_words=["missing synonym"],
                specific_ds=True,
                datasource_ids=[10],
            ),
            1,
            lambda key: key,
        )
        example_id = create_training(
            session,
            DataTrainingInfo(
                question="missing question", description="select 1", datasource=10
            ),
            1,
            lambda key: key,
        )
    queue.drain()
    generated = []

    def embed_documents(words):
        generated.extend(words)
        return [[0.6, 0.8] for _word in words]

    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_documents=embed_documents),
    )
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": True}]).status_code == 200
    )
    # Saving only queues work: a slow embedding provider cannot block the API.
    assert generated == []
    queue.drain()
    with Session(database) as session:
        assert list(session.get(Terminology, term_id).embedding) == pytest.approx(
            [0.6, 0.8]
        )
        assert list(session.get(DataTraining, example_id).embedding) == pytest.approx(
            [0.6, 0.8]
        )
        assert list(
            session.exec(select(Terminology).where(Terminology.pid == term_id))
            .one()
            .embedding
        ) == pytest.approx([0.6, 0.8])
    assert sorted(generated) == ["missing question", "missing synonym", "missing term"]


@pytest.mark.parametrize("kind", ["terminology", "data_training"])
@pytest.mark.parametrize("change", ["edit", "delete", "unchanged"])
def test_in_flight_old_content_cannot_restore_invalidated_or_deleted_vectors(
    lifecycle_environment,
    monkeypatch,
    kind,
    change,
):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.data_training.curd.data_training import create_training, delete_training
    from apps.terminology.curd.terminology import create_terminology, delete_terminology

    database, client, _chat_id, queue = lifecycle_environment
    entered, release = threading.Event(), threading.Event()

    def embed_documents(words):
        entered.set()
        assert release.wait(10), "test did not release provider"
        return [[1, 0] for _ in words]

    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_documents=embed_documents),
    )
    with Session(database) as session:
        if kind == "terminology":
            resource_id = create_terminology(
                session,
                TerminologyInfo(
                    word="old term",
                    description="meaning",
                    other_words=["old synonym"],
                    specific_ds=True,
                    datasource_ids=[10],
                ),
                1,
                lambda key: key,
            )
            model = Terminology
        else:
            resource_id = create_training(
                session,
                DataTrainingInfo(
                    question="old question", description="select 1", datasource=10
                ),
                1,
                lambda key: key,
            )
            model = DataTraining
    function, args, kwargs, _result = queue.jobs.pop(0)
    with ThreadPoolExecutor(max_workers=1) as pool:
        task = pool.submit(function, *args, **kwargs)
        try:
            assert entered.wait(10), "generation never reached provider"
            assert (
                save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code
                == 200
            )
            with Session(database) as session:
                if change == "delete":
                    (delete_terminology if kind == "terminology" else delete_training)(
                        session, [resource_id], 1
                    )
                elif change == "edit" and kind == "terminology":
                    update_terminology(
                        session,
                        TerminologyInfo(
                            id=resource_id,
                            word="new term",
                            description="meaning",
                            other_words=["new synonym"],
                            specific_ds=True,
                            datasource_ids=[10],
                        ),
                        1,
                        lambda key: key,
                    )
                elif change == "edit":
                    update_training(
                        session,
                        DataTrainingInfo(
                            id=resource_id,
                            question="new question",
                            description="select 1",
                            datasource=10,
                        ),
                        1,
                        lambda key: key,
                    )
        finally:
            release.set()
        task.result(timeout=10)
    queue.drain()
    with Session(database) as session:
        resource = session.get(model, resource_id)
        if change == "delete":
            assert resource is None
        elif change == "unchanged":
            assert list(resource.embedding) == [1, 0]
        else:
            assert resource.embedding is None


def test_concurrent_startup_and_resource_job_generate_each_input_once(
    lifecycle_environment, monkeypatch
):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.data_training.curd.data_training import create_training

    database, _client, _chat_id, queue = lifecycle_environment
    entered, release = threading.Event(), threading.Event()
    import time
    import uuid

    from sqlalchemy import event, text

    application = "knowledge-concurrency-" + uuid.uuid4().hex

    def identify_connection(connection, _record, _proxy):
        connection.execute(
            "SELECT set_config('application_name', %s, false)", (application,)
        )
        connection.commit()

    event.listen(database, "checkout", identify_connection)
    duplicate = threading.Event()
    generated = []

    def embed_documents(words):
        generated.extend(words)
        if len(generated) > 1:
            duplicate.set()
        entered.set()
        assert release.wait(10)
        return [[1, 0] for _ in words]

    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_documents=embed_documents),
    )
    with Session(database) as session:
        create_training(
            session,
            DataTrainingInfo(
                question="concurrent question", description="select 1", datasource=10
            ),
            1,
            lambda key: key,
        )
    embedding_threads.fill_empty_data_training_embeddings()
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [
            pool.submit(function, *args, **kwargs)
            for function, args, kwargs, _ in queue.jobs
        ]
        try:
            assert entered.wait(10)
            deadline = time.monotonic() + 10
            while not duplicate.is_set():
                with database.connect() as connection:
                    waiting = connection.execute(
                        text(
                            "SELECT count(*) FROM pg_stat_activity WHERE application_name = :name AND wait_event = 'advisory'"
                        ),
                        {"name": application},
                    ).scalar_one()
                if waiting:
                    break
                assert time.monotonic() < deadline, (
                    "neither duplicate provider nor lock contention observed"
                )
                duplicate.wait(0.01)
        finally:
            release.set()
        for task in tasks:
            task.result(timeout=10)
    assert generated == ["concurrent question"]


def test_synonym_edit_preserves_unchanged_vectors(lifecycle_environment, monkeypatch):
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.terminology.curd.terminology import create_terminology

    database, client, _chat_id, queue = lifecycle_environment
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_documents=lambda words: [[1, 0] for _ in words]),
    )
    with Session(database) as session:
        resource_id = create_terminology(
            session,
            TerminologyInfo(
                word="main",
                description="meaning",
                other_words=["keep", "remove"],
                specific_ds=True,
                datasource_ids=[10],
            ),
            1,
            lambda key: key,
        )
    queue.drain()
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code == 200
    )
    with Session(database) as session:
        update_terminology(
            session,
            TerminologyInfo(
                id=resource_id,
                word="main",
                description="new meaning",
                other_words=["keep", "added"],
                specific_ds=True,
                datasource_ids=[10],
            ),
            1,
            lambda key: key,
        )
    queue.drain()
    with Session(database) as session:
        rows = session.exec(
            select(Terminology).where(
                (Terminology.id == resource_id) | (Terminology.pid == resource_id)
            )
        ).all()
        vectors = {row.word: row.embedding for row in rows}
        assert set(vectors) == {"main", "keep", "added"}
        assert list(vectors["main"]) == [1, 0]
        assert list(vectors["keep"]) == [1, 0]
        assert vectors["added"] is None


@pytest.mark.parametrize("other_words", [None, [], [" "]])
def test_update_terminology_can_clear_all_synonyms(lifecycle_environment, other_words):
    from apps.terminology.curd.terminology import create_terminology

    database, client, _chat_id, queue = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code == 200
    )
    with Session(database) as session:
        resource_id = create_terminology(
            session,
            TerminologyInfo(word="main", description="meaning", other_words=["alias"]),
            1,
            lambda key: key,
        )
        assert (
            update_terminology(
                session,
                TerminologyInfo(
                    id=resource_id,
                    word="main",
                    description="updated",
                    other_words=other_words,
                ),
                1,
                lambda key: key,
            )
            == resource_id
        )
    queue.drain()
    with Session(database) as session:
        assert session.get(Terminology, resource_id).description == "updated"
        assert (
            session.exec(
                select(Terminology).where(Terminology.pid == resource_id)
            ).all()
            == []
        )


@pytest.mark.parametrize("crash_first_worker", [False, True])
def test_processes_share_fill_locks_and_restart_recovers_pending_work(
    lifecycle_environment,
    tmp_path,
    crash_first_worker,
):
    import json
    import subprocess
    import sys
    import time
    import uuid

    from sqlalchemy import text

    from apps.data_training.curd.data_training import create_training
    from apps.terminology.curd.terminology import create_terminology

    database, client, _chat_id, queue = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code == 200
    )
    with Session(database) as session:
        term_id = create_terminology(
            session,
            TerminologyInfo(
                word="process term",
                description="meaning",
                specific_ds=True,
                datasource_ids=[10],
            ),
            1,
            lambda key: key,
        )
        example_id = create_training(
            session,
            DataTrainingInfo(
                question="process question", description="select 1", datasource=10
            ),
            1,
            lambda key: key,
        )
        schema = session.execute(text("SELECT current_schema()")).scalar_one()
    queue.drain()
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": True}]).status_code == 200
    )
    application = "knowledge-process-" + uuid.uuid4().hex
    worker = tmp_path / "worker.py"
    worker.write_text("""
import json, sys, time
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from apps.ai_model.embedding import EmbeddingModelCache
from common.core.config import settings
from common.utils import embedding_threads
url, schema, application, directory = sys.argv[1:]
directory = Path(directory)
settings.EMBEDDING_ENABLED = False
engine = create_engine(url, connect_args={"options": "-csearch_path=" + schema + ",public", "application_name": application})
embedding_threads.session_maker = scoped_session(sessionmaker(bind=engine))
def embed_documents(words):
    with (directory / "generated.jsonl").open("a") as output:
        output.write(json.dumps(words) + "\\n")
    deadline = time.monotonic() + 30
    while not (directory / "release").exists():
        if time.monotonic() >= deadline:
            raise TimeoutError("provider barrier was not released")
        time.sleep(0.01)
    return [[0.6, 0.8] for _ in words]
EmbeddingModelCache.get_model = staticmethod(lambda: SimpleNamespace(embed_documents=embed_documents))
embedding_threads.fill_empty_terminology_embeddings().result(timeout=35)
embedding_threads.fill_empty_data_training_embeddings().result(timeout=35)
embedding_threads.executor.shutdown(wait=True)
engine.dispose()
print("completed")
""")
    command = [
        sys.executable,
        str(worker),
        database.url.render_as_string(hide_password=False),
        schema,
        application,
        str(tmp_path),
    ]
    processes = []

    def await_state(predicate, message):
        deadline = time.monotonic() + 25
        while not predicate():
            assert time.monotonic() < deadline, message
            for process in processes:
                assert process.poll() is None, process.communicate()[1]
            time.sleep(0.01)

    try:
        first = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        processes.append(first)
        await_state(
            lambda: (tmp_path / "generated.jsonl").exists(),
            "first worker did not reach provider",
        )
        second = subprocess.Popen(
            command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        processes.append(second)

        def second_is_waiting():
            with database.connect() as connection:
                return (
                    connection.execute(
                        text(
                            "SELECT count(*) FROM pg_stat_activity WHERE application_name=:name AND wait_event='advisory'"
                        ),
                        {"name": application},
                    ).scalar_one()
                    == 1
                )

        await_state(
            second_is_waiting, "second process did not wait on shared resource lock"
        )
        if crash_first_worker:
            first.kill()
            first.communicate(timeout=10)
            processes.remove(first)
            await_state(
                lambda: (
                    len((tmp_path / "generated.jsonl").read_text().splitlines()) == 2
                ),
                "surviving worker did not recover",
            )
        (tmp_path / "release").touch()
        for process in processes:
            stdout, stderr = process.communicate(timeout=35)
            assert process.returncode == 0, stderr
            assert "completed" in stdout
    finally:
        (tmp_path / "release").touch()
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
    generated = [
        word
        for line in (tmp_path / "generated.jsonl").read_text().splitlines()
        for word in json.loads(line)
    ]
    assert generated.count("process term") == (2 if crash_first_worker else 1)
    assert generated.count("process question") == 1
    with Session(database) as session:
        assert list(session.get(Terminology, term_id).embedding) == pytest.approx(
            [0.6, 0.8]
        )
        assert list(session.get(DataTraining, example_id).embedding) == pytest.approx(
            [0.6, 0.8]
        )


def test_disabled_batch_import_and_reenable_preserve_advanced_scope(
    lifecycle_environment, monkeypatch
):
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.data_training.curd.data_training import batch_create_training
    from apps.datasource.models.datasource import CoreDatasource
    from apps.system.models.system_model import AssistantModel
    from apps.terminology.curd.terminology import batch_create_terminology

    database, client, chat_id, queue = lifecycle_environment
    CoreDatasource.__table__.create(database)
    AssistantModel.__table__.create(database)
    with Session(database) as session:
        session.add(
            AssistantModel(
                id=99,
                oid=1,
                name="import application",
                type=1,
                domain="http://localhost",
            )
        )
        session.commit()
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code == 200
    )
    with Session(database) as session:
        term = batch_create_terminology(
            session,
            [
                TerminologyInfo(
                    word="import main",
                    description="imported term",
                    other_words=["query"],
                    specific_ds=True,
                    advanced_application_name="import application",
                )
            ],
            1,
            lambda key: key,
        )
        example = batch_create_training(
            session,
            [
                DataTrainingInfo(
                    question="query",
                    description="imported SQL",
                    advanced_application_name="import application",
                )
            ],
            1,
            lambda key: key,
        )
        assert term["success_count"] == 1, term
        assert example["success_count"] == 1, example
    queue.drain()
    with Session(database) as session:
        imported = session.exec(
            select(Terminology).where(Terminology.description == "imported term")
        ).one()
        synonym = session.exec(
            select(Terminology).where(Terminology.pid == imported.id)
        ).one()
        assert imported.embedding is None and synonym.embedding is None
        synonym_id = synonym.id
        result = recall(
            question_task(session, chat_id, SimpleNamespace(type=1, id=99, oid=1)),
            session,
        )
        assert "imported term" in result[0] and "imported SQL" in result[1]
        ordinary = recall(question_task(session, chat_id), session)
        assert "imported" not in "".join(ordinary)
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(
            embed_documents=lambda words: [[1, 0] for _ in words],
            embed_query=lambda _word: [1, 0],
        ),
    )
    assert (
        save(client, [{"pkey": "embedding.enabled", "pval": True}]).status_code == 200
    )
    queue.drain()
    with Session(database) as session:
        assert list(session.get(Terminology, synonym_id).embedding) == [1, 0]
        ordinary = recall(question_task(session, chat_id), session)
        assert "imported" not in "".join(ordinary)


def test_new_analysis_uses_disabled_snapshot_and_historical_literal_terms(
    lifecycle_environment,
):
    from types import SimpleNamespace

    from langchain_core.messages import AIMessageChunk
    from sqlalchemy import update

    from apps.chat.curd.chat import get_chat_with_records
    from apps.chat.models.chat_model import ChatRecord

    database, client, chat_id, _queue = lifecycle_environment
    with Session(database) as session:
        session.add(
            Terminology(
                word="literal",
                description="analysis literal",
                oid=1,
                embedding=[0, 1],
                specific_ds=False,
            )
        )
        session.add(
            Terminology(
                word="semantic",
                description="analysis vector",
                oid=1,
                embedding=[1, 0],
                specific_ds=False,
            )
        )
        session.commit()
        old_task = question_task(session, chat_id)
        assert (
            save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code
            == 200
        )
        new_task = question_task(session, chat_id)
        messages = []

        def stream(value):
            messages.extend(value)
            return iter([AIMessageChunk(content="knowledge analysis")])

        for task in (old_task, new_task):
            task.record.extracted_keywords = "literal"
            task.chat_question.question = "unrelated original question"
            session.execute(
                update(ChatRecord)
                .where(ChatRecord.id == task.record.id)
                .values(extracted_keywords="literal")
            )
            session.commit()
            task.llm = SimpleNamespace(stream=stream)
            list(task.generate_analysis(session))
        assert "analysis vector" in old_task.chat_question.terminologies
        assert "analysis vector" not in new_task.chat_question.terminologies
        assert "analysis literal" in new_task.chat_question.terminologies
        assert any("analysis literal" in str(message.content) for message in messages)
        records = get_chat_with_records(
            session, chat_id, new_task.current_user, None
        ).records
        assert any(record["analysis"] == "knowledge analysis" for record in records)


@pytest.mark.parametrize("query_provider_fails", [False, True])
def test_failed_generation_keeps_literal_and_available_vector_recall(
    lifecycle_environment,
    monkeypatch,
    query_provider_fails,
):
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.data_training.curd.data_training import create_training
    from common.utils.embedding_lifecycle import EmbeddingGenerationError

    database, _client, chat_id, queue = lifecycle_environment

    def fail(_value):
        raise ConnectionError("controlled provider failure")

    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(
            embed_documents=fail,
            embed_query=fail if query_provider_fails else lambda _value: [1, 0],
        ),
    )
    with Session(database) as session:
        resource_id = create_training(
            session,
            DataTrainingInfo(
                question="pending question", description="pending SQL", datasource=10
            ),
            1,
            lambda key: key,
        )
    with pytest.raises(EmbeddingGenerationError):
        queue.drain()
    with Session(database) as session:
        assert session.get(DataTraining, resource_id).embedding is None
        result = recall(question_task(session, chat_id), session)
        assert "literal" in result[0] and "literal" in result[1]
        assert ("alpha" in result[0]) is not query_provider_fails
        assert ("alpha" in result[1]) is not query_provider_fails


def test_off_then_on_during_old_generation_fills_latest_input(
    lifecycle_environment, monkeypatch
):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.data_training.curd.data_training import create_training

    database, client, _chat_id, queue = lifecycle_environment
    entered, release = threading.Event(), threading.Event()
    generated = []

    def embed_documents(words):
        generated.extend(words)
        if "old input" in words:
            entered.set()
            assert release.wait(10)
        return [[1, 0] if word == "old input" else [0, 1] for word in words]

    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_documents=embed_documents),
    )
    with Session(database) as session:
        resource_id = create_training(
            session,
            DataTrainingInfo(
                question="old input", description="select 1", datasource=10
            ),
            1,
            lambda key: key,
        )
    function, args, kwargs, _future = queue.jobs.pop(0)
    with ThreadPoolExecutor(max_workers=3) as pool:
        old_task = pool.submit(function, *args, **kwargs)
        try:
            assert entered.wait(10)
            assert (
                save(client, [{"pkey": "embedding.enabled", "pval": False}]).status_code
                == 200
            )
            with Session(database) as session:
                update_training(
                    session,
                    DataTrainingInfo(
                        id=resource_id,
                        question="new input",
                        description="select 2",
                        datasource=10,
                    ),
                    1,
                    lambda key: key,
                )
            queue.drain()  # The edit job really starts while the switch is off.
            assert (
                save(client, [{"pkey": "embedding.enabled", "pval": True}]).status_code
                == 200
            )
            tasks = [
                pool.submit(function, *args, **kwargs)
                for function, args, kwargs, _future in queue.jobs
            ]
        finally:
            release.set()
        old_task.result(timeout=10)
        for task in tasks:
            task.result(timeout=10)
    with Session(database) as session:
        assert list(session.get(DataTraining, resource_id).embedding) == [0, 1]
    assert generated == ["old input", "new input"]


@pytest.mark.parametrize("vector", [[0, 0], [float("nan"), 1], []])
def test_unusable_query_vector_falls_back_to_literal_knowledge(
    lifecycle_environment, monkeypatch, vector
):
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache

    database, _client, chat_id, _queue = lifecycle_environment
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_query=lambda _question: vector),
    )
    with Session(database) as session:
        result = recall(question_task(session, chat_id), session)
        assert "literal" in result[0] and "literal" in result[1]
        assert "alpha" not in "".join(result)
