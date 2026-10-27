"""Offline HTTP regressions for TAPD 1078034 using real routers and handlers.

Identity, audit persistence and database sessions are test adapters. No application
startup, external database, provider or deployed service is used.
"""

import io
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before API imports.
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.data_training.api import data_training
from apps.settings.api import base
from apps.system.api import user
from apps.system.crud import user_excel
from apps.system.schemas.permission import RequestContextMiddleware
from apps.terminology.api import terminology
from common.audit.schemas.logger_decorator import SystemLogger
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.db import get_session
from common.core.deps import get_i18n
from common.core.response_middleware import ResponseMiddleware, exception_handler

UPLOAD_URLS = [
    "/system/terminology/uploadExcel",
    "/system/data-training/uploadExcel",
    "/user/batchImport",
]


@pytest.fixture
def api(monkeypatch, tmp_path):
    app = FastAPI()
    for module in (terminology, data_training, base, user):
        app.include_router(module.router)
    app.add_exception_handler(
        StarletteHTTPException, exception_handler.http_exception_handler
    )
    app.add_exception_handler(Exception, exception_handler.global_exception_handler)
    app.add_middleware(ResponseMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RequestContextMiddlewareCommon)

    @app.middleware("http")
    async def identity(request, call_next):
        request.state.current_user = SimpleNamespace(
            isAdmin=True, weight=1, id=1, oid=1, account="test", name="test"
        )
        return await call_next(request)

    session = Mock()
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_i18n] = lambda: lambda key: key
    monkeypatch.setattr(SystemLogger, "create_log_record", AsyncMock())
    for module in (terminology, data_training, base):
        monkeypatch.setattr(module, "path", str(tmp_path))
    monkeypatch.setattr(user_excel, "_TEMP_FILE_MAP", {})
    monkeypatch.setattr(user_excel.tempfile, "gettempdir", lambda: str(tmp_path))
    # ResponseMiddleware tracks live instances globally in the application.
    monkeypatch.setattr(ResponseMiddleware, "instances", [])
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, session


def workbook(columns):
    buffer = io.BytesIO()
    pd.DataFrame(columns=columns).to_excel(buffer, index=False)
    return buffer.getvalue()


@pytest.mark.parametrize("url", UPLOAD_URLS)
@pytest.mark.parametrize("filename", ["bad.csv", "bad", "bad.xlsx.csv"])
def test_unsupported_upload_returns_400(api, tmp_path, url, filename):
    client, session = api
    response = client.post(url, files={"file": (filename, b"invalid spreadsheet")})
    assert response.status_code == 400, response.text
    assert response.json() == "Only support .xlsx/.xls"
    assert list(tmp_path.iterdir()) == []
    session.add_all.assert_not_called()
    session.commit.assert_not_called()


def test_invalid_user_excel_headers_return_400(api):
    client, session = api
    response = client.post(
        "/user/batchImport", files={"file": ("users.xlsx", workbook(["wrong"]))}
    )
    assert response.status_code == 400, response.text
    assert response.json() == "Excel header validation failed"
    session.add_all.assert_not_called()
    session.commit.assert_not_called()


def test_valid_empty_user_workbook_is_accepted(api):
    client, session = api
    response = client.post(
        "/user/batchImport",
        files={"file": ("users.xlsx", workbook(user_excel.get_i18n_head_list()))},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "successCount": 0,
        "errorCount": 0,
        "dataKey": None,
    }
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "module,batch_name,column_count",
    [
        (terminology, "batch_create_terminology", 6),
        (data_training, "batch_create_training", 4),
    ],
)
@pytest.mark.parametrize("filename", ["valid.xlsx", "valid.XLSX"])
def test_valid_knowledge_workbook_reaches_batch_import(
    api, monkeypatch, module, batch_name, column_count, filename
):
    client, session = api
    monkeypatch.setattr(module, "session_maker", lambda: session)
    batch = Mock(
        return_value={
            "failed_records": [],
            "success_count": 0,
            "duplicate_count": 0,
            "original_count": 0,
        }
    )
    monkeypatch.setattr(module, batch_name, batch)
    response = client.post(
        module.router.prefix + "/uploadExcel",
        files={"file": (filename, workbook(range(column_count)))},
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["failed_count"] == 0
    batch.assert_called_once()
    assert batch.call_args.args[:3] == (session, [], 1)


@pytest.mark.parametrize(
    "module,batch_name,column_count",
    [
        (terminology, "batch_create_terminology", 6),
        (data_training, "batch_create_training", 4),
    ],
)
@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize(
    "language,message",
    [
        ("zh-CN", "EXCEL列数量不匹配"),
        ("en", "Number of columns in Excel does not match"),
    ],
)
def test_insufficient_excel_columns_return_localized_400(
    api, monkeypatch, module, batch_name, column_count, empty, language, message
):
    client, session = api
    client.app.dependency_overrides.pop(get_i18n)
    monkeypatch.setattr(module, "session_maker", lambda: session)
    batch = Mock()
    monkeypatch.setattr(module, batch_name, batch)
    columns = [] if empty else range(column_count - 1)
    response = client.post(
        module.router.prefix + "/uploadExcel",
        files={"file": ("invalid.xlsx", workbook(columns))},
        headers={"Accept-Language": language},
    )
    assert response.status_code == 400, response.text
    assert response.json() == message
    batch.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize(
    "filename,exists,status,message",
    [
        ("missing_error.xlsx", False, 404, "File Not Exists"),
        ("bad.csv", True, 400, "Only support _error.xlsx"),
    ],
)
def test_knowledge_error_download_returns_client_error(
    api, tmp_path, filename, exists, status, message
):
    client, _session = api
    if exists:
        (tmp_path / filename).write_bytes(b"test file")
    response = client.post("/system/download-fail-info", json={"file": filename})
    assert response.status_code == status, response.text
    assert response.json() == message


def test_user_error_download_requires_file_id():
    with pytest.raises(HTTPException) as raised:
        user_excel.download_error_file("")
    assert raised.value.status_code == 400
    assert raised.value.detail == "file_id required"


@pytest.mark.parametrize("registered", [False, True])
def test_missing_user_error_file_returns_404(api, tmp_path, registered):
    client, _session = api
    if registered:
        user_excel._TEMP_FILE_MAP["missing"] = str(tmp_path / "missing.xlsx")
    response = client.get("/user/errorRecord/missing")
    assert response.status_code == 404, response.text
    assert response.json() == "File not found"


def test_user_error_file_outside_temp_directory_returns_403(api, tmp_path, monkeypatch):
    client, _session = api
    monkeypatch.setattr(
        user_excel.tempfile, "gettempdir", lambda: str(tmp_path / "allowed")
    )
    outside = tmp_path / "outside.xlsx"
    outside.write_bytes(b"private data")
    user_excel._TEMP_FILE_MAP["outside"] = str(outside)
    response = client.get("/user/errorRecord/outside")
    assert response.status_code == 403, response.text
    assert response.json() == "Unauthorized file access"
    assert outside.read_bytes() == b"private data"


@pytest.mark.parametrize("kind", ["knowledge", "user"])
def test_valid_error_file_can_be_downloaded(api, tmp_path, kind):
    client, _session = api
    content = workbook(["error"])
    target = tmp_path / "valid_error.xlsx"
    target.write_bytes(content)
    if kind == "knowledge":
        response = client.post("/system/download-fail-info", json={"file": target.name})
    else:
        user_excel._TEMP_FILE_MAP["valid"] = str(target)
        response = client.get("/user/errorRecord/valid")
    assert response.status_code == 200, response.text
    assert response.content == content
