"""Opt-in task and transport coverage for completed automatic datasource queries."""

import json
from types import SimpleNamespace

import pytest
import test_table_parameters_integration as contracts
from langchain_core.messages import AIMessageChunk
from sqlmodel import Session
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)
from test_query_embedding import embedding_model

from apps.ai_model.embedding import EmbeddingModelCache
from apps.chat.models.chat_model import Chat, ChatRecord

table_environment = contracts.table_environment


def is_completion_request(messages):
    try:
        transcript = json.loads(messages[-1].content)
    except (ValueError, TypeError):
        return False
    return (
        isinstance(transcript, dict)
        and isinstance(transcript.get("history"), list)
        and isinstance(transcript.get("current"), dict)
    )


def test_completed_intent_selects_source_then_preserves_original_sql_question(
    table_environment, monkeypatch
):
    database, client, ds_id = table_environment
    contracts.add_datasource_candidates(database)
    contracts.configure(
        client, datasource_count=1, table_count=3, keyword_enabled=False, enabled=False
    )
    calls = []
    model = embedding_model(limit=512)

    def encode(query):
        calls.append(query)
        return [1, 0] if "sales" in query else [0, 1]

    model.embed_query = encode
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: model)
    current = contracts.task(database, None, question="and last year?")
    completed = "sales totals last year excluding refunds"
    contexts = []

    def stream(messages):
        context = "\n".join(m.content for m in messages)
        contexts.append(context)
        if len(contexts) == 1:
            yield AIMessageChunk(content=json.dumps({"question": completed}))
        elif "【Schema】" in context:
            yield AIMessageChunk(
                content=json.dumps(
                    {
                        "success": True,
                        "sql": "SELECT id FROM vector_beta",
                        "tables": ["vector_beta"],
                    }
                )
            )
        else:
            assert completed in context
            assert "accessible" in context
            assert "second_candidate" not in context
            assert "foreign_workspace" not in context
            yield AIMessageChunk(content=json.dumps({"id": ds_id}))

    current.llm = SimpleNamespace(stream=stream)
    contracts.run(current)
    assert calls[0] == completed
    assert len(contexts) == 3
    assert "and last year?" in contexts[-1]
    assert current.chat_question.question == "and last year?"
    with Session(database) as session:
        assert session.get(Chat, current.chat_question.chat_id).datasource == ds_id
        assert (
            session.get(ChatRecord, current.record.id).sql
            == "SELECT id FROM vector_beta"
        )


def test_overlong_completion_keeps_all_workspace_candidates(
    table_environment, monkeypatch, caplog
):
    database, client, ds_id = table_environment
    contracts.add_datasource_candidates(database)
    contracts.configure(
        client, datasource_count=1, table_count=3, keyword_enabled=False, enabled=False
    )
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: embedding_model(limit=5, calls=calls)
    )
    current = contracts.task(database, None, question="short")
    completed = "a a a a"
    contexts = []

    def stream(messages):
        context = "\n".join(m.content for m in messages)
        contexts.append(context)
        if len(contexts) == 1:
            result = {"question": completed}
        elif "【Schema】" in context:
            result = {
                "success": True,
                "sql": "SELECT id FROM vector_beta",
                "tables": ["vector_beta"],
            }
        else:
            assert completed in context
            assert "accessible" in context and "second_candidate" in context
            assert "foreign_workspace" not in context
            result = {"id": ds_id}
        yield AIMessageChunk(content=json.dumps(result))

    current.llm = SimpleNamespace(stream=stream)
    contracts.run(current)
    assert completed not in calls
    assert '"stage": "datasource"' in caplog.text
    assert '"reason": "query_too_long"' in caplog.text


