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


@pytest.fixture(params=["hive", "impala"])
def get_hive_fields(request):
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
    _load_symbol("apps/db/db.py", "is_spark_thrift", namespace)
    _load_symbol("apps/db/db.py", "parse_hive_field_rows", namespace)
    get_fields = _load_symbol("apps/db/db.py", "get_fields", namespace)

    def discover(rows):
        cursor.fetchall.return_value = rows
        fields = get_fields(SimpleNamespace(type=request.param, configuration="{}"), "sample")
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


# --- Spark Thrift Server support ---


@pytest.fixture
def get_hive_spark_fields():
    cursor = Mock()
    connection = SimpleNamespace(cursor=lambda: nullcontext(cursor))
    pool = SimpleNamespace(connection=lambda: nullcontext(connection))
    engine_probe = Mock(return_value=True)
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
        "is_spark_thrift": engine_probe,
    }
    _load_symbol("common/utils/utils.py", "equals_ignore_case", namespace)
    _load_symbol("apps/datasource/models/datasource.py", "ColumnSchema", namespace)
    _load_symbol("apps/db/db.py", "parse_hive_field_rows", namespace)
    get_fields = _load_symbol("apps/db/db.py", "get_fields", namespace)

    def discover(rows):
        cursor.fetchall.return_value = rows
        fields = get_fields(SimpleNamespace(type="hive", configuration="{}"), "sample")
        return [(field.fieldName, field.fieldType, field.fieldComment) for field in fields]

    return discover


def test_spark_describe_skips_col_name_header_row(get_hive_spark_fields):
    # Spark Thrift Server returns the (col_name, data_type, comment) header as data.
    rows = [("col_name", "data_type", "comment"),
            ("id", "bigint", None),
            ("dt", "string", "partition date")]
    assert get_hive_spark_fields(rows) == [
        ("id", "bigint", None),
        ("dt", "string", "partition date"),
    ]


def test_spark_describe_with_partition_section(get_hive_spark_fields):
    rows = [
        ("col_name", "data_type", "comment"),
        ("id", "bigint", None),
        ("# Partition Information", "", ""),
        ("# col_name", "data_type", "comment"),
        ("dt", "string", "partition date"),
    ]
    assert get_hive_spark_fields(rows) == [
        ("id", "bigint", None),
        ("dt", "string", "partition date"),
    ]


# --- SHOW TABLES (parse_hive_table_rows) ---


@pytest.fixture
def get_hive_tables():
    namespace = {"DatasourceConf": SimpleNamespace}
    _load_symbol("apps/db/db.py", "parse_hive_table_rows", namespace)
    _load_symbol("common/utils/utils.py", "equals_ignore_case", namespace)
    _load_symbol("apps/db/db.py", "is_spark_thrift", namespace)
    return namespace["parse_hive_table_rows"]


def test_hs2_show_tables_single_column(get_hive_tables):
    rows = [("orders",), ("users",), ("orders",)]
    assert get_hive_tables(rows, False) == [("orders", ""), ("users", "")]


def test_spark_show_tables_three_columns_with_header(get_hive_tables):
    rows = [
        ("database", "tableName", "isTemporary"),  # header row returned as data
        ("default", "orders", "false"),
        ("default", "users", "false"),
        ("default", "orders", "false"),
    ]
    assert get_hive_tables(rows, True) == [("orders", ""), ("users", "")]


def test_spark_show_tables_without_header(get_hive_tables):
    rows = [("default", "sales", "false"), ("default", "inventory", "false")]
    assert get_hive_tables(rows, True) == [("sales", ""), ("inventory", "")]


def test_spark_show_tables_ignores_database_column_and_handles_temp_views(get_hive_tables):
    # Spark 2.4+/3.x/4.x always returns (database, tableName, isTemporary);
    # take the second column and tolerate an empty database (temp views).
    rows = [
        ("salesdb", "orders", "false"),
        ("", "temp_view", "true"),
        ("salesdb", "orders", "false"),
    ]
    assert get_hive_tables(rows, True) == [("orders", ""), ("temp_view", "")]


def test_spark_real_table_named_tablename_is_preserved(get_hive_tables):
    assert get_hive_tables([
        ("namespace", "tableName", "isTemporary"),
        ("default", "tablename", False),
        ("default", "ordinary", False),
    ], True) == [("tablename", ""), ("ordinary", "")]


def test_spark_real_column_named_col_name_is_preserved(get_hive_spark_fields):
    assert get_hive_spark_fields([
        ("col_name", "data_type", "comment"),
        ("col_name", "string", "custom column"),
        ("id", "int", None),
    ]) == [("col_name", "string", "custom column"), ("id", "int", None)]


def test_spark_discovery_sync_preserves_saved_metadata(get_hive_tables):
    from typing import List
    from sqlalchemy import and_
    from sqlmodel import Session, create_engine, select
    from apps.datasource.models.datasource import CoreTable, CoreField, ColumnSchema

    engine = create_engine("sqlite://")
    CoreTable.__table__.create(engine)
    CoreField.__table__.create(engine)
    namespace = dict(
        SessionDep=Session, CoreDatasource=SimpleNamespace, CoreTable=CoreTable,
        CoreField=CoreField, ColumnSchema=ColumnSchema, List=List, select=select,
        and_=and_, invalidate_metadata=lambda *a: None,
        run_save_table_embeddings=lambda *a: None,
        run_save_ds_embeddings=lambda *a: None,
    )
    parse_fields = _load_symbol("apps/db/db.py", "parse_hive_field_rows", namespace)
    discovered_fields = [
        ColumnSchema(n, t, c)
        for n, t, c in parse_fields([
            ("col_name", "data_type", "comment"),
            ("col_name", "string", "source comment"),
        ], True)
    ]
    namespace["getFieldsByDs"] = lambda *a: discovered_fields
    namespace["get_tables_by_ds_id"] = lambda session, ds_id: session.exec(
        select(CoreTable).where(CoreTable.ds_id == ds_id)
    ).all()
    sync_fields = _load_symbol("apps/datasource/crud/datasource.py", "sync_fields", namespace)
    sync_table = _load_symbol("apps/datasource/crud/datasource.py", "sync_table", namespace)
    with Session(engine) as session:
        for table_id, name in [(11, "tablename"), (12, "ordinary")]:
            session.add(CoreTable(id=table_id, ds_id=1, table_name=name,
                                  table_comment="source", custom_comment="custom table"))
            session.add(CoreField(id=table_id + 100, ds_id=1, table_id=table_id,
                                  field_name="col_name", field_type="string",
                                  field_comment="source", custom_comment="custom field"))
        session.commit()
        tables = [
            CoreTable(table_name=name, table_comment=comment)
            for name, comment in get_hive_tables([
                ("database", "tableName", "isTemporary"),
                ("default", "tablename", False), ("default", "ordinary", False),
            ], True)
        ]
        sync_table(session, SimpleNamespace(id=1), tables)
        ordinary = session.get(CoreTable, 12)
        sync_fields(session, SimpleNamespace(id=1), ordinary, discovered_fields)
        session.expire_all()
        assert [(t.id, t.custom_comment) for t in session.exec(
            select(CoreTable).order_by(CoreTable.id)
        )] == [(11, "custom table"), (12, "custom table")]
        assert [(f.id, f.custom_comment) for f in session.exec(
            select(CoreField).order_by(CoreField.id)
        )] == [(111, "custom field"), (112, "custom field")]
