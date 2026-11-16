"""Built-in dialect policies for every ``DB`` datasource type.

Adding a datasource type means appending one ``DialectPolicy`` here (or
registering one from another module); guard and execution code stays unchanged.

``sqlglot_dialect`` keeps the parser each type used before this registry
existed (shared read-only check). ``precise_dialect`` is used where SQLBot
re-renders SQL, so the output must be valid for the real database.
"""

import logging

from apps.db.dialect.base import DialectPolicy
from apps.db.dialect.registry import DialectRegistry, dialect_registry

logger = logging.getLogger(__name__)

_MYSQL_FILE = frozenset({"LOAD_FILE", "INTO OUTFILE", "INTO DUMPFILE"})
_PG_FILE = frozenset({
    # Server-side file access: even a read-only role may read host files.
    "pg_read_file",
    "pg_read_binary_file",
    "pg_ls_dir",
    "pg_stat_file",
    "pg_write_file",
    "lo_import",
    "lo_export",
})
_ORACLE_FILE = frozenset({"UTL_FILE", "DBMS_PIPE", "DBMS_LOCK"})
_MYSQL_RESOURCE = frozenset({"sleep", "benchmark", "get_lock"})
_PG_RESOURCE = frozenset({
    "pg_sleep", "pg_sleep_for", "pg_sleep_until",
    "pg_advisory_lock", "pg_advisory_xact_lock", "pg_terminate_backend", "pg_cancel_backend",
    "dblink", "dblink_exec", "dblink_connect",
})
_ORACLE_RESOURCE = frozenset({"DBMS_LOCK", "DBMS_SESSION", "UTL_HTTP", "UTL_TCP", "UTL_INADDR"})
_MSSQL_RESOURCE = frozenset({"WAITFOR", "OPENROWSET", "OPENDATASOURCE", "OPENQUERY"})
_CK_RESOURCE = frozenset({"sleep", "sleepEachRow", "url", "remote", "remoteSecure", "file", "s3"})
_HIVE_RESOURCE = frozenset({"reflect", "java_method"})


def _pg_statement_timeout(conn, seconds: int):
    # SET LOCAL only lasts until the current transaction ends, so a pooled
    # connection does not keep the setting.
    conn.exec_driver_sql(f"SET LOCAL statement_timeout = {int(seconds) * 1000}")
    return None


def _mysql_execution_time(conn, seconds: int):
    # max_execution_time is session scoped: remember and restore it so the
    # pooled connection behaves as before for other callers.
    previous = conn.exec_driver_sql("SELECT @@SESSION.max_execution_time").scalar()
    conn.exec_driver_sql(f"SET SESSION max_execution_time = {int(seconds) * 1000}")

    def restore():
        conn.exec_driver_sql(f"SET SESSION max_execution_time = {int(previous or 0)}")

    return restore


BUILTIN_POLICIES = (
    DialectPolicy("mysql", "mysql", "mysql", _MYSQL_FILE, _MYSQL_RESOURCE, apply_timeout=_mysql_execution_time),
    DialectPolicy("doris", "mysql", "doris", _MYSQL_FILE, _MYSQL_RESOURCE),
    DialectPolicy("starrocks", "mysql", "starrocks", _MYSQL_FILE, _MYSQL_RESOURCE),
    DialectPolicy("sqlServer", "tsql", "tsql", frozenset({"EXEC", "xp_cmdshell", "sp_executesql"}),
                  _MSSQL_RESOURCE),
    DialectPolicy("hive", "hive", "hive", frozenset({"ADD FILE", "ADD JAR"}), _HIVE_RESOURCE),
    DialectPolicy("pg", None, "postgres", _PG_FILE, _PG_RESOURCE, apply_timeout=_pg_statement_timeout),
    DialectPolicy("excel", None, "postgres", _PG_FILE, _PG_RESOURCE, apply_timeout=_pg_statement_timeout),
    DialectPolicy("kingbase", None, "postgres", _PG_FILE, _PG_RESOURCE),
    DialectPolicy("redshift", None, "redshift", _PG_FILE, _PG_RESOURCE),
    # Oracle < 12c has no FETCH FIRST; DM syntax only partly matches sqlglot's
    # Oracle dialect. Cap rows while fetching instead of rewriting.
    DialectPolicy("oracle", None, "oracle", _ORACLE_FILE, _ORACLE_RESOURCE, limit_rewrite=False),
    DialectPolicy("dm", None, "oracle", _ORACLE_FILE, _ORACLE_RESOURCE, limit_rewrite=False),
    DialectPolicy("ck", None, "clickhouse", frozenset(), _CK_RESOURCE),
    # Elasticsearch SQL is executed over HTTP, not through sqlglot/SQLAlchemy.
    DialectPolicy("es", None, None, frozenset(), frozenset(), agent_supported=False, limit_rewrite=False),
)


def register_builtin_policies(registry: DialectRegistry = dialect_registry) -> None:
    for policy in BUILTIN_POLICIES:
        if registry.find(policy.ds_type) is None:
            registry.register(policy)


register_builtin_policies()
