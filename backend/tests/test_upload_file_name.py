"""Regression coverage for client-supplied upload file names (issue #1448).

`/datasource/parseExcel` and the deprecated `/datasource/uploadExcel` derive the
stored file name from the multipart `file.filename`. Splitting that name on "/"
only keeps Windows separators and a full client path intact, so on a Windows host
the write could leave `settings.EXCEL_PATH`.

`safe_upload_name` is now the single place that reduces the client name to one path
component, so these tests pin its contract for both separator styles and for the
names that must be rejected outright instead of being stored somewhere else.
"""

import os

import pytest

from common.utils.utils import safe_upload_name


@pytest.mark.parametrize(
    "file_name, expected",
    [
        ("orders.xlsx", "orders.xlsx"),
        ("quarter-1.xls", "quarter-1.xls"),
        ("2026-报表.csv", "2026-报表.csv"),
        ("a.b.c.csv", "a.b.c.csv"),
        ("  spaced .xlsx  ", "spaced .xlsx"),
        ("/tmp/orders.xlsx", "orders.xlsx"),
        ("./nested/orders.xlsx", "orders.xlsx"),
        ("../../orders.xlsx", "orders.xlsx"),
        ("nested/../../orders.xlsx", "orders.xlsx"),
        ("..\\..\\evil.xlsx", "evil.xlsx"),
        ("nested\\..\\..\\evil.xlsx", "evil.xlsx"),
        ("C:\\Users\\me\\orders.xlsx", "orders.xlsx"),
        ("\\\\server\\share\\orders.xlsx", "orders.xlsx"),
    ],
)
def test_only_the_last_path_component_survives(file_name, expected):
    assert safe_upload_name(file_name) == expected


@pytest.mark.parametrize(
    "file_name",
    [
        None,
        "",
        "   ",
        ".",
        "..",
        "../",
        "..\\",
        "C:orders.xlsx",
        "C:.xlsx",
        "orders.xlsx:extra",
        "orders.xlsx\x00",
    ],
)
def test_names_that_still_address_another_location_are_rejected(file_name):
    assert safe_upload_name(file_name) is None


@pytest.mark.parametrize(
    "file_name", ["dir/orders.xlsx", "dir\\orders.xlsx", "dir/dir\\orders.xlsx"]
)
def test_both_separator_styles_are_stripped(file_name):
    # The same request body can be served by a POSIX or a Windows host, so
    # neither "/" nor "\" may survive into the stored name.
    assert safe_upload_name(file_name) == "orders.xlsx"


@pytest.mark.parametrize(
    "file_name",
    [
        "..\\..\\evil.xlsx",
        "C:\\Users\\me\\orders.xlsx",
        "/tmp/orders.xlsx",
        "orders.xlsx",
    ],
)
def test_accepted_names_never_carry_a_separator_or_drive(file_name):
    name = safe_upload_name(file_name)
    assert name
    assert "/" not in name and "\\" not in name and ":" not in name
    assert os.path.basename(name) == name
