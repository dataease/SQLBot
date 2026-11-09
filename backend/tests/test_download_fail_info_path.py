"""Regression coverage for the fail-info download route (path handling).

`/system/download-fail-info` joined the client-supplied `file` field onto
`settings.EXCEL_PATH` and only afterwards checked the suffix, so the route could
read a file outside the upload directory when the name ended with
`_error.xlsx`, and the order of the checks disclosed whether an arbitrary path
exists (`404` when missing, `400` when it exists with the wrong suffix).

The route is exercised over HTTP here, with its router mounted on a bare app and
the upload directory redirected to a temporary path; no database, permission
layer or xpack module is involved.
"""

import os
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.settings.api import base as settings_api

URL = "/system/download-fail-info"
REPORT = b"error report body\n"


@pytest.fixture
def api(monkeypatch, tmp_path):
    upload_dir = tmp_path / "excel"
    upload_dir.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret_error.xlsx"
    secret.write_bytes(REPORT)
    # Sibling directory whose name starts with the upload directory name.
    sibling = tmp_path / "excel_backup"
    sibling.mkdir()
    (sibling / "secret_error.xlsx").write_bytes(REPORT)

    (upload_dir / "orders_error.xlsx").write_bytes(REPORT)
    (upload_dir / "orders.xlsx").write_bytes(REPORT)  # exists, wrong suffix
    (upload_dir / "nested").mkdir()
    (upload_dir / "nested" / "orders_error.xlsx").write_bytes(REPORT)
    (upload_dir / "sub_error.xlsx").mkdir()  # a directory, not a file

    app = FastAPI()
    app.include_router(settings_api.router)
    monkeypatch.setattr(settings_api, "path", str(upload_dir))
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            upload_dir=upload_dir,
            outside=outside,
            secret=secret,
            tmp_path=tmp_path,
            monkeypatch=monkeypatch,
        )


def request(api, file_name):
    return api.client.post(URL, json={"file": file_name})


def test_report_in_the_upload_directory_is_served(api):
    response = request(api, "orders_error.xlsx")
    assert response.status_code == 200, response.text
    assert response.content == REPORT
    assert "orders_error.xlsx" in response.headers.get("content-disposition", "")


def test_name_with_a_directory_part_is_not_resolved_as_a_path(api):
    # The export endpoints answer with a bare file name, so a name that carries a
    # directory must not be used to walk into a subdirectory of the upload root.
    response = request(api, "nested/orders_error.xlsx")
    assert response.status_code in (400, 404), response.text
    assert REPORT not in response.content


@pytest.mark.parametrize(
    "file_name",
    [
        "../outside/secret_error.xlsx",
        "../../outside/secret_error.xlsx",
        "./../outside/secret_error.xlsx",
        "/etc/secret_error.xlsx",
        "..\\..\\outside\\secret_error.xlsx",
        "C:secret_error.xlsx",
        "C:\\outside\\secret_error.xlsx",
    ],
)
def test_names_that_leave_the_upload_directory_are_refused(api, file_name):
    response = request(api, file_name)
    assert response.status_code in (400, 404), response.text
    assert REPORT not in response.content
    assert api.secret.read_bytes() == REPORT  # untouched


def test_a_sibling_directory_is_not_reachable(api):
    response = request(api, "../excel_backup/secret_error.xlsx")
    assert response.status_code in (400, 404), response.text
    assert REPORT not in response.content


def test_existing_and_missing_names_are_indistinguishable(api):
    # "orders.xlsx" exists inside the upload directory but carries the wrong
    # suffix; "missing.xlsx" does not exist at all. Both must be refused the same
    # way, so the route cannot be used to probe arbitrary paths.
    existing = request(api, "orders.xlsx")
    missing = request(api, "missing.xlsx")
    assert existing.status_code == 400, existing.text
    assert missing.status_code == 400, missing.text
    assert existing.json() == missing.json()


def test_a_directory_is_never_downloaded(api):
    response = request(api, "sub_error.xlsx")
    assert response.status_code == 404, response.text


def test_a_symlink_that_leaves_the_upload_directory_is_refused(api):
    link = api.upload_dir / "link_error.xlsx"
    try:
        os.symlink(api.secret, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks are not available in this environment")
    response = request(api, "link_error.xlsx")
    assert response.status_code == 404, response.text
    assert REPORT not in response.content
