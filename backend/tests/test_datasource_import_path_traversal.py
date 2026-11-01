"""Offline HTTP regressions for path traversal in /datasource/importToDb (CWE-22).

Identity, audit persistence, database sessions and the import engine are test
adapters. No application startup, external database or deployed service is used.
"""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before API imports.
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from apps.datasource.api import datasource
from apps.system.schemas.permission import RequestContextMiddleware
from common.audit.schemas.logger_decorator import SystemLogger
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.db import get_session
from common.core.deps import get_i18n
from common.core.response_middleware import ResponseMiddleware, exception_handler

IMPORT_URL = "/datasource/importToDb"
SHEETS = [
    {"sheetName": "Sheet1", "fields": [{"fieldName": "a", "fieldType": "string"}]}
]
# get_i18n is overridden to return the key itself.
INVALID_FILE_PATH = "i18n_ds_invalid_file_path"


@pytest.fixture
def api(monkeypatch, tmp_path):
    upload_dir = tmp_path / "excel"
    upload_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.csv"
    secret.write_text("a\nprivate data\n")
    # Sibling whose name starts with the upload directory name.
    sibling = tmp_path / "excel_backup"
    sibling.mkdir()
    (sibling / "secret.csv").write_text("a\nprivate data\n")

    app = FastAPI()
    app.include_router(datasource.router)
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
    monkeypatch.setattr(datasource, "path", str(upload_dir))
    monkeypatch.setattr(datasource, "get_engine_conn", Mock())
    reader = Mock(side_effect=RuntimeError("reader reached"))
    monkeypatch.setattr(datasource, "read_import_dataframe", reader)
    # ResponseMiddleware tracks live instances globally in the application.
    monkeypatch.setattr(ResponseMiddleware, "instances", [])
    with TestClient(app, raise_server_exceptions=False) as client:
        yield SimpleNamespace(
            client=client,
            upload_dir=upload_dir,
            outside=outside,
            secret=secret,
            reader=reader,
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
        )


def post(api, file_path, sheets=SHEETS):
    return api.client.post(IMPORT_URL, json={"filePath": file_path, "sheets": sheets})


def assert_rejected(api, response):
    assert response.status_code == 400, response.text
    assert response.json() == INVALID_FILE_PATH
    api.reader.assert_not_called()


def test_absolute_file_path_is_rejected(api):
    response = api.client.post(
        IMPORT_URL, json={"filePath": str(api.secret), "sheets": SHEETS}
    )
    assert response.status_code == 400, response.text
    assert response.json() == INVALID_FILE_PATH
    api.reader.assert_not_called()


@pytest.mark.parametrize(
    "file_path",
    [
        "../outside/secret.csv",
        "./../outside/secret.csv",
        "nested/../../outside/secret.csv",
    ],
)
def test_relative_traversal_is_rejected(api, file_path):
    response = api.client.post(
        IMPORT_URL, json={"filePath": file_path, "sheets": SHEETS}
    )
    assert response.status_code == 400, response.text
    assert response.json() == INVALID_FILE_PATH
    api.reader.assert_not_called()


def test_symlink_leaving_upload_directory_is_rejected(api):
    link = api.upload_dir / "link.csv"
    os.symlink(api.secret, link)
    response = api.client.post(
        IMPORT_URL, json={"filePath": link.name, "sheets": SHEETS}
    )
    assert response.status_code == 400, response.text
    assert response.json() == INVALID_FILE_PATH
    api.reader.assert_not_called()


@pytest.mark.parametrize("file_path", ["", "."])
def test_upload_directory_itself_is_rejected(api, file_path):
    response = api.client.post(
        IMPORT_URL, json={"filePath": file_path, "sheets": SHEETS}
    )
    assert response.status_code == 400, response.text
    assert response.json() == INVALID_FILE_PATH
    api.reader.assert_not_called()


def test_missing_file_in_upload_directory_returns_400(api):
    response = api.client.post(
        IMPORT_URL, json={"filePath": "missing_0123456789.csv", "sheets": SHEETS}
    )
    assert response.status_code == 400, response.text
    assert response.json() == "File not found"
    api.reader.assert_not_called()


def test_uploaded_file_name_is_accepted(api):
    uploaded = api.upload_dir / "orders_0123456789.csv"
    uploaded.write_text("a\n1\n")
    response = api.client.post(
        IMPORT_URL, json={"filePath": uploaded.name, "sheets": []}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"] == {"filename": uploaded.name, "sheets": []}


def test_uploaded_file_is_read_from_upload_directory(api):
    uploaded = api.upload_dir / "orders_0123456789.csv"
    uploaded.write_text("a\n1\n")
    response = api.client.post(
        IMPORT_URL, json={"filePath": uploaded.name, "sheets": SHEETS}
    )
    # The stub reader stops the import after the path check has passed.
    assert response.status_code == 500, response.text
    api.reader.assert_called_once()
    assert api.reader.call_args.args[0] == os.path.realpath(uploaded)


@pytest.mark.parametrize(
    "file_path",
    ["../excel_backup/secret.csv", "../excel_backup", "..", "nested/.."],
)
def test_sibling_with_same_prefix_and_parent_are_rejected(api, file_path):
    # A plain string prefix check (startswith/commonprefix) accepts these.
    assert_rejected(api, post(api, file_path))


@pytest.mark.parametrize(
    "file_path",
    ["../outside/does_not_exist.csv", "/nonexistent_0123456789/x.csv"],
)
def test_missing_file_outside_is_rejected_before_existence_check(api, file_path):
    # Answering "File not found" here would reveal which paths exist outside.
    assert_rejected(api, post(api, file_path))


def test_directory_symlink_leaving_upload_directory_is_rejected(api):
    os.symlink(api.outside, api.upload_dir / "sub")
    assert_rejected(api, post(api, "sub/secret.csv"))


def test_symlink_inside_upload_directory_is_accepted(api):
    target = api.upload_dir / "orders_0123456789.csv"
    target.write_text("a\n1\n")
    os.symlink(target, api.upload_dir / "alias.csv")
    response = post(api, "alias.csv", sheets=[])
    assert response.status_code == 200, response.text


def test_upload_directory_behind_symlink_still_accepts_uploads(api):
    # EXCEL_PATH may itself contain a symlink (e.g. /var -> /private/var on
    # macOS or a mounted volume). Both sides of the comparison must be resolved.
    link = api.tmp_path / "excel_link"
    os.symlink(api.upload_dir, link)
    api.monkeypatch.setattr(datasource, "path", str(link))
    uploaded = api.upload_dir / "orders_0123456789.csv"
    uploaded.write_text("a\n1\n")

    accepted = post(api, uploaded.name, sheets=[])
    assert accepted.status_code == 200, accepted.text

    post(api, uploaded.name)
    api.reader.assert_called_once()
    assert api.reader.call_args.args[0] == os.path.realpath(uploaded)

    api.reader.reset_mock()
    assert_rejected(api, post(api, "../outside/secret.csv"))


def test_null_byte_in_file_path_is_rejected(api):
    assert_rejected(api, post(api, "secret.csv\x00"))
