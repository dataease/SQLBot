"""Offline policy/API regressions with SQLite and a loopback OpenAI endpoint.

Real routers, permission decorators, SQLModel queries, model selection, config
loading and provider calls are exercised. Identity, audit DB, unrelated chat
construction and chat parameters are isolated; no external LLM is contacted.
"""

import asyncio
import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest
import sqlbot_xpack  # noqa: F401 -- initialize the released wheel before app routers
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine, select

from apps.ai_model.model_factory import LLMFactory, get_default_config
from apps.chat.api import chat as chat_api
from apps.chat.models.chat_model import Chat, ChatQuestion, ChatRecord
from apps.chat.task import llm
from apps.mcp import mcp
from apps.system.api import aimodel, workspace
from apps.system.crud.workspace_model import resolve_model_id
from apps.system.models.system_model import (
    AiModelDetail,
    AiModelWorkspaceMapping,
    AssistantModel,
    WorkspaceModel,
)
from apps.system.schemas.permission import RequestContextMiddleware
from common.audit.models.log_model import SystemLog, SystemLogsResource
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.db import get_session
from common.error import SingleMessageError
from common.utils.locale import I18n

TRANS = I18n()(lang="en")


@pytest.fixture
def environment(monkeypatch):
    calls = []

    class Provider(BaseHTTPRequestHandler):
        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            calls.append(body["model"])
            data = json.dumps(
                {
                    "id": "local-test",
                    "object": "chat.completion",
                    "created": 1,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {"role": "assistant", "content": "ok"},
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "total_tokens": 2,
                    },
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Provider)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    database = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    for model in (
        AiModelDetail,
        AiModelWorkspaceMapping,
        WorkspaceModel,
        AssistantModel,
        Chat,
        ChatRecord,
    ):
        model.__table__.create(database)
    # Migration 055 allows nullable audit fields; its SQLModel annotations are
    # stricter. Match the production migration without changing global metadata.
    metadata = MetaData()
    for model in (SystemLog, SystemLogsResource):
        table = model.__table__.to_metadata(metadata)
        for column in table.columns:
            if not column.primary_key:
                column.nullable = True
        table.create(database)
    with Session(database) as session:
        session.add_all(
            [WorkspaceModel(id=1, name="A"), WorkspaceModel(id=2, name="B")]
        )
        for model_id in (10, 20, 30):
            session.add(
                AiModelDetail(
                    id=model_id,
                    name=f"model-{model_id}",
                    supplier=15,
                    model_type=0,
                    base_model=f"base-{model_id}",
                    default_model=model_id == 10,
                    api_domain=f"http://127.0.0.1:{server.server_port}/v1",
                    api_key="local-test",
                    config="[]",
                )
            )
        session.add_all(
            [
                AiModelWorkspaceMapping(ai_model_id=20, workspace_id=1),
                AiModelWorkspaceMapping(ai_model_id=30, workspace_id=1),
            ]
        )
        session.add_all(
            [
                Chat(id=101, oid=1, create_by=1, engine_type="PostgreSQL"),
                Chat(id=102, oid=2, create_by=1, engine_type="PostgreSQL"),
            ]
        )
        session.commit()
    monkeypatch.setattr("apps.ai_model.model_factory.engine", database)
    monkeypatch.setattr("common.audit.schemas.logger_decorator.engine", database)
    # The audit name union includes unrelated xpack tables; only resource-name
    # lookup is isolated. The decorator and log persistence remain real.
    monkeypatch.setattr(
        "common.audit.schemas.logger_decorator.get_resource_name_by_id_and_module",
        lambda *_args: [],
    )
    monkeypatch.setattr("apps.system.api.workspace.clean_user_cache", _empty_async)
    monkeypatch.setattr(llm, "get_groups", _empty_async)

    def construct(self, _session, user, question, _assistant, *_args, **kwargs):
        self.config = kwargs["config"]
        self.current_user = user
        self.chat_question = question
        self.llm = LLMFactory.create_llm(self.config).llm

    monkeypatch.setattr(llm.LLMService, "__init__", construct)
    monkeypatch.setattr("apps.system.schemas.permission.engine", database)
    monkeypatch.setattr(llm.LLMService, "init_record", lambda *_args, **_kwargs: None)

    def run(self, **kwargs):
        self.test_stream = kwargs.get("stream", True)
        assert self.llm.invoke("hello").content == "ok"

    def result(self):
        data = {"success": True, "model_id": self.config.model_id}
        yield "data:" + json.dumps(data) + "\n\n" if self.test_stream else data

    monkeypatch.setattr(llm.LLMService, "run_task_async", run)
    monkeypatch.setattr(llm.LLMService, "await_result", result)
    monkeypatch.setattr(llm.LLMService, "run_recommend_questions_task_async", run)
    monkeypatch.setattr(
        llm.LLMService,
        "run_analysis_or_predict_task_async",
        lambda self, _session, _action, _record, _in_chat, stream: run(
            self, stream=stream
        ),
    )
    monkeypatch.setattr(
        mcp, "get_user", lambda *_args: SimpleNamespace(id=1, oid=2, language="en")
    )

    async def workspaces(*_args):
        return [SimpleNamespace(id=1), SimpleNamespace(id=2)]

    monkeypatch.setattr(mcp, "user_ws_options", workspaces)
    app = FastAPI()
    app.include_router(workspace.router)
    app.include_router(aimodel.router)
    app.include_router(chat_api.router)
    app.include_router(mcp.router)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestContextMiddlewareCommon)

    @app.middleware("http")
    async def identity(request, call_next):
        role = request.headers.get("test-role", "admin")
        request.state.assistant = None
        if role != "anonymous":
            request.state.current_user = SimpleNamespace(
                id=1,
                oid=1,
                name="test",
                language="en",
                isAdmin=role == "admin",
                weight=1 if role == "workspace-admin" else 0,
            )
        return await call_next(request)

    @app.exception_handler(Exception)
    async def error_response(_request, exc):
        return JSONResponse(status_code=400, content={"error": str(exc)})

    def session_dependency():
        with Session(database) as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise

    app.dependency_overrides[get_session] = session_dependency
    with TestClient(app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(database=database, client=client, calls=calls)
    database.dispose()
    server.shutdown()
    server.server_close()
    thread.join()


async def _empty_async(*_args, **_kwargs):
    return []


def save(env, enabled, model_id, workspace_id=1):
    return env.client.put(
        f"/system/workspace/{workspace_id}/model",
        json={"enable_custom_model": enabled, "custom_model": model_id},
    )


def call(env, custom_model=None, assistant=None, chat_id=101):
    with Session(env.database) as session:
        service = asyncio.run(
            llm.LLMService.create(
                session,
                SimpleNamespace(id=1, oid=2, language="en"),
                ChatQuestion(
                    chat_id=chat_id, question="hello", custom_model=custom_model
                ),
                assistant,
            )
        )
        assert service.llm.invoke("hello").content == "ok"
        return service.config.model_id


def test_default_compatibility_and_workspace_isolation(environment):
    env = environment
    assert call(env) == 10  # not authorized to workspace A
    assert save(env, True, "20").status_code == 200
    assert call(env) == 20
    assert call(env, chat_id=102) == 10
    assert env.calls == ["base-10", "base-20", "base-10"]
    assert save(env, False, None).status_code == 200
    assert call(env) == 10


@pytest.mark.parametrize(
    "kind", ["page", "assistant-default", "assistant-custom", "mcp"]
)
def test_explicit_empty_workspace_disables_every_entry(environment, kind):
    env = environment
    assert save(env, True, None).status_code == 200
    assistant = (
        SimpleNamespace(
            enable_custom_model=kind == "assistant-custom", custom_model="20"
        )
        if kind.startswith("assistant")
        else None
    )
    with pytest.raises(SingleMessageError, match="disabled"):
        call(env, custom_model="30" if kind == "mcp" else None, assistant=assistant)
    assert env.calls == []


def test_assistant_inherits_without_rewriting_custom_settings(environment):
    env = environment
    default = SimpleNamespace(enable_custom_model=False, custom_model=None)
    explicit = SimpleNamespace(enable_custom_model=True, custom_model="30")
    assert save(env, True, "20").status_code == 200
    assert call(env, assistant=default) == 20
    assert call(env, assistant=explicit) == 30
    assert save(env, False, None).status_code == 200
    assert call(env, assistant=default) == 10
    assert explicit.custom_model == "30"


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("model_id", ["10", "999", "-1", "bad", 999])
def test_explicit_unauthorized_or_missing_models_never_fallback(
    environment, enabled, model_id
):
    env = environment
    assert save(env, enabled, "20" if enabled else None).status_code == 200
    for assistant in (
        None,
        SimpleNamespace(enable_custom_model=True, custom_model=model_id),
    ):
        with pytest.raises(SingleMessageError, match="not authorized"):
            call(
                env,
                custom_model=model_id if assistant is None else None,
                assistant=assistant,
            )
    assert env.calls == []


def test_invalid_default_preserves_reference_and_allows_valid_explicit_override(
    environment,
):
    env = environment
    assert save(env, True, "20").status_code == 200
    with Session(env.database) as session:
        session.delete(session.get(AiModelDetail, 20))
        session.commit()
    with pytest.raises(SingleMessageError):
        call(env)
    assert call(env, custom_model="30") == 30
    assert (
        call(
            env, assistant=SimpleNamespace(enable_custom_model=True, custom_model="30")
        )
        == 30
    )
    assert env.client.get("/system/workspace/1/model").json()["custom_model"] == "20"
    with pytest.raises(SingleMessageError):
        asyncio.run(get_default_config(20, trans=TRANS))
    assert env.calls == ["base-30", "base-30"]


@pytest.mark.parametrize("role", ["workspace-admin", "user", "anonymous"])
def test_only_system_admin_can_read_or_change_settings_or_impacts(environment, role):
    env = environment
    headers = {"test-role": role}
    assert (
        env.client.get("/system/workspace/1/model", headers=headers).status_code >= 400
    )
    assert (
        env.client.put(
            "/system/workspace/1/model",
            json={"enable_custom_model": True, "custom_model": None},
            headers=headers,
        ).status_code
        >= 400
    )
    assert (
        env.client.post(
            "/system/aimodel/20/workspace_impact", json=None, headers=headers
        ).status_code
        >= 400
    )
    assert (
        env.client.get("/system/workspace/1/model").json()["enable_custom_model"]
        is False
    )


def test_settings_validate_authorization_preserve_rename_and_audit(environment):
    env = environment
    assert save(env, True, "10").status_code >= 400
    assert save(env, True, "20").status_code == 200
    assert (
        env.client.put(
            "/system/workspace", json={"id": 1, "name": "renamed"}
        ).status_code
        == 200
    )
    result = env.client.get("/system/workspace/1/model").json()
    assert result["custom_model"] == "20"
    assert [item["id"] for item in result["models"]] == ["20", "30"]
    with Session(env.database) as session:
        logs = session.exec(select(SystemLog).where(SystemLog.resource_id == "1")).all()
        audit = next(json.loads(item.remark) for item in logs if item.remark)
        assert audit == {
            "before": {"enable_custom_model": False, "custom_model": None},
            "after": {"enable_custom_model": True, "custom_model": "20"},
        }


def test_precheck_uses_workspace_model_without_system_default(environment):
    env = environment
    assert save(env, True, "20").status_code == 200
    with Session(env.database) as session:
        session.delete(session.get(AiModelDetail, 10))
        session.commit()
    assert env.client.get("/system/aimodel/default").status_code == 200
    assert call(env) == 20
    assert save(env, True, None).status_code == 200
    assert env.client.get("/system/aimodel/default").status_code >= 400


@pytest.mark.parametrize("operation", ["delete", "remove", "replace-mapping"])
def test_impact_confirmation_replacement_and_atomic_rejection(environment, operation):
    env = environment
    assert save(env, True, "20").status_code == 200
    preview = env.client.post("/system/aimodel/20/workspace_impact", json=["1"])
    assert preview.status_code == 200
    assert preview.json()[0]["workspace_id"] == "1"
    assert [item["id"] for item in preview.json()[0]["models"]] == ["30"]

    def mutate(resolutions):
        if operation == "delete":
            return env.client.request("DELETE", "/system/aimodel/20", json=resolutions)
        return env.client.request(
            "PUT" if operation == "replace-mapping" else "DELETE",
            "/system/aimodel/20/ws_mapping",
            json={
                "ws_ids": [] if operation == "replace-mapping" else ["1"],
                "resolutions": resolutions,
            },
        )

    assert mutate([]).status_code >= 400
    assert mutate([{"workspace_id": "1", "custom_model": "10"}]).status_code >= 400
    with Session(env.database) as session:
        assert session.get(WorkspaceModel, 1).custom_model == "20"
        assert session.get(AiModelDetail, 20) is not None
        assert (
            session.exec(
                select(AiModelWorkspaceMapping).where(
                    AiModelWorkspaceMapping.ai_model_id == 20
                )
            ).first()
            is not None
        )
    assert mutate([{"workspace_id": "1", "custom_model": "30"}]).status_code == 200
    assert call(env) == 30


def test_confirmed_revoke_retains_id_and_refuses_stale_preview(environment):
    env = environment
    assert save(env, True, "20").status_code == 200
    assert save(env, True, "20", workspace_id=2).status_code >= 400
    response = env.client.request(
        "DELETE",
        "/system/aimodel/20/ws_mapping",
        json={
            "ws_ids": ["1"],
            "resolutions": [{"workspace_id": "1", "custom_model": None}],
        },
    )
    assert response.status_code == 200
    result = env.client.get("/system/workspace/1/model").json()
    assert result["custom_model"] == "20" and result["model_valid"] is False
    with pytest.raises(SingleMessageError):
        call(env)
    assert call(env, custom_model="30") == 30
    # Old clients cannot bypass the impact check by sending the legacy array.
    assert (
        env.client.put("/system/aimodel/30/ws_mapping", json=["1"]).status_code == 200
    )


def test_new_requests_see_changes_but_started_operation_keeps_its_model(environment):
    env = environment
    assert save(env, True, "20").status_code == 200
    with Session(env.database) as session:
        service = asyncio.run(
            llm.LLMService.create(
                session,
                SimpleNamespace(id=1, oid=1, language="en"),
                ChatQuestion(chat_id=101, question="hello"),
                None,
            )
        )
    assert save(env, True, None).status_code == 200
    assert service.llm.invoke("hello").content == "ok"
    assert env.calls == ["base-20"]
    with pytest.raises(SingleMessageError):
        call(env)


def test_model_list_and_resolution_use_same_explicit_authorization(environment):
    env = environment
    with Session(env.database) as session:
        assert resolve_model_id(session, 1, TRANS) == 10
        with pytest.raises(SingleMessageError):
            resolve_model_id(session, 1, TRANS, custom_model=10)
        session.add(AiModelWorkspaceMapping(ai_model_id=10, workspace_id=1))
        session.commit()
        assert resolve_model_id(session, 1, TRANS, custom_model=10) == 10


def test_migration_preserves_old_rows_and_server_defaults_and_can_downgrade():
    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic/versions/073_workspace_model_settings.py"
    )
    spec = importlib.util.spec_from_file_location(
        "workspace_model_migration", migration_path
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    database = create_engine("sqlite://")
    with database.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE sys_workspace (id BIGINT PRIMARY KEY, name VARCHAR(255))"
            )
        )
        connection.execute(
            text("INSERT INTO sys_workspace (id, name) VALUES (1, 'existing')")
        )
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        connection.execute(
            text("INSERT INTO sys_workspace (id, name) VALUES (2, 'new')")
        )
        assert connection.execute(
            text(
                "SELECT enable_custom_model, custom_model FROM sys_workspace ORDER BY id"
            )
        ).all() == [(0, None), (0, None)]
        migration.downgrade()
        assert [
            item["name"] for item in inspect(connection).get_columns("sys_workspace")
        ] == ["id", "name"]
        assert (
            connection.execute(text("SELECT COUNT(*) FROM sys_workspace")).scalar() == 2
        )
    database.dispose()


