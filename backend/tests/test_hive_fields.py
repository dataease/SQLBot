"""Regression tests for Hive DESCRIBE field discovery (issue #1250)."""

import ast
import json
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _load_symbol(relative_path, name, namespace):
    # As in test_connection_pool_manager, avoid importing unrelated DB drivers.
    path = BACKEND_DIR / relative_path
    tree = ast.parse(path.read_text(encoding="utf-8"))
    node = next(node for node in tree.body if getattr(node, "name", None) == name)
    module = ast.Module(body=[node], type_ignores=[])
    exec(compile(module, str(path), "exec"), namespace)
    return namespace[name]


@pytest.fixture
def get_hive_fields():
    cursor = Mock()
    connection = SimpleNamespace(cursor=lambda: nullcontext(cursor))
    pool = SimpleNamespace(connection=lambda: nullcontext(connection))
    namespace = {
        "json": json,
        "CoreDatasource": SimpleNamespace,
        "DatasourceConf": SimpleNamespace,
        "aes_decrypt": lambda value: value,
        "DB": SimpleNamespace(
            get_db=lambda _: SimpleNamespace(connect_type="driver")
        ),
        "ConnectType": SimpleNamespace(sqlalchemy="sqlalchemy"),
        "get_driver_pool": lambda _: pool,
        "get_field_sql": lambda *args: ("DESCRIBE sample", None, None),
    }
    _load_symbol("common/utils/utils.py", "equals_ignore_case", namespace)
    _load_symbol("apps/datasource/models/datasource.py", "ColumnSchema", namespace)
    get_fields = _load_symbol("apps/db/db.py", "get_fields", namespace)

    def discover(rows):
        cursor.fetchall.return_value = rows
        fields = get_fields(SimpleNamespace(type="hive", configuration="{}"), "sample")
        return [(field.fieldName, field.fieldType, field.fieldComment) for field in fields]

    return discover


@pytest.mark.parametrize("repeat_partition", [False, True])
def test_partition_fields_are_retained_once_without_metadata(get_hive_fields, repeat_partition):
    rows = [("id", "int", "identifier")]
    if repeat_partition:
        rows.append(("dt", "string", "partition date"))
    rows.extend([
        ("", "", ""),
        ("# Partition Information", "", ""),
        ("# col_name", "data_type", "comment"),
        ("dt", "string", "partition date"),
    ])

    assert get_hive_fields(rows) == [
        ("id", "int", "identifier"),
        ("dt", "string", "partition date"),
    ]


def test_duplicate_fields_preserve_first_occurrence_and_order(get_hive_fields):
    assert get_hive_fields([
        ("id", "int", "identifier"),
        ("dt", "string", "first comment"),
        ("region", "string", "region"),
        ("dt", "string", "repeated comment"),
    ]) == [
        ("id", "int", "identifier"),
        ("dt", "string", "first comment"),
        ("region", "string", "region"),
    ]


def test_blank_names_and_padded_metadata_are_ignored(get_hive_fields):
    assert get_hive_fields([
        (None, None, None),
        ("  ", "", ""),
        ("  # Partition Information  ", None, None),
        ("  # col_name  ", "data_type  ", "comment"),
        ("dt", "string", None),
    ]) == [("dt", "string", None)]


def test_regular_columns_preserve_names_types_and_comments(get_hive_fields):
    assert get_hive_fields([
        ("id", "bigint", None),
        ("amount", "decimal(10,2)", b"amount"),
        ("#tag", "string", "tag"),
        ("# Partition Information", "string", "a real column"),
        (" spaced name ", "string", "keep the original name"),
    ]) == [
        ("id", "bigint", None),
        ("amount", "decimal(10,2)", "amount"),
        ("#tag", "string", "tag"),
        ("# Partition Information", "string", "a real column"),
        (" spaced name ", "string", "keep the original name"),
    ]


def test_extra_driver_columns_remain_supported(get_hive_fields):
    assert get_hive_fields([
        ("id", "int", "identifier", "extra", 1, None),
        ("# Partition Information", None, None, "extra", 2, None),
        ("dt", "string", "partition date", "extra", 3, None),
    ]) == [
        ("id", "int", "identifier"),
        ("dt", "string", "partition date"),
    ]


@pytest.mark.parametrize("rows", [[], [("", "", ""), ("# col_name", "data_type", "comment")]])
def test_no_real_columns_returns_empty_list(get_hive_fields, rows):
    assert get_hive_fields(rows) == []