@pytest.mark.parametrize("scope", ["workspace", "assistant"])
def test_model_cannot_select_source_outside_allowed_candidates(
    table_environment, scope
):
    from apps.chat.models.chat_model import ChatFinishStep
    from apps.datasource.models.datasource import CoreDatasource

    database, client, ds_id = table_environment
    contracts.add_datasource_candidates(database)
    contracts.configure(
        client, table_enabled=False, keyword_enabled=False, enabled=False
    )
    assistant = None
    with Session(database) as session:
        denied = session.query(CoreDatasource).filter(CoreDatasource.oid == 2).one().id
        if scope == "assistant":
            denied = (
                session.query(CoreDatasource)
                .filter(CoreDatasource.name == "second_candidate")
                .one()
                .id
            )
            extra = CoreDatasource(
                name="also_public", description="test", type="pg", oid=1
            )
            session.add(extra)
            session.commit()
            assistant = SimpleNamespace(
                type=0,
                id=99,
                oid=1,
                online=False,
                configuration=json.dumps({"oid": 1, "public_list": [ds_id, extra.id]}),
            )
    current = contracts.task(database, None, assistant=assistant)
    contexts = []

    def stream(messages):
        context = "\n".join(m.content for m in messages)
        contexts.append(context)
        result = {"question": "sales"} if len(contexts) == 1 else {"id": denied}
        yield AIMessageChunk(content=json.dumps(result))

    current.llm = SimpleNamespace(stream=stream)
    result = list(
        current.run_task(
            in_chat=False, stream=False, finish_step=ChatFinishStep.GENERATE_SQL
        )
    )
    assert result[-1]["success"] is False
    assert len(contexts) == 2
    assert "foreign_workspace" not in contexts[1]
    if scope == "assistant":
        assert "second_candidate" not in contexts[1]
        assert "also_public" in contexts[1]
    with Session(database) as session:
        assert session.get(Chat, current.chat_question.chat_id).datasource is None
        assert session.get(ChatRecord, current.record.id).sql is None


class EntryProvider:
    def __init__(self, ds_id, *, sink=None):
        self.ds_id = ds_id
        self.calls = []
        self.sink = sink

    def stream(self, messages):
        context = "\n".join(str(m.content) for m in messages)
        if is_completion_request(messages):
            stage = "completion"
            result = {"question": "sales totals last year excluding refunds"}
        elif "SELECT id FROM vector_beta" in " ".join(
            str(messages[-1].content).split()
        ):
            stage = "chart"
            result = {"type": "table", "columns": [{"name": "id", "value": "id"}]}
        elif "【Schema】" in context:
            stage = "sql"
            result = {
                "success": True,
                "sql": "SELECT id FROM vector_beta",
                "tables": ["vector_beta"],
            }
        else:
            stage = "datasource"
            result = {"id": self.ds_id}
        event = {"stage": stage, "context": context}
        self.calls.append(event)
        if self.sink:
            self.sink(event)
        yield AIMessageChunk(
            content=json.dumps(result),
            usage_metadata={
                "input_tokens": 20,
                "output_tokens": 10,
                "total_tokens": 30,
            },
        )


def serve_controlled_process(app_name, port):
    """Only model/infrastructure boundaries substituted; source SQL executes on PG."""
    import os
    from pathlib import Path

    import uvicorn
    from sqlalchemy import text
    from sqlmodel import create_engine

    from apps.ai_model.model_factory import BaseLLM, LLMFactory
    from apps.chat.task import llm

    def record(event):
        with Path(os.environ["SQLBOT_TEST_CONTEXTS"]).open("a") as output:
            output.write(json.dumps(event) + "\n")

    class Provider(BaseLLM):
        def _init_llm(self):
            return self

        def stream(self, messages):
            return EntryProvider(
                int(os.environ["SQLBOT_TEST_DS_ID"]), sink=record
            ).stream(messages)

    def encode(query):
        record({"stage": "embedding", "context": query})
        return [1.0, 0.0] if "sales" in query else [0.0, 1.0]

    model = embedding_model(limit=512)
    model.embed_query = encode
    EmbeddingModelCache.get_model = staticmethod(lambda: model)
    LLMFactory.register_llm("openai", Provider)
    llm.get_version = lambda _ds: ""
    llm.check_connection = lambda **_kw: True
    database = create_engine(os.environ["SQLBOT_DB_URL"])

    def execute(*, ds, sql, **_kw):
        assert ds.id == int(os.environ["SQLBOT_TEST_DS_ID"])
        with database.connect() as connection:
            result = connection.execute(text(sql))
            return {
                "fields": list(result.keys()),
                "data": [dict(row) for row in result.mappings()],
            }

    llm.exec_sql = execute
    uvicorn.run(
        "main:" + app_name,
        host="127.0.0.1",
        port=port,
        lifespan="off" if app_name == "app" else "on",
        log_level="warning",
    )