def test_batch_revoke_requires_fresh_complete_confirmation(environment):
    env = environment
    assert save(env, True, "20").status_code == 200
    # A second workspace starts using this default after the first preview.
    assert (
        env.client.post("/system/aimodel/20/ws_mapping", json=["2"]).status_code == 200
    )
    assert save(env, True, "20", workspace_id=2).status_code == 200
    request = {
        "ws_ids": ["1", "2"],
        "resolutions": [{"workspace_id": "1", "custom_model": "30"}],
    }
    assert (
        env.client.request(
            "DELETE", "/system/aimodel/20/ws_mapping", json=request
        ).status_code
        >= 400
    )
    request["resolutions"].append({"workspace_id": "2", "custom_model": "30"})
    # Replacement 30 is not authorized to B: all workspaces/mappings stay intact.
    assert (
        env.client.request(
            "DELETE", "/system/aimodel/20/ws_mapping", json=request
        ).status_code
        >= 400
    )
    with Session(env.database) as session:
        assert session.get(WorkspaceModel, 1).custom_model == "20"
        assert session.get(WorkspaceModel, 2).custom_model == "20"
        assert (
            len(
                session.exec(
                    select(AiModelWorkspaceMapping).where(
                        AiModelWorkspaceMapping.ai_model_id == 20
                    )
                ).all()
            )
            == 2
        )


