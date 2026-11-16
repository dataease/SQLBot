"""Offline regressions for the shared SQL guard and the dialect registry.

``check_sql_read`` now delegates to the ``basic`` guard profile; the ``agent``
profile adds strict checks and deterministic rewrites for SQL written by an
external caller. No database, model or network is used.
"""

from types import SimpleNamespace

import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before app imports.
import sqlglot

from apps.db.constant import DB
from apps.db.db import (
    DS_SPECIFIC_DANGEROUS_FUNCTIONS,
    check_sql_read,
    get_dangerous_functions,
    get_sqlglot_dialect,
)
from apps.db.dialect import (
    DialectPolicy,
    DialectRegistry,
    UnsupportedDialectError,
    dialect_registry,
)
from apps.db.sql_guard import (
    AGENT,
    GuardPipeline,
    SqlRejected,
    TableAccess,
    build_context,
    get_pipeline,
)

EMP = TableAccess(
    "emp",
    visible_columns=frozenset({"id", "name", "dept_id"}),
    all_columns=frozenset({"id", "name", "dept_id", "salary"}),
    row_filter="(\"region\" IN ('east'))",
    schema="public",
)
DEPT = TableAccess("dept", all_columns=frozenset({"id", "title"}))
TABLES = {"emp": EMP, "dept": DEPT}


def _ds(ds_type):
    return SimpleNamespace(type=ds_type)


def agent(sql, ds_type="pg", tables=TABLES, max_rows=200):
    ctx = build_context(sql, ds_type, tables=tables, max_rows=max_rows, strict=True)
    return get_pipeline(AGENT).run(ctx), ctx


def rejected(sql, ds_type="pg", **kwargs):
    with pytest.raises(SqlRejected) as info:
        agent(sql, ds_type, **kwargs)
    return info.value


# --- dialect registry -------------------------------------------------------

def test_every_db_type_has_a_policy():
    assert {db.type.lower() for db in DB} <= dialect_registry.types()


def test_legacy_sqlglot_dialects_are_unchanged():
    # The shared read-only check must keep parsing web-flow SQL as before.
    legacy = {"mysql": "mysql", "doris": "mysql", "starrocks": "mysql", "sqlServer": "tsql", "hive": "hive"}
    for db in DB:
        assert get_sqlglot_dialect(db.type) == legacy.get(db.type)


def test_unknown_type_fails_closed():
    assert get_sqlglot_dialect("nope") is None
    with pytest.raises(UnsupportedDialectError):
        dialect_registry.get("nope")
    with pytest.raises(SqlRejected) as info:
        build_context("SELECT 1", "nope")
    assert info.value.code == "unsupported_dialect"


def test_pg_family_shares_the_file_function_denylist():
    for ds_type in ("pg", "excel", "kingbase", "redshift"):
        assert {"pg_read_file", "lo_import"} <= get_dangerous_functions(ds_type)
        assert ds_type in DS_SPECIFIC_DANGEROUS_FUNCTIONS
        is_safe, reason = check_sql_read("SELECT pg_read_file('/etc/passwd')", _ds(ds_type))
        assert not is_safe and "dangerous function" in reason


def test_a_new_dialect_is_one_registration():
    registry = DialectRegistry()
    registry.register(DialectPolicy("newdb", "postgres", resource_functions=frozenset({"stall"})))
    assert registry.get("NEWDB").sqlglot_dialect == "postgres"
    with pytest.raises(ValueError):
        registry.register(DialectPolicy("newdb"))


# --- basic profile (check_sql_read) ------------------------------------------

@pytest.mark.parametrize("sql", ["SELECT id FROM users", "WITH t AS (SELECT 1 AS x) SELECT x FROM t"])
def test_reads_are_allowed(sql):
    assert check_sql_read(sql, _ds("pg")) == (True, "")


@pytest.mark.parametrize("sql,reason", [
    ("DROP TABLE users", "Write operation 'DROP' is not allowed"),
    ("SELECT * INTO OUTFILE '/tmp/x' FROM users", "dangerous pattern"),
    ("SELECT user()", "dangerous function"),
    ("SHOW TABLES", "is not allowed. Only SELECT and WITH are permitted"),
])
def test_basic_rejections_keep_their_reasons(sql, reason):
    is_safe, message = check_sql_read(sql, _ds("pg"))
    assert not is_safe
    assert reason in message


@pytest.mark.parametrize("sql", ["", "   "])
def test_unparseable_sql_still_raises(sql):
    with pytest.raises(ValueError, match="Parse SQL Error"):
        check_sql_read(sql, _ds("pg"))


# --- agent profile: structure -------------------------------------------------

@pytest.mark.parametrize("sql,code", [
    ("SELECT name FROM emp; SELECT 1", "multiple_statements"),
    ("WITH x AS (DELETE FROM emp RETURNING *) SELECT * FROM x", "write_operation"),
    ("SELECT name FROM emp FOR UPDATE", "locking"),
    ("SELECT name FROM generate_series(1, 3)", "table_function"),
    ("SELECT 1", "table_access"),
])
def test_agent_rejects_unsafe_structure(sql, code):
    assert rejected(sql).code == code


def test_agent_rejects_table_hints_and_select_into():
    assert rejected("SELECT name FROM emp WITH (UPDLOCK)", "sqlServer").code == "table_hint"
    assert rejected("SELECT name INTO copy FROM emp").code in {"select_into", "write_operation"}


