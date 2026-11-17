"""Opt-in HTTP question/regeneration contracts on disposable PostgreSQL.

Identity middleware and model/source providers are controlled; resource permission,
model policy, route, task orchestration, retrieval and record persistence are real.
"""

import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessageChunk
from sqlalchemy import select
from sqlmodel import Session
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)
from test_table_parameters_integration import table_environment  # noqa: F401

from apps.ai_model.model_factory import LLMFactory
from apps.chat.api.chat import router
from apps.chat.models.chat_model import Chat, ChatRecord
from apps.system.models.system_model import AiModelDetail, WorkspaceModel
from apps.system.schemas.permission import RequestContextMiddleware
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.db import get_session


class RouteProvider:
    def __init__(self):
        self.messages = []

    def stream(self, messages):
        self.messages.append(list(messages))
        content = "\n".join(str(message.content) for message in messages)
        if "SELECT id FROM vector_beta" in " ".join(str(messages[-1].content).split()):
            result = {"type": "table", "columns": [{"name": "id", "value": "id"}]}
        elif "【Schema】" in content:
            result = {
                "success": True,
                "sql": "SELECT id FROM vector_beta",
                "tables": ["vector_beta"],
            }
        else:
            result = {"question": "show vector_beta totals for last year"}
        yield AIMessageChunk(
            content=json.dumps(result),
            usage_metadata={
                "input_tokens": 20,
                "output_tokens": 10,
                "total_tokens": 30,
            },
        )


@pytest.fixture
def question_api(table_environment, monkeypatch):  # noqa: F811
    database, _parameters, ds_id = table_environment
    AiModelDetail.__table__.create(database)
    with Session(database) as session:
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
        session.add(WorkspaceModel(id=2, name="outside"))
        session.commit()
    provider = RouteProvider()
    monkeypatch.setattr(
        LLMFactory, "create_llm", lambda _config: SimpleNamespace(llm=provider)
    )
    monkeypatch.setattr("apps.ai_model.model_factory.engine", database)
    monkeypatch.setattr("apps.system.schemas.permission.engine", database)
    monkeypatch.setattr(
        "apps.chat.task.llm.exec_sql",
        lambda **_kwargs: {"fields": ["id"], "data": [{"id": 7}]},
    )
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestContextMiddlewareCommon)

    @app.middleware("http")
    async def identity(request, call_next):
        request.state.current_user = SimpleNamespace(
            id=1,
            oid=int(request.headers.get("test-workspace", "1")),
            language="en",
            isAdmin=True,
            weight=1,
            account="test",
            username="test",
            name="test",
        )
        return await call_next(request)

    @app.exception_handler(Exception)
    async def error(_request, exc):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    def sessions():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    with TestClient(app, raise_server_exceptions=False) as client:
        yield database, client, ds_id, provider


def ask(client, chat_id, question):
    response = client.post(
        "/chat/question", json={"chat_id": chat_id, "question": question}
    )
    assert response.status_code == 200, response.text
    events = [
        json.loads(line[5:])
        for line in response.text.splitlines()
        if line.startswith("data:")
    ]
    assert not [event for event in events if event.get("type") == "error"], events
    return events


def records(database, chat_id):
    with Session(database) as session:
        return (
            session.execute(
                select(ChatRecord)
                .where(ChatRecord.chat_id == chat_id, ChatRecord.first_chat.is_(False))
                .order_by(ChatRecord.create_time)
            )
            .scalars()
            .all()
        )


def test_http_question_and_regenerate_keep_original_and_complete_each_new_task(
    question_api,
):
    database, client, ds_id, provider = question_api
    response = client.post(
        "/chat/start", json={"datasource": ds_id, "question": "sales"}
    )
    assert response.status_code == 200, response.text
    chat_id = response.json()["id"]
    ask(client, chat_id, "show vector_beta totals for this year")
    ask(client, chat_id, "last year instead")
    original = records(database, chat_id)[-1]
    ask(client, chat_id, f"/regenerate {original.id}")
    result = records(database, chat_id)
    assert [record.question for record in result] == [
        "show vector_beta totals for this year",
        "last year instead",
        "last year instead",
    ]
    assert result[-1].regenerate_record_id == original.id
    assert all(
        record.finish
        and not record.error
        and " ".join(record.sql.split()) == "SELECT id FROM vector_beta"
        for record in result
    )
    assert all(record.data for record in result)
    # Exactly one additional preparation call per question, including regeneration.
    assert len(provider.messages) == 9
    for record in result:
        response = client.get(f"/chat/record/{record.id}/log")
        assert response.status_code == 200, response.text
        history = response.json()
        completion = [
            step for step in history["steps"] if step["operate"] == "COMPLETE_QUESTION"
        ]
        assert len(completion) == 1
        assert completion[0]["total_tokens"] == 30
        assert not completion[0]["error"]
        assert (
            json.loads(completion[0]["message"][1]["content"])["current"]["question"]
            == record.question
        )
        assert history["total_tokens"] == 90
        usage = client.get(f"/chat/record/{record.id}/usage")
        assert usage.status_code == 200, usage.text
        assert usage.json()["total_tokens"] == 90
    sql_messages = [
        messages
        for messages in provider.messages
        if "【Schema】" in "\n".join(str(message.content) for message in messages)
        and "SELECT id FROM vector_beta"
        not in " ".join(str(messages[-1].content).split())
    ]
    assert len(sql_messages) == 3
    assert all(
        "last year instead" in messages[-1].content for messages in sql_messages[1:]
    )
    assert all(
        "show vector_beta totals for last year" not in messages[-1].content
        for messages in sql_messages[1:]
    )


def test_http_cross_workspace_rejection_does_not_prepare_or_persist(question_api):
    database, client, ds_id, provider = question_api
    response = client.post(
        "/chat/start", json={"datasource": ds_id, "question": "sales"}
    )
    assert response.status_code == 200, response.text
    chat_id = response.json()["id"]
    denied = client.post(
        "/chat/question",
        headers={"test-workspace": "2"},
        json={"chat_id": chat_id, "question": "last year instead"},
    )
    assert denied.status_code >= 400
    assert not provider.messages
    assert not records(database, chat_id)
    with Session(database) as session:
        assert session.get(Chat, chat_id).datasource == ds_id


def test_http_workspace_disabled_model_prevents_completion(question_api):
    database, client, ds_id, provider = question_api
    response = client.post(
        "/chat/start", json={"datasource": ds_id, "question": "sales"}
    )
    assert response.status_code == 200, response.text
    chat_id = response.json()["id"]
    with Session(database) as session:
        workspace = session.get(WorkspaceModel, 1)
        workspace.enable_custom_model = True
        workspace.custom_model = None
        session.add(workspace)
        session.commit()
    response = client.post(
        "/chat/question", json={"chat_id": chat_id, "question": "last year instead"}
    )
    assert "error" in response.text
    assert not provider.messages
    assert not records(database, chat_id)