def test_page_and_mcp_http_routes_use_policy_and_reject_without_provider_requests(
    environment,
):
    env = environment
    assert save(env, True, "20").status_code == 200
    response = env.client.post(
        "/chat/question", json={"chat_id": 101, "question": "hello"}
    )
    assert response.status_code == 200 and '"model_id": 20' in response.text
    payload = {
        "token": "test-identity",
        "chat_id": 101,
        "question": "hello",
        "stream": False,
        "lang": "en",
        "custom_model": "30",
    }
    response = env.client.post("/mcp/mcp_question", json=payload)
    assert response.status_code == 200 and response.json()["model_id"] == 30
    payload["custom_model"] = "10"
    response = env.client.post("/mcp/mcp_question", json=payload)
    assert (
        response.status_code == 500 and "not authorized" in response.json()["message"]
    )
    assert env.calls == ["base-20", "base-30"]
    assert save(env, True, None).status_code == 200
    payload["custom_model"] = "30"
    response = env.client.post("/mcp/mcp_question", json=payload)
    assert response.status_code == 500 and "disabled" in response.json()["message"]
    response = env.client.post(
        "/chat/question", json={"chat_id": 101, "question": "hello"}
    )
    assert '"type":"error"' in response.text and "disabled" in response.text
    assert env.calls == ["base-20", "base-30"]


@pytest.mark.parametrize("entry", ["analysis", "predict", "recommend", "regenerate"])
def test_followup_http_operations_revalidate_policy(environment, entry):
    env = environment
    with Session(env.database) as session:
        session.add(
            ChatRecord(
                id=201,
                chat_id=101,
                create_by=1,
                question="hello",
                first_chat=False,
                ai_modal_id=10,
                chart="{}",
            )
        )
        session.commit()
    assert save(env, True, "20").status_code == 200

    def request():
        if entry == "recommend":
            return env.client.post("/chat/recommend_questions/201")
        if entry == "regenerate":
            return env.client.post(
                "/mcp/mcp_question",
                json={
                    "token": "test-identity",
                    "chat_id": 101,
                    "question": "/regenerate",
                    "stream": False,
                    "lang": "en",
                    "custom_model": "30",
                },
            )
        return env.client.post(f"/chat/record/201/{entry}")

    response = request()
    assert response.status_code == 200
    assert env.calls == ["base-30" if entry == "regenerate" else "base-20"]
    assert save(env, True, None).status_code == 200
    response = request()
    assert "disabled" in response.text
    assert len(env.calls) == 1
