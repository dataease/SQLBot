"""HTTP coverage for ID-based, owner-scoped Excel error reports."""

from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from apps.settings.api import base
from common.core.deps import get_current_user
from common.core.file import save_error_report

URL = "/system/download-fail-info"


@pytest.fixture
def api(tmp_path, monkeypatch):
    user = SimpleNamespace(id=12, oid=34)
    report_id = save_error_report(
        str(tmp_path), pd.DataFrame({"error": ["sample"]}), user.id, user.oid
    )
    report = next(tmp_path.rglob("*.xlsx"))
    app = FastAPI()
    app.include_router(base.router)
    app.dependency_overrides[get_current_user] = lambda: user
    monkeypatch.setattr(base, "path", str(tmp_path))
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            user=user,
            report=report,
            payload={"report_id": str(report_id)},
        )


def test_owner_can_download_report_repeatedly(api):
    for _ in range(2):
        response = api.client.post(URL, json=api.payload)
        assert response.status_code == 200
        assert response.content == api.report.read_bytes()
        assert "attachment" in response.headers["content-disposition"]


@pytest.mark.parametrize("field", ["id", "oid"])
def test_report_is_private_to_its_user_and_workspace(api, field):
    setattr(api.user, field, 99)
    response = api.client.post(URL, json=api.payload)
    assert response.status_code == 404
    assert response.json() == {"detail": "File Not Exists"}


@pytest.mark.parametrize(
    "value", ["orders_error.xlsx", "../outside/report.xlsx", "C:\\report.xlsx", ""]
)
@pytest.mark.parametrize("key", ["file", "report_id"])
def test_names_and_paths_never_reach_storage(api, monkeypatch, value, key):
    lookup = Mock()
    monkeypatch.setattr(base, "open_error_report", lookup)
    assert api.client.post(URL, json={key: value}).status_code == 422
    lookup.assert_not_called()


@pytest.mark.parametrize(
    "control", ["\x00", "\t", "\n", "\x01", "\r", "\x1f", "\x7f", "\x85", "\x9f"]
)
@pytest.mark.parametrize("position", [0, 12, 36])
def test_controls_in_report_id_are_rejected_before_lookup(
    api, monkeypatch, control, position
):
    lookup = Mock()
    monkeypatch.setattr(base, "open_error_report", lookup)
    report_id = api.payload["report_id"]
    response = api.client.post(
        URL, json={"report_id": report_id[:position] + control + report_id[position:]}
    )
    assert response.status_code == 422
    lookup.assert_not_called()


@pytest.mark.parametrize("replacement", ["directory", "symlink", "symlink_directory"])
def test_only_regular_files_in_the_report_directory_are_served(
    api, replacement, tmp_path
):
    outside = tmp_path / "other"
    outside.mkdir()
    target = outside / api.report.name
    api.report.rename(target)
    if replacement == "symlink":
        api.report.symlink_to(target)
    elif replacement == "symlink_directory":
        api.report.parent.rmdir()
        api.report.parent.symlink_to(outside, target_is_directory=True)
    else:
        api.report.mkdir()
    response = api.client.post(URL, json=api.payload)
    assert response.status_code == 404
    assert response.json() == {"detail": "File Not Exists"}
