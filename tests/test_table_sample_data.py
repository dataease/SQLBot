"""Isolated regression tests for the table-sample context switch (#1291).

Load function definitions from the actual sources, not copied implementations.
This avoids importing database drivers, embedding models and X-Pack just to test
sampling and prompt construction. Settings uses the real Pydantic loader. These
are unit tests, not full application or model-provider integration tests.
"""

import __future__
import ast
import importlib.util
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

import pytest
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SENTINEL = "SQLBOT_SAMPLE_SENTINEL_1291"


def load_functions(relative_path, names, namespace):
    """Execute unchanged source definitions with explicit dependency doubles."""
    path = BACKEND / relative_path
    source = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    definitions = [
        node for node in source.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert {node.name for node in definitions} == set(names)
    module = ast.Module(body=definitions, type_ignores=[])
    code = compile(
        module, str(path), "exec", flags=__future__.annotations.compiler_flag,
        dont_inherit=True,
    )
    exec(code, namespace)
    return namespace


@pytest.fixture
def settings_class(monkeypatch, tmp_path):
    # Do not load a developer's .env or carry a previous test's configuration.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TABLE_SAMPLE_DATA_ENABLED", raising=False)
    spec = importlib.util.spec_from_file_location(
        "sqlbot_test_settings", BACKEND / "common/core/config.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Settings


def test_sample_context_is_enabled_by_default(settings_class):
    assert settings_class(_env_file=None).TABLE_SAMPLE_DATA_ENABLED is True


@pytest.mark.parametrize("value, expected", [
    ("true", True), ("false", False), ("TRUE", True), ("FALSE", False),
    (" True ", True), (" False ", False), ("1", True), ("0", False),
])
def test_environment_boolean_parsing(settings_class, monkeypatch, value, expected):
    monkeypatch.setenv("TABLE_SAMPLE_DATA_ENABLED", value)
    assert settings_class(_env_file=None).TABLE_SAMPLE_DATA_ENABLED is expected


def test_invalid_boolean_is_rejected(settings_class, monkeypatch):
    monkeypatch.setenv("TABLE_SAMPLE_DATA_ENABLED", "not-a-boolean")
    with pytest.raises(ValidationError):
        settings_class(_env_file=None)


def test_dotenv_can_disable_sample_context(settings_class, tmp_path):
    env_file = tmp_path / "sample.env"
    env_file.write_text("TABLE_SAMPLE_DATA_ENABLED=false\n", encoding="utf-8")
    assert settings_class(_env_file=env_file).TABLE_SAMPLE_DATA_ENABLED is False


@pytest.fixture
def sampling():
    fields = [SimpleNamespace(
        field_name="sku", field_type="varchar", custom_comment="Product code",
    )]
    table = SimpleNamespace(
        id=1, table_name="orders", custom_comment="Order records", embedding=None,
    )
    table_obj = SimpleNamespace(schema="shop", table=table, fields=fields)
    namespace = {
        "settings": SimpleNamespace(
            TABLE_SAMPLE_DATA_ENABLED=True, TABLE_EMBEDDING_ENABLED=False,
        ),
        "get_table_obj_by_ds": Mock(return_value=[table_obj]),
        "exec_sql": Mock(return_value={"data": [{"sku": SENTINEL}]}),
        "DB": SimpleNamespace(get_db=lambda _: SimpleNamespace(prefix='"', suffix='"')),
        "equals_ignore_case": lambda first, second: first.lower() == second.lower(),
    }
    return load_functions(
        "apps/datasource/crud/datasource.py",
        {"get_tables_sample_data", "get_table_sample_data", "get_table_schema", "execSql", "preview"},
        namespace,
    )


def test_disabled_does_not_read_metadata_or_rows(sampling):
    sampling["settings"].TABLE_SAMPLE_DATA_ENABLED = False
    result = sampling["get_tables_sample_data"](
        object(), object(), SimpleNamespace(type="pg"),
    )
    assert result == ""
    sampling["get_table_obj_by_ds"].assert_not_called()
    sampling["exec_sql"].assert_not_called()


def test_enabled_preserves_sample_query_and_output(sampling):
    session, user = object(), object()
    datasource = SimpleNamespace(type="pg")
    result = sampling["get_tables_sample_data"](session, user, datasource)
    sampling["get_table_obj_by_ds"].assert_called_once_with(
        session=session, current_user=user, ds=datasource,
    )
    sampling["exec_sql"].assert_called_once_with(
        ds=datasource, sql='SELECT "sku" FROM "orders" LIMIT 3', origin_column=True,
    )
    assert result == '# Table: orders\n[\n  {\n    "sku": "' + SENTINEL + '"\n  }\n]'


@pytest.mark.parametrize("table_list", [[], ["another_table"]])
def test_selected_table_filter_is_preserved(sampling, table_list):
    assert sampling["get_tables_sample_data"](
        object(), object(), SimpleNamespace(type="pg"), table_list,
    ) == ""
    sampling["exec_sql"].assert_not_called()


def test_no_authorized_fields_does_not_sample(sampling):
    sampling["get_table_obj_by_ds"].return_value[0].fields = []
    assert sampling["get_tables_sample_data"](
        object(), object(), SimpleNamespace(type="pg"),
    ) == ""
    sampling["exec_sql"].assert_not_called()


def test_sample_limit_remains_three_rows(sampling):
    sampling["exec_sql"].return_value = {"data": [{"sku": n} for n in range(5)]}
    result = sampling["get_tables_sample_data"](
        object(), object(), SimpleNamespace(type="pg"),
    )
    assert json.loads(result.split("\n", 1)[1]) == [{"sku": 0}, {"sku": 1}, {"sku": 2}]


def test_disabled_does_not_remove_schema(sampling):
    sampling["settings"].TABLE_SAMPLE_DATA_ENABLED = False
    schema, tables = sampling["get_table_schema"](
        object(), object(), SimpleNamespace(type="pg", table_relation=None),
        "Show orders", embedding=False,
    )
    assert tables == ["orders"]
    assert "shop.orders" in schema
    assert "sku:varchar, Product code" in schema
    sampling["exec_sql"].assert_not_called()


def test_disabled_does_not_block_explicit_sql_execution(sampling):
    sampling["settings"].TABLE_SAMPLE_DATA_ENABLED = False
    sampling["CoreDatasource"] = SimpleNamespace(id=1)
    sampling["select"] = Mock()
    session, datasource = Mock(), object()
    session.exec.return_value.first.return_value = datasource
    result = sampling["execSql"](session, 1, "SELECT 1")
    sampling["exec_sql"].assert_called_once_with(datasource, "SELECT 1", True)
    assert result is sampling["exec_sql"].return_value


@pytest.fixture
def templates():
    template = {"template": {"sql": {
        "generate_basic_info": (
            "<db-engine>{engine}</db-engine>\n<schema>{schema}</schema>\n"
            "<sample-data>{sample_data}</sample-data>"
        ),
        "other_rule": "Preserve other rules",
    }}}
    namespace = {
        "settings": SimpleNamespace(TABLE_SAMPLE_DATA_ENABLED=True),
        "get_base_template": Mock(return_value=template),
    }
    return load_functions(
        "apps/template/generate_sql/generator.py", {"get_sql_template"}, namespace,
    )


@pytest.mark.parametrize("enabled", [True, False])
def test_template_controls_sample_insertion_without_removing_schema(templates, enabled):
    templates["settings"].TABLE_SAMPLE_DATA_ENABLED = enabled
    result = templates["get_sql_template"]()
    rendered = result["generate_basic_info"].format(
        engine="PostgreSQL", schema="orders(sku varchar)", sample_data=SENTINEL,
    )
    assert (SENTINEL in rendered) is enabled
    assert "PostgreSQL" in rendered
    assert "orders(sku varchar)" in rendered
    assert result["other_rule"] == "Preserve other rules"


def test_disabling_does_not_mutate_shared_templates(templates):
    original = deepcopy(templates["get_base_template"].return_value)
    templates["settings"].TABLE_SAMPLE_DATA_ENABLED = False
    disabled = templates["get_sql_template"]()
    assert "{sample_data}" not in disabled["generate_basic_info"]
    assert templates["get_base_template"].return_value == original
    templates["settings"].TABLE_SAMPLE_DATA_ENABLED = True
    assert "{sample_data}" in templates["get_sql_template"]()["generate_basic_info"]


def test_disabled_does_not_block_manual_preview(sampling):
    sampling["settings"].TABLE_SAMPLE_DATA_ENABLED = False
    sampling.update({
        "CoreDatasource": MagicMock(), "CoreField": MagicMock(), "CoreTable": MagicMock(),
        "is_normal_user": Mock(return_value=False),
        "get_engine_config": Mock(return_value=SimpleNamespace(dbSchema="public")),
    })
    datasource = SimpleNamespace(type="excel")
    field = SimpleNamespace(field_name="sku", checked=True)
    table = SimpleNamespace(id=1, table_name="orders")
    ds_query, field_query, table_query = Mock(), Mock(), Mock()
    ds_query.filter.return_value.first.return_value = datasource
    field_query.filter.return_value.order_by.return_value.all.return_value = [field]
    table_query.filter.return_value.first.return_value = table
    session = Mock()
    session.query.side_effect = [ds_query, field_query, table_query]
    result = sampling["preview"](session, object(), 1, SimpleNamespace(table=table))
    sampling["exec_sql"].assert_called_once()
    args = sampling["exec_sql"].call_args.args
    assert args[0] is datasource
    assert '"public"."orders"' in args[1]
    assert "LIMIT 100" in args[1]
    assert args[2] is True
    assert result is sampling["exec_sql"].return_value