def test_mcp_without_datasource_selects_once_and_followup_reuses_source(
    table_environment, tmp_path, caplog
):
    import asyncio
    import logging
    import os
    import secrets
    from pathlib import Path

    import httpx
    from mcp import ClientSession
    from mcp.client.sse import sse_client
    from sqlalchemy import text
    from test_mcp_parameters_integration import server

    from apps.system.models.system_model import AiModelDetail, UserWsModel
    from apps.system.models.user import UserModel
    from common.core.security import md5pwd

    caplog.set_level(logging.WARNING, logger="mcp.client.sse")
    database, client, ds_id = table_environment
    contracts.add_datasource_candidates(database)
    contracts.configure(
        client, datasource_count=1, table_count=3, keyword_enabled=False, enabled=False
    )
    for model in (UserModel, UserWsModel, AiModelDetail):
        model.__table__.create(database)
    password = secrets.token_urlsafe(24)
    with Session(database) as session:
        schema = session.execute(text("SELECT current_schema()")).scalar_one()
        session.add(
            UserModel(
                id=1,
                account="admin",
                name="MCP test",
                oid=1,
                email="mcp@example.invalid",
                password=md5pwd(password),
                status=1,
            )
        )
        session.add(UserWsModel(uid=1, oid=1, weight=1))
        session.add(
            AiModelDetail(
                supplier=1,
                name="controlled",
                model_type=1,
                base_model="controlled",
                default_model=True,
                api_domain="http://127.0.0.1:9/v1",
                api_key="unused",
                config="[]",
            )
        )
        session.execute(text("CREATE TABLE vector_beta (id INTEGER)"))
        session.execute(text("INSERT INTO vector_beta VALUES (7)"))
        session.commit()
    for name in ("logs", "images", "scripts", "files", "excel", "models"):
        (tmp_path / name).mkdir()
    env = {
        **os.environ,
        "SQLBOT_DB_URL": database.url.update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        ).render_as_string(hide_password=False),
        "PYTHONPATH": os.pathsep.join(
            [str(Path(__file__).parent), str(Path(__file__).parents[1])]
        ),
        "SECRET_KEY": secrets.token_urlsafe(48),
        "CACHE_TYPE": "None",
        "CONTEXT_PATH": "",
        "BASE_DIR": str(tmp_path),
        "LOG_DIR": str(tmp_path / "logs"),
        "MCP_IMAGE_PATH": str(tmp_path / "images"),
        "SCRIPT_DIR": str(tmp_path / "scripts"),
        "UPLOAD_DIR": str(tmp_path / "files"),
        "EXCEL_PATH": str(tmp_path / "excel"),
        "LOCAL_MODEL_PATH": str(tmp_path / "models"),
        "LOG_FORMAT": "%(levelname)s %(message)s",
        "LOG_LEVEL": "WARNING",
        "SQLBOT_TEST_CONTEXTS": str(tmp_path / "contexts.jsonl"),
        "SQLBOT_TEST_DS_ID": str(ds_id),
        "EMBEDDING_ENABLED": "false",
        "TABLE_EMBEDDING_ENABLED": "true",
        "TABLE_EMBEDDING_KEYWORD_ENABLED": "false",
        "SAMPLE_DATA_ENABLED": "false",
    }
    with (
        server("app", env, tmp_path, provider_module=__name__) as api,
        server("mcp_app", env, tmp_path, provider_module=__name__) as mcp_url,
    ):
        with httpx.Client(base_url=api, timeout=15) as client:
            response = client.post(
                "/api/v1/mcp/access_token",
                json={"username": "admin", "password": password},
            )
            assert response.status_code == 200, response.text
            token = response.json()["data"]["access_token"]

        async def ask():
            async with sse_client(
                mcp_url + "/mcp", timeout=15, sse_read_timeout=30
            ) as streams:
                async with ClientSession(*streams) as session:
                    await session.initialize()
                    started = await session.call_tool("mcp_start", {"token": token})
                    assert not started.isError, started
                    chat_id = json.loads(started.content[0].text)["data"]["chat_id"]
                    for question in ("sales totals", "last year instead"):
                        result = await session.call_tool(
                            "mcp_question",
                            {
                                "token": token,
                                "chat_id": chat_id,
                                "question": question,
                                "stream": False,
                                "return_img": False,
                                "lang": "en",
                            },
                        )
                        assert not result.isError, result
                        answer = json.loads(result.content[0].text)
                        assert answer["success"], answer
                        assert answer["sql"] == "SELECT id FROM vector_beta"
                        assert answer["data"]["data"] == [{"id": 7}]
                    return chat_id

        chat_id = asyncio.run(ask())
    calls = [
        json.loads(line)
        for line in (tmp_path / "contexts.jsonl").read_text().splitlines()
    ]
    selections = [call["context"] for call in calls if call["stage"] == "datasource"]
    assert len(selections) == 1
    assert "sales totals last year excluding refunds" in selections[0]
    assert "accessible" in selections[0]
    assert (
        "second_candidate" not in selections[0]
        and "foreign_workspace" not in selections[0]
    )
    assert len([call for call in calls if call["stage"] == "completion"]) == 2
    assert (
        next(call["context"] for call in calls if call["stage"] == "embedding")
        == "sales totals last year excluding refunds"
    )
    with Session(database) as session:
        assert session.get(Chat, chat_id).datasource == ds_id
        records = session.query(ChatRecord).filter(ChatRecord.chat_id == chat_id).all()
        assert len(records) == 2
        assert all(
            json.loads(record.data)["datasource"] == ds_id
            and record.finish
            and not record.error
            for record in records
        )