@pytest.mark.parametrize("ds_type,sql", [
    ("pg", "SELECT pg_sleep(5), name FROM emp"),
    ("pg", "SELECT version(), name FROM emp"),
    ("pg", "SELECT current_user, name FROM emp"),
    ("pg", "SELECT dblink('x', 'y'), name FROM emp"),
    ("mysql", "SELECT sleep(1), name FROM emp"),
    ("mysql", "SELECT BENCHMARK(10, MD5('a')), name FROM emp"),
    ("oracle", "SELECT DBMS_LOCK.SLEEP(5), name FROM emp"),
])
def test_agent_rejects_dangerous_functions_in_any_node_form(ds_type, sql):
    assert rejected(sql, ds_type).code == "dangerous_function"


@pytest.mark.parametrize("ds_type", ["es", "nope"])
def test_agent_rejects_unsupported_datasources(ds_type):
    assert rejected("SELECT name FROM emp", ds_type).code == "unsupported_dialect"


# --- agent profile: tables ----------------------------------------------------

@pytest.mark.parametrize("sql", [
    "SELECT * FROM secret",
    "SELECT * FROM information_schema.tables",
    "SELECT name FROM information_schema.emp",
    "SELECT name FROM other.emp",
    "SELECT title FROM dept WHERE id IN (SELECT id FROM secret)",
])
def test_agent_rejects_tables_outside_the_allowlist(sql):
    error = rejected(sql)
    assert error.code == "table_access"
    # The allowed table names must not be disclosed.
    assert "dept" not in error.reason.replace("FROM dept", "")


def test_cte_shadowing_a_table_still_reaches_the_real_table():
    error = rejected("WITH secret AS (SELECT * FROM secret) SELECT * FROM secret")
    assert error.code == "table_access"


def test_schema_qualified_allowed_table_is_accepted():
    sql, _ = agent("SELECT name FROM public.emp")
    assert "public.emp" in sql


# --- agent profile: columns ---------------------------------------------------

@pytest.mark.parametrize("sql", [
    "SELECT * FROM emp",
    "SELECT e.* FROM emp e",
    "SELECT e.salary FROM emp e",
    "SELECT name FROM emp WHERE salary > 100",
    "SELECT name FROM emp ORDER BY salary",
    "SELECT max(salary) FROM emp",
    "WITH c AS (SELECT * FROM emp) SELECT name FROM c",
])
def test_hidden_columns_are_rejected_everywhere(sql):
    assert rejected(sql).code == "column_access"


@pytest.mark.parametrize("sql", [
    "SELECT name FROM emp",
    "SELECT count(*) FROM emp",
    "SELECT * FROM dept",
    "SELECT name AS label FROM emp ORDER BY label",
    "SELECT e.name, d.title FROM emp e JOIN dept d ON e.dept_id = d.id",
])
def test_visible_columns_are_allowed(sql):
    agent(sql)


# --- agent profile: rewrites --------------------------------------------------

def test_row_filter_wraps_every_occurrence_and_keeps_aliases():
    sql, ctx = agent("SELECT e.name FROM emp e WHERE e.dept_id IN (SELECT dept_id FROM emp)")
    assert sql.count("""WHERE ("region" IN ('east'))""") == 2
    assert ") AS e " in sql
    assert ctx.notes["row_permission_applied"] == ["emp"]


def test_rewritten_sql_is_valid_and_has_no_unfiltered_reference():
    sql, _ = agent("SELECT d.title, count(*) FROM emp JOIN dept d ON emp.dept_id = d.id GROUP BY d.title")
    tree = sqlglot.parse_one(sql, read="postgres")
    emp_refs = [t for t in tree.find_all(sqlglot.exp.Table) if t.name == "emp"]
    assert emp_refs and all(t.find_ancestor(sqlglot.exp.Subquery) for t in emp_refs)


def test_unparseable_row_filter_rejects_instead_of_running_unfiltered():
    broken = {"emp": TableAccess("emp", row_filter="((")}
    assert rejected("SELECT name FROM emp", tables=broken).code in {"row_permission", "rewrite_error"}


@pytest.mark.parametrize("ds_type,sql,expected", [
    ("pg", "SELECT title FROM dept", "LIMIT 201"),
    ("pg", "SELECT title FROM dept LIMIT 5", "LIMIT 5"),
    ("mysql", "SELECT title FROM dept LIMIT 100000", "LIMIT 201"),
    ("sqlServer", "SELECT title FROM dept", "TOP 201"),
])
def test_row_cap(ds_type, sql, expected):
    out, _ = agent(sql, ds_type)
    assert expected in out


def test_oracle_family_is_capped_while_fetching_not_rewritten():
    out, _ = agent("SELECT title FROM dept", "oracle")
    assert "FETCH" not in out.upper() and "ROWNUM" not in out.upper()


# --- extensibility ------------------------------------------------------------

def test_extra_rules_plug_in_without_changing_the_pipeline():
    class DenyTitle:
        name = "deny_title"
        recheck = True

        def check(self, ctx):
            if "title" in ctx.sql.lower():
                raise SqlRejected("no titles", code="custom")

    pipeline = get_pipeline(AGENT).extend(checks=[DenyTitle()])
    ctx = build_context("SELECT title FROM dept", "pg", tables=TABLES, strict=True)
    with pytest.raises(SqlRejected, match="no titles"):
        pipeline.run(ctx)


def test_a_crashing_rule_rejects_instead_of_being_skipped():
    class Broken:
        name = "broken"
        recheck = True

        def check(self, ctx):
            raise RuntimeError("boom")

    ctx = build_context("SELECT title FROM dept", "pg", tables=TABLES)
    with pytest.raises(SqlRejected) as info:
        GuardPipeline([Broken()]).run(ctx)
    assert info.value.code == "check_error"
