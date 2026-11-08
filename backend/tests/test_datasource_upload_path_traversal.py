"""Offline HTTP regressions for the Excel upload routes (CWE-22, issue #1448).

These tests post real multipart bodies to `/datasource/parseExcel` and to the
deprecated `/datasource/uploadExcel`, and reuse the offline harness from
`test_datasource_import_path_traversal.py`: identity, audit logging, the database
session and the Excel reader are test adapters, so no application startup,
external database or deployed service is used.

Before the fix the stored name kept whatever the client sent apart from POSIX
directory parts (`..\\..\\evil.xlsx` -> `..\\evil_<hash>.xlsx`), which resolves
outside the upload directory on a Windows host, and `uploadExcel` matched bare
suffixes and indexed the name with `split('.')[1]`. The assertions below are the
platform-independent view of that contract: whatever the client sends, the stored
name is a single component inside the upload directory, or the request is refused.
"""

from unittest.mock import Mock

import pytest
from test_datasource_import_path_traversal import (
    api,  # noqa: F401  # shared offline harness, resolved by fixture name
)

from apps.datasource.api import datasource

PARSE_URL = "/datasource/parseExcel"
UPLOAD_URL = "/datasource/uploadExcel"
XLSX_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
INVALID_FILE_PATH = "i18n_ds_invalid_file_path"

# Names whose directory part must be dropped, not written.
STRIPPED_NAMES = [
    "..\\..\\evil.xlsx",
    "..\\evil.xlsx",
    "nested\\..\\..\\evil.xlsx",
    "../../evil.xlsx",
    "/tmp/orders.xlsx",
    "C:\\Users\\me\\orders.xlsx",
]

# Names that would still address another location after dropping the separators.
REJECTED_NAMES = ["C:evil.xlsx", "C:.xlsx", "orders.xlsx:extra"]


def stored_files(root):
    return {path for path in root.rglob("*") if path.is_file()}


def upload(client, url, file_name):
    return client.post(url, files={"file": (file_name, b"a\n1\n", XLSX_TYPE)})


@pytest.fixture
def harness(request):
    """The offline API harness defined by the import-traversal guard."""
    return request.getfixturevalue("api")


@pytest.fixture
def parse_harness(harness):
    # The preview reader is not part of this contract and would need a real workbook.
    harness.monkeypatch.setattr(
        datasource, "parse_excel_preview", Mock(return_value=[])
    )
    return harness


@pytest.mark.parametrize("file_name", STRIPPED_NAMES)
def test_parse_excel_stores_one_component_inside_the_upload_dir(
    parse_harness, file_name
):
    before = stored_files(parse_harness.tmp_path)
    response = upload(parse_harness.client, PARSE_URL, file_name)
    assert response.status_code == 200, response.text
    stored = response.json()["filePath"]
    assert "/" not in stored and "\\" not in stored and ":" not in stored, stored
    assert (parse_harness.upload_dir / stored).is_file()
    created = stored_files(parse_harness.tmp_path) - before
    assert created, f"nothing was stored for {file_name!r}"
    assert all(parse_harness.upload_dir in path.parents for path in created), created


@pytest.mark.parametrize("file_name", STRIPPED_NAMES)
def test_upload_excel_stores_one_component_inside_the_upload_dir(harness, file_name):
    before = stored_files(harness.tmp_path)
    response = upload(harness.client, UPLOAD_URL, file_name)
    # The deprecated route continues into the import engine, which the harness
    # stubs out; only the stored name is under test here.
    assert response.status_code in (200, 500), response.text
    created = stored_files(harness.tmp_path) - before
    assert created, f"nothing was stored for {file_name!r}"
    assert all(harness.upload_dir in path.parents for path in created), created
    assert all(path.name == path.name.strip("/\\") for path in created)
    assert all(":" not in path.name for path in created)


@pytest.mark.parametrize("url", [PARSE_URL, UPLOAD_URL])
@pytest.mark.parametrize("file_name", REJECTED_NAMES)
def test_names_that_keep_a_drive_relative_location_are_refused(harness, url, file_name):
    before = stored_files(harness.tmp_path)
    response = upload(harness.client, url, file_name)
    assert response.status_code == 400, response.text
    assert response.json() == INVALID_FILE_PATH
    assert stored_files(harness.tmp_path) == before


@pytest.mark.parametrize("file_name", ["evil.txlsx", "evilxlsx"])
def test_upload_excel_refuses_names_that_only_end_with_the_bare_suffix(
    harness, file_name
):
    # The whitelist used to be {"xlsx", "xls", "csv"}: "evil.txlsx" was accepted
    # and the dot-less "evilxlsx" made `split('.')[1]` raise IndexError.
    before = stored_files(harness.tmp_path)
    response = upload(harness.client, UPLOAD_URL, file_name)
    assert response.status_code == 400, response.text
    assert stored_files(harness.tmp_path) == before


def test_normal_names_keep_their_own_stem_and_extension(parse_harness):
    response = upload(parse_harness.client, PARSE_URL, "a.b.xlsx")
    assert response.status_code == 200, response.text
    stored = response.json()["filePath"]
    assert stored.startswith("a.b_") and stored.endswith(".xlsx"), stored
    assert (parse_harness.upload_dir / stored).is_file()