def test_assistant_auto_ds_entry_selects_once_and_followup_reuses_source(
    table_environment, monkeypatch
):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy import text

    from apps.ai_model.model_factory import LLMFactory
    from apps.chat.api.chat import router
    from apps.system.models.system_model import AiModelDetail
    from apps.system.schemas.permission import RequestContextMiddleware
    from common.audit.schemas.request_context import RequestContextMiddlewareCommon
    from common.core.db import get_session

    database, parameters, ds_id = table_environment
    contracts.add_datasource_candidates(database)
    contracts.configure(
        parameters,
        datasource_count=1,
        table_count=3,
        keyword_enabled=False,
        enabled=False,
    )
    AiModelDetail.__table__.create(database)
    from apps.datasource.models.datasource import CoreDatasource

    with Session(database) as session:
        other_id = (
            session.query(CoreDatasource)
            .filter(CoreDatasource.name == "second_candidate")
            .one()
            .id
        )
        session.add(
            AiModelDetail(
                supplier=1,
                name="controlled",
                model_type=1,
                base_model="controlled",
                default_model=True,
                api_domain="http://127.0.0.1:9/v1",
                api_key="unused",
                config="[]",
            )
        )
        session.execute(text("CREATE TABLE vector_beta (id INTEGER)"))
        session.execute(text("INSERT INTO vector_beta VALUES (7)"))
        session.commit()
    provider = EntryProvider(ds_id)
    monkeypatch.setattr(
        LLMFactory, "create_llm", lambda _config: SimpleNamespace(llm=provider)
    )
    monkeypatch.setattr("apps.ai_model.model_factory.engine", database)
    monkeypatch.setattr("apps.system.schemas.permission.engine", database)

    def execute(*, ds, sql, **_kwargs):
        assert ds.id == ds_id
        with database.connect() as connection:
            result = connection.execute(text(sql))
            return {
                "fields": list(result.keys()),
                "data": [dict(row) for row in result.mappings()],
            }

    monkeypatch.setattr("apps.chat.task.llm.exec_sql", execute)
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestContextMiddlewareCommon)

    @app.middleware("http")
    async def identity(request, call_next):
        request.state.current_user = SimpleNamespace(
            id=1,
            oid=1,
            language="en",
            isAdmin=True,
            weight=1,
            account="test",
            username="test",
            name="test",
        )
        request.state.assistant = SimpleNamespace(
            type=0,
            id=99,
            oid=1,
            online=False,
            model_id=None,
            enable_custom_model=False,
            configuration=json.dumps(
                {"oid": 1, "auto_ds": True, "public_list": [ds_id, other_id]}
            ),
        )
        return await call_next(request)

    def sessions():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/chat/assistant/start", json={"origin": 2})
        assert response.status_code == 200, response.text
        chat_id = response.json()["id"]
        for question in ("sales totals", "last year instead"):
            response = client.post(
                "/chat/question", json={"chat_id": chat_id, "question": question}
            )
            assert response.status_code == 200, response.text
            events = [
                json.loads(line[5:])
                for line in response.text.splitlines()
                if line.startswith("data:")
            ]
            assert not [event for event in events if event.get("type") == "error"], (
                events
            )
    selections = [
        call["context"] for call in provider.calls if call["stage"] == "datasource"
    ]
    assert len(selections) == 1
    assert "sales totals last year excluding refunds" in selections[0]
    assert (
        "second_candidate" not in selections[0]
        and "foreign_workspace" not in selections[0]
    )
    assert len([call for call in provider.calls if call["stage"] == "completion"]) == 2
    with Session(database) as session:
        assert session.get(Chat, chat_id).datasource == ds_id
        records = session.query(ChatRecord).filter(ChatRecord.chat_id == chat_id).all()
        assert [record.question for record in records] == [
            "sales totals",
            "last year instead",
        ]
        assert all(
            json.loads(record.data)["datasource"] == ds_id
            and record.finish
            and not record.error
            and json.loads(record.data)["data"] == [{"id": 7}]
            for record in records
        )


