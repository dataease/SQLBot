"""Opt-in PG/pgvector contract tests.

Run explicitly with SQLBOT_RUN_EMBEDDING_INTEGRATION=1 and
SQLBOT_TEST_DATABASE_URL pointing at an authorized disposable PostgreSQL database.
Each test owns a fresh schema; no existing application rows are used.
"""

import asyncio
import json
import os
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk
from sqlalchemy import text, update
from sqlbot_xpack.config.model import SysArgModel
from sqlmodel import Session, create_engine
from test_embedding_parameters import parameter_app, save, values

from apps.ai_model.embedding import EmbeddingModelCache
from apps.ai_model.model_factory import LLMConfig
from apps.chat.curd.chat import get_chat_with_records
from apps.chat.models.chat_model import Chat, ChatLog, ChatQuestion, ChatRecord
from apps.chat.task.llm import LLMService
from apps.data_training.models.data_training_model import DataTraining
from apps.system.models.system_model import WorkspaceModel
from apps.terminology.models.terminology_model import Terminology
from common.audit.models.log_model import SystemLog, SystemLogsResource
from common.core.config import settings

pytestmark = pytest.mark.skipif(
    os.environ.get("SQLBOT_RUN_EMBEDDING_INTEGRATION") != "1",
    reason="explicit disposable PostgreSQL integration opt-in required",
)


@pytest.fixture
def knowledge_environment(monkeypatch, request):
    url = os.environ["SQLBOT_TEST_DATABASE_URL"]
    schema = "embedding_1404_" + uuid.uuid4().hex
    admin = create_engine(url)
    with admin.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    database = create_engine(
        url, connect_args={"options": f"-csearch_path={schema},public"}
    )

    def cleanup():
        database.dispose()
        with admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()

    request.addfinalizer(cleanup)
    # checkfirst=True sees public tables through search_path; create explicitly in
    # our fresh current schema before handing the engine to the real router.
    for model in (
        WorkspaceModel,
        Chat,
        ChatRecord,
        ChatLog,
        Terminology,
        DataTraining,
        SystemLog,
        SystemLogsResource,
    ):
        model.__table__.create(database)
    # Match the installed migration, which lacks the wheel model's unique pkey.
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE sys_arg (id BIGINT PRIMARY KEY, pkey VARCHAR(255), pval VARCHAR(255), ptype VARCHAR(255), sort_no INTEGER NOT NULL DEFAULT 0)"
            )
        )
        # The audit migration allows NULL operation detail and optional fields;
        # its legacy SQLModel annotations are stricter than the real schema.
        for column in SystemLog.__table__.columns:
            if not column.primary_key and not column.nullable:
                connection.execute(
                    text(
                        f'ALTER TABLE sys_logs ALTER COLUMN "{column.name}" DROP NOT NULL'
                    )
                )
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_query=lambda _query: [1.0, 0.0]),
    )
    monkeypatch.setattr(settings, "EMBEDDING_ENABLED", True)
    monkeypatch.setattr(settings, "EMBEDDING_TERMINOLOGY_TOP_COUNT", 1)
    monkeypatch.setattr(settings, "EMBEDDING_DATA_TRAINING_TOP_COUNT", 1)
    monkeypatch.setattr(settings, "EMBEDDING_TERMINOLOGY_SIMILARITY", 0.5)
    monkeypatch.setattr(settings, "EMBEDDING_DATA_TRAINING_SIMILARITY", 0.5)
    with TestClient(
        parameter_app(database, monkeypatch), raise_server_exceptions=False
    ) as client:
        with Session(database) as session:
            session.add(WorkspaceModel(id=1, name="test"))
            chat = Chat(
                oid=1,
                brief="test",
                create_by=1,
                create_time=datetime.now(),
                engine_type="PostgreSQL",
            )
            session.add(chat)
            session.flush()
            chat_id = chat.id
            for oid, datasource, application in [
                (1, 10, None),
                (1, None, 99),
                (2, 10, None),
            ]:
                for word, vector in [
                    ("alpha", [1, 0]),
                    ("beta", [0.8, 0.6]),
                    ("literal", [0, 1]),
                ]:
                    session.add(
                        Terminology(
                            oid=oid,
                            word=word,
                            description=f"term-{word}-{oid}-{application}",
                            embedding=vector,
                            enabled=True,
                            specific_ds=True,
                            datasource_ids=[datasource] if datasource else [],
                            advanced_application=application,
                        )
                    )
                    session.add(
                        DataTraining(
                            oid=oid,
                            question=word,
                            description=f"example-{word}-{oid}-{application}",
                            embedding=vector,
                            enabled=True,
                            datasource=datasource,
                            advanced_application=application,
                        )
                    )
            session.commit()
        yield database, client, chat_id


