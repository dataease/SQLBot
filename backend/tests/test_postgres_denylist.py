"""Regression coverage for the PostgreSQL dangerous-function denylist (issue 1438).

`DS_SPECIFIC_DANGEROUS_FUNCTIONS` is looked up with `ds.type`, whose PostgreSQL
value is `pg` (see `apps/db/constant.py`). The table was keyed `postgresql`, so
none of the PostgreSQL dangerous functions were ever blocked.

These tests drive the guard the datasource path actually uses (`check_sql_read`)
rather than the table alone, and pin the table keys to the `DB` type codes so a
mismatch cannot silently disable a dialect again.
"""

from types import SimpleNamespace

import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before app imports.

from apps.db.constant import DB
from apps.db.db import (
    COMMON_DANGEROUS_FUNCTIONS,
    DS_SPECIFIC_DANGEROUS_FUNCTIONS,
    check_sql_read,
    get_dangerous_functions,
)

PG_FILE_FUNCTIONS = {
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "pg_stat_file",
    "pg_write_file",
    "lo_import",
    "lo_export",
}


def _ds(db: DB) -> SimpleNamespace:
    return SimpleNamespace(type=db.type)


def test_every_dialect_key_is_a_db_type():
    """A key that is not a `DB.type` value silently disables that dialect's rules."""
    known = {db.type.lower() for db in DB}
    unknown = set(DS_SPECIFIC_DANGEROUS_FUNCTIONS) - known
    assert not unknown, f"denylist keys that no DB type uses: {sorted(unknown)}"


def test_postgres_functions_are_resolved_from_the_pg_type():
    functions = get_dangerous_functions(DB.pg.type)
    assert PG_FILE_FUNCTIONS <= functions
    assert COMMON_DANGEROUS_FUNCTIONS <= functions


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT pg_read_file('/etc/passwd')",
        "SELECT pg_read_binary_file('/etc/shadow')",
        "SELECT pg_ls_dir('/')",
        "SELECT pg_stat_file('/etc/passwd')",
        "SELECT pg_write_file('/tmp/out', 'x')",
        "SELECT lo_import('/etc/passwd')",
        "SELECT lo_export(1, '/tmp/out')",
    ],
)
def test_postgres_file_functions_are_rejected(sql):
    is_safe, reason = check_sql_read(sql, _ds(DB.pg))
    assert not is_safe
    assert "dangerous function" in reason


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO users (id) VALUES (1)",
        "UPDATE users SET name = 'x'",
        "DELETE FROM users",
        "TRUNCATE TABLE users",
        "COPY users FROM STDIN",
        "DROP TABLE users",
    ],
)
def test_postgres_write_statements_are_rejected(sql):
    is_safe, _ = check_sql_read(sql, _ds(DB.pg))
    assert not is_safe


def test_ordinary_postgres_select_is_still_allowed():
    is_safe, reason = check_sql_read("SELECT id, name FROM users", _ds(DB.pg))
    assert is_safe, reason


def test_other_dialects_keep_their_own_rules():
    assert "xp_cmdshell" in get_dangerous_functions(DB.sqlServer.type)
    # A MySQL-only entry must not leak into the PostgreSQL list.
    assert "LOAD_FILE" not in get_dangerous_functions(DB.pg.type)
    # ...and a PostgreSQL-only entry must not leak into the MySQL list.
    assert "pg_read_file" not in get_dangerous_functions(DB.mysql.type)
