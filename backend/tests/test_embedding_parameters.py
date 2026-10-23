"""Offline parameter API regressions using the released xpack persistence adapter."""

import json
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlbot_xpack.config.model import SysArgModel
from sqlmodel import Session, create_engine

from apps.system.api.parameter import router
from apps.system.schemas.permission import RequestContextMiddleware
from common.audit.models.log_model import SystemLog, SystemLogsResource
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.config import settings
from common.core.db import get_session


def parameter_app(database, monkeypatch):
    """Use real auth decorators/auditing; only identity and database are test adapters."""
    for model in (SysArgModel, SystemLog, SystemLogsResource):
        model.__table__.create(database, checkfirst=True)
    monkeypatch.setattr("common.audit.schemas.logger_decorator.engine", database)
    app = FastAPI()
    app.include_router(router)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestContextMiddlewareCommon)

    @app.middleware("http")
    async def identity(request, call_next):
        role = request.headers.get("test-role", "admin")
        if role != "anonymous":
            request.state.current_user = SimpleNamespace(
                isAdmin=role == "admin",
                weight=1 if role == "workspace-admin" else 0,
                id=1,
                oid=1,
                username="test",
                account="test",
                name="test",
            )
        return await call_next(request)

    @app.exception_handler(Exception)
    async def error_response(_request, _exc):
        return JSONResponse(status_code=400, content={"error": str(_exc)})

    def session():
        with Session(database) as value:
            yield value

    app.dependency_overrides[get_session] = session
    return app


@pytest.fixture
def parameter_client(monkeypatch):
    database = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    with TestClient(
        parameter_app(database, monkeypatch), raise_server_exceptions=False
    ) as client:
        yield client
    database.dispose()


def values(client):
    response = client.get("/system/parameter")
    assert response.status_code == 200
    return {item["pkey"]: item["pval"] for item in response.json()}


def save(client, items, **kwargs):
    return client.post("/system/parameter", data={"data": json.dumps(items)}, **kwargs)


def test_deployment_defaults_and_saved_knowledge_parameters(
    parameter_client, monkeypatch
):
    monkeypatch.setattr(settings, "EMBEDDING_TERMINOLOGY_SIMILARITY", 0.65)
    assert values(parameter_client)["embedding.terminology_similarity"] == "0.65"
    response = save(
        parameter_client,
        [
            {"pkey": "embedding.terminology_similarity", "pval": 0},
            {"pkey": "embedding.terminology_top_count", "pval": 1},
            {"pkey": "embedding.data_training_similarity", "pval": 1},
            {"pkey": "embedding.data_training_top_count", "pval": 9},
        ],
    )
    assert response.status_code == 200
    result = values(parameter_client)
    assert result["embedding.terminology_similarity"] == "0.0"
    assert result["embedding.terminology_top_count"] == "1"
    assert result["embedding.data_training_similarity"] == "1.0"
    assert result["embedding.data_training_top_count"] == "9"


@pytest.mark.parametrize(
    "key,bad_value",
    [
        ("terminology_similarity", -0.1),
        ("terminology_similarity", 1.1),
        ("data_training_similarity", "nan"),
        ("data_training_similarity", "inf"),
        ("terminology_top_count", True),
        ("terminology_top_count", 0),
        ("data_training_top_count", 1.5),
        ("data_training_top_count", "1.0"),
        ("terminology_similarity", None),
        ("table_count", 0),
        ("table_count", 1.5),
        ("datasource_count", -1),
        ("datasource_count", True),
        ("table_alpha", -0.1),
        ("table_alpha", 1.1),
        ("table_alpha", "nan"),
        ("table_alpha", "inf"),
        ("keyword_enabled", 1),
        ("keyword_enabled", "yes"),
    ],
)
def test_invalid_batch_preserves_all_existing_parameters(
    parameter_client, key, bad_value
):
    assert (
        save(
            parameter_client, [{"pkey": "chat.sqlbot_name", "pval": "existing"}]
        ).status_code
        == 200
    )
    before = values(parameter_client)
    response = save(
        parameter_client,
        [
            {"pkey": "chat.sqlbot_name", "pval": "changed"},
            {"pkey": "embedding.terminology_top_count", "pval": 8},
            {"pkey": f"embedding.{key}", "pval": bad_value},
        ],
    )
    assert response.status_code >= 400
    assert values(parameter_client) == before


@pytest.mark.parametrize("role", ["anonymous", "user", "workspace-admin"])
def test_only_system_admin_can_manage_parameters(parameter_client, role):
    before = values(parameter_client)
    assert (
        parameter_client.get(
            "/system/parameter", headers={"test-role": role}
        ).status_code
        >= 400
    )
    assert (
        save(
            parameter_client,
            [{"pkey": "embedding.terminology_top_count", "pval": 12}],
            headers={"test-role": role},
        ).status_code
        >= 400
    )
    assert values(parameter_client) == before


@pytest.mark.parametrize(
    "payload",
    [
        {"pkey": "embedding.terminology_top_count", "pval": 8},
        [None],
        [42],
        [{"pkey": 1, "pval": 3}],
    ],
)
def test_malformed_batch_is_rejected_without_updates(parameter_client, payload):
    before = values(parameter_client)
    assert save(parameter_client, payload).status_code >= 400
    assert values(parameter_client) == before


@pytest.mark.parametrize("data", [None, "{", "null"])
def test_malformed_form_has_a_localized_validation_error(parameter_client, data):
    before = values(parameter_client)
    response = parameter_client.post(
        "/system/parameter", data={} if data is None else {"data": data}
    )
    assert response.status_code >= 400
    assert response.json()["error"].startswith("Invalid embedding parameter:")
    assert values(parameter_client) == before


def test_table_selection_parameters_preserve_types_and_other_settings(
    parameter_client, monkeypatch
):
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_COUNT", 17)
    assert values(parameter_client)["embedding.table_count"] == "17"
    assert (
        save(
            parameter_client, [{"pkey": "chat.sqlbot_name", "pval": "existing"}]
        ).status_code
        == 200
    )
    for alpha, enabled in [(0, True), (1, "false")]:
        assert (
            save(
                parameter_client,
                [
                    {"pkey": "embedding.table_count", "pval": 1},
                    {"pkey": "embedding.datasource_count", "pval": 3},
                    {"pkey": "embedding.table_alpha", "pval": alpha},
                    {"pkey": "embedding.keyword_enabled", "pval": enabled},
                ],
            ).status_code
            == 200
        )
        result = values(parameter_client)
        assert result["embedding.table_count"] == "1"
        assert result["embedding.datasource_count"] == "3"
        assert result["embedding.table_alpha"] == f"{alpha}.0"
        assert result["embedding.keyword_enabled"] == str(enabled).lower()
        assert result["chat.sqlbot_name"] == "existing"
    entries = parameter_client.get("/system/parameter").json()
    assert (
        next(item for item in entries if item["pkey"] == "embedding.keyword_enabled")[
            "ptype"
        ]
        == "bool"
    )