def question_task(session, chat_id, assistant=None):
    user = SimpleNamespace(id=1, oid=1, language="en")
    service = LLMService(
        session,
        user,
        ChatQuestion(chat_id=chat_id, question="literal query"),
        current_assistant=assistant,
        config=LLMConfig(
            model_type="openai",
            model_name="test",
            api_key="test",
            api_base_url="http://127.0.0.1:9/v1",
        ),
    )
    service.init_record(session)
    return service


def recall(service, session):
    service.filter_terminology_template(session, 1, 10)
    service.filter_training_template(session, 1, 10)
    return service.chat_question.terminologies, service.chat_question.data_training


def test_new_question_uses_saved_counts_and_in_flight_question_keeps_snapshot(
    knowledge_environment,
):
    database, client, chat_id = knowledge_environment
    with Session(database) as session:
        old_task = question_task(session, chat_id)
        before = recall(old_task, session)
        assert "term-alpha-1-None" in before[0] and "term-beta" not in before[0]
        assert "example-alpha-1-None" in before[1] and "example-beta" not in before[1]
        assert (
            save(
                client,
                [
                    {"pkey": "embedding.terminology_top_count", "pval": 2},
                    {"pkey": "embedding.data_training_top_count", "pval": 2},
                ],
            ).status_code
            == 200
        )
        assert recall(old_task, session) == before
    with Session(database) as session:
        result = recall(question_task(session, chat_id), session)
        assert "term-beta-1-None" in result[0]
        assert "example-beta-1-None" in result[1]
        assert (
            "term-literal-1-None" in result[0] and "example-literal-1-None" in result[1]
        )
        assert "-2-" not in "".join(result)
        assert "-1-99" not in "".join(result)


def test_strict_threshold_preserves_literal_matches_and_advanced_knowledge_scope(
    knowledge_environment,
):
    database, client, chat_id = knowledge_environment
    assert (
        save(
            client,
            [
                {"pkey": "embedding.terminology_similarity", "pval": 1},
                {"pkey": "embedding.data_training_similarity", "pval": 1},
            ],
        ).status_code
        == 200
    )
    with Session(database) as session:
        result = recall(question_task(session, chat_id), session)
        assert "alpha" not in "".join(result)
        assert "literal" in result[0] and "literal" in result[1]
        advanced = question_task(
            session, chat_id, SimpleNamespace(type=1, id=99, oid=1)
        )
        result = recall(advanced, session)
        assert "term-literal-1-99" in result[0] and "example-literal-1-99" in result[1]
        assert "-1-None" not in "".join(result)
    assert values(client)["embedding.terminology_similarity"] == "1.0"


def test_analysis_retrieves_terms_using_new_settings_and_historical_keywords(
    knowledge_environment,
):
    database, client, chat_id = knowledge_environment
    with Session(database) as session:
        session.add(
            Terminology(
                oid=1,
                word="literal",
                description="historical-keyword",
                embedding=[0, 1],
                specific_ds=False,
            )
        )
        session.add(
            Terminology(
                oid=1,
                word="global-vector",
                description="vector-only",
                embedding=[1, 0],
                specific_ds=False,
            )
        )
        session.commit()
        old_task = question_task(session, chat_id)
        assert (
            save(
                client,
                [
                    {"pkey": "embedding.terminology_similarity", "pval": 1},
                    {"pkey": "embedding.keyword_enabled", "pval": False},
                ],
            ).status_code
            == 200
        )
        new_task = question_task(session, chat_id)
        messages = []

        def stream(value):
            messages.extend(value)
            return iter([AIMessageChunk(content="analysis result")])

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
        assert "vector-only" in old_task.chat_question.terminologies
        assert "vector-only" not in new_task.chat_question.terminologies
        assert "historical-keyword" in new_task.chat_question.terminologies
        assert any("historical-keyword" in str(message.content) for message in messages)
        records = get_chat_with_records(
            session, chat_id, new_task.current_user, None
        ).records
        assert any(record["analysis"] == "analysis result" for record in records)