@pytest.mark.parametrize("original,limit", [("sales original", 512), ("a a a a", 5)])
def test_failed_completion_uses_original_for_source_selection(
    table_environment, monkeypatch, caplog, original, limit
):
    database, client, ds_id = table_environment
    contracts.add_datasource_candidates(database)
    contracts.configure(
        client, datasource_count=1, table_count=3, keyword_enabled=False, enabled=False
    )
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: embedding_model(limit=limit, calls=calls),
    )
    current = contracts.task(database, None, question=original)
    provider = EntryProvider(ds_id)

    def stream(messages):
        if is_completion_request(messages):
            raise RuntimeError("controlled completion failure")
        if limit == 5 and "【Schema】" not in "\n".join(m.content for m in messages):
            assert calls == []
        yield from provider.stream(messages)

    current.llm = SimpleNamespace(stream=stream)
    contracts.run(current)
    if limit == 5:
        assert "second_candidate" in provider.calls[0]["context"]
        assert '"reason": "query_too_long"' in caplog.text
    else:
        assert calls[0] == original
        assert "second_candidate" not in provider.calls[0]["context"]
    assert "foreign_workspace" not in provider.calls[0]["context"]
    assert original in provider.calls[0]["context"]
    assert '"reason": "model_error"' in caplog.text


def test_single_and_no_candidate_do_not_call_datasource_model_or_vectors(
    table_environment, monkeypatch
):
    from apps.chat.models.chat_model import ChatFinishStep

    database, client, ds_id = table_environment
    contracts.configure(
        client, enabled=False, table_enabled=False, keyword_enabled=False
    )
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: (_ for _ in ()).throw(AssertionError("unexpected embedding")),
    )
    current = contracts.task(database, None)
    provider = EntryProvider(ds_id)
    current.llm = provider
    contracts.run(current)
    assert [call["stage"] for call in provider.calls] == ["completion", "sql"]
    assistant = SimpleNamespace(
        type=0,
        id=99,
        oid=1,
        online=False,
        configuration=json.dumps({"oid": 1, "public_list": []}),
    )
    denied = contracts.task(database, None, assistant=assistant)
    provider = EntryProvider(ds_id)
    denied.llm = provider
    result = list(
        denied.run_task(
            in_chat=False, stream=False, finish_step=ChatFinishStep.GENERATE_SQL
        )
    )
    assert result[-1]["success"] is False
    assert [call["stage"] for call in provider.calls] == ["completion"]