def test_new_task_in_another_process_uses_api_saved_settings(knowledge_environment):
    database, client, chat_id = knowledge_environment
    assert (
        save(
            client,
            [
                {"pkey": "embedding.terminology_top_count", "pval": 1},
                {"pkey": "embedding.data_training_top_count", "pval": 1},
            ],
        ).status_code
        == 200
    )
    with database.connect() as connection:
        schema = connection.execute(text("select current_schema()")).scalar_one()
    script = """
import json, os
from types import SimpleNamespace
from sqlmodel import Session, create_engine
from apps.ai_model.embedding import EmbeddingModelCache
from test_embedding_parameters_integration import question_task, recall
EmbeddingModelCache.get_model = staticmethod(lambda: SimpleNamespace(embed_query=lambda _: [1.0, 0.0]))
db = create_engine(os.environ['SQLBOT_TEST_DATABASE_URL'], connect_args={'options': '-csearch_path=' + os.environ['SQLBOT_TEST_SCHEMA'] + ',public'})
with Session(db) as session:
    result = recall(question_task(session, int(os.environ['SQLBOT_TEST_CHAT_ID'])), session)
    print('RESULT:' + json.dumps(result))
db.dispose()
"""
    env = {
        **os.environ,
        "EMBEDDING_ENABLED": "true",
        "EMBEDDING_TERMINOLOGY_SIMILARITY": "0.5",
        "EMBEDDING_DATA_TRAINING_SIMILARITY": "0.5",
        "EMBEDDING_TERMINOLOGY_TOP_COUNT": "5",
        "EMBEDDING_DATA_TRAINING_TOP_COUNT": "5",
        "SQLBOT_TEST_SCHEMA": schema,
        "SQLBOT_TEST_CHAT_ID": str(chat_id),
        "PYTHONPATH": os.pathsep.join(
            [
                str(Path(__file__).parent.resolve()),
                str(Path(__file__).parents[1].resolve()),
            ]
        ),
    }
    process = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(
        next(
            line.removeprefix("RESULT:")
            for line in process.stdout.splitlines()
            if line.startswith("RESULT:")
        )
    )
    # The child process has startup count=5, so beta's exclusion proves it read
    # the persisted count rather than merely matching the startup defaults.
    assert "term-alpha-1-None" in result[0] and "term-beta" not in result[0]
    assert "example-alpha-1-None" in result[1] and "example-beta" not in result[1]


def test_legacy_duplicate_keys_have_deterministic_effective_value_and_can_be_saved(
    knowledge_environment,
):
    database, client, _chat_id = knowledge_environment
    with Session(database) as session:
        session.add(
            SysArgModel(id=100, pkey="embedding.terminology_top_count", pval="3")
        )
        session.add(
            SysArgModel(id=101, pkey="embedding.terminology_top_count", pval="7")
        )
        session.commit()
    assert values(client)["embedding.terminology_top_count"] == "7"
    assert (
        save(
            client, [{"pkey": "embedding.terminology_top_count", "pval": 4}]
        ).status_code
        == 200
    )
    assert values(client)["embedding.terminology_top_count"] == "4"


def test_waiting_for_another_parameter_writer_does_not_block_requests(
    knowledge_environment, monkeypatch
):
    database, _client, _chat_id = knowledge_environment
    app = parameter_app(database, monkeypatch)
    ready = threading.Event()

    def hold_lock():
        with database.begin() as connection:
            connection.execute(
                text("SELECT pg_advisory_xact_lock(:key)"), {"key": 14030001}
            )
            ready.set()
            time.sleep(1)

    holder = threading.Thread(target=hold_lock)
    holder.start()
    assert ready.wait(timeout=2)

    async def requests():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app), base_url="http://testserver"
        ) as client:
            started = time.monotonic()
            writer = asyncio.create_task(
                client.post(
                    "/system/parameter",
                    data={
                        "data": json.dumps(
                            [
                                {"pkey": "embedding.terminology_top_count", "pval": 4},
                            ]
                        )
                    },
                )
            )
            await asyncio.sleep(0.1)
            response = await client.get("/system/parameter")
            assert response.status_code == 200
            assert time.monotonic() - started < 0.5
            assert (await writer).status_code == 200

    try:
        asyncio.run(requests())
    finally:
        holder.join(timeout=3)
