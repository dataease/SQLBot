"""Strict rules for SQL submitted by an external caller (agent tools).

These run on top of the basic read-only checks. They assume the SQL author is
untrusted: one statement, no locks or nested writes, no resource-exhausting
functions, and only the tables/columns the caller is allowed to read.
"""

from sqlglot import expressions as exp

from apps.db.sql_guard.base import GuardContext, SqlRejected
from apps.db.sql_guard.basic import WRITE_STATEMENT_TYPES, dangerous_functions_for
from apps.db.sql_guard.tables import physical_tables_in, scopes_of

# Identity/introspection helpers sqlglot parses into named nodes rather than
# ``Anonymous``; the basic check only sees the latter.
NAMED_IDENTITY_FUNCTIONS = (
    exp.CurrentUser, exp.CurrentVersion, exp.CurrentDatabase, exp.CurrentSchema,
    exp.CurrentCatalog, exp.CurrentRole, exp.SessionUser,
)

# Catalog schemas that expose the whole database structure.
SYSTEM_SCHEMAS = frozenset({
    "information_schema", "pg_catalog", "mysql", "performance_schema", "sys",
    "sysibm", "system", "dba", "all", "user",
})


def _function_names(node: exp.Expression) -> set[str]:
    """Every name a function call can be matched by: bare, qualified and package."""
    names = set()
    if isinstance(node, exp.Anonymous):
        names.add(node.name.upper())
    elif isinstance(node, exp.Func):
        names.update(n.upper() for n in node.sql_names())
        names.add(type(node).__name__.upper())
    parent = node.parent
    if isinstance(parent, exp.Dot) and parent.expression is node:
        # ``PKG.FUNC(...)`` / ``schema.PKG.FUNC(...)``: match the package too.
        for ident in parent.this.find_all(exp.Identifier):
            names.add(ident.name.upper())
    return names


class AgentDialectCheck:
    name = "agent_dialect"
    recheck = False

    def check(self, ctx: GuardContext) -> None:
        if not ctx.policy.agent_supported:
            raise SqlRejected(f"Datasource type '{ctx.policy.ds_type}' is not supported", code="unsupported_dialect")


class SingleStatementCheck:
    name = "single_statement"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        ctx.tree()


class NestedWriteCheck:
    """Reject DML/DDL anywhere in the tree (e.g. ``WITH x AS (DELETE ...)``)."""

    name = "nested_write"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        for node in ctx.tree().walk():
            if isinstance(node, WRITE_STATEMENT_TYPES):
                raise SqlRejected(f"SQL contains write operation: {type(node).__name__}", code="write_operation")


class LockAndIntoCheck:
    """Reject row locks, ``SELECT ... INTO`` and table lock hints."""

    name = "lock_and_into"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        tree = ctx.tree()
        for select in tree.find_all(exp.Select):
            if select.args.get("locks"):
                raise SqlRejected("Locking clauses (FOR UPDATE/SHARE) are not allowed", code="locking")
            if select.args.get("into"):
                raise SqlRejected("SELECT ... INTO is not allowed", code="select_into")
        if any(True for _ in tree.find_all(exp.WithTableHint)):
            raise SqlRejected("Table hints are not allowed", code="table_hint")


class FunctionDenylistCheck:
    """Denylisted, identity and resource-exhausting functions, in any node form."""

    name = "function_denylist"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        denied = {f.upper() for f in dangerous_functions_for(ctx) | ctx.policy.resource_functions}
        for node in ctx.tree().walk():
            if isinstance(node, NAMED_IDENTITY_FUNCTIONS):
                raise SqlRejected(f"SQL contains dangerous function: {node.sql_name()}", code="dangerous_function")
            if isinstance(node, exp.Func):
                hit = _function_names(node) & denied
                if hit:
                    raise SqlRejected(f"SQL contains dangerous function: {sorted(hit)[0]}", code="dangerous_function")


class TableAllowlistCheck:
    """Every physical table must be one the caller may read, in its own schema."""

    name = "table_allowlist"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        if ctx.tables is None:
            raise SqlRejected("No table permissions were resolved", code="table_access")
        tables = [t for scope in scopes_of(ctx.tree()) for t in physical_tables_in(scope)]
        if not tables:
            raise SqlRejected("SQL must read from at least one table", code="table_access")
        denied = set()
        for table in tables:
            access = ctx.tables.get(table.name)
            if access is None or table.schema in SYSTEM_SCHEMAS or table.catalog in SYSTEM_SCHEMAS:
                denied.add(table.node.sql(dialect=ctx.dialect))
            elif table.schema and access.schema and table.schema != access.schema:
                denied.add(table.node.sql(dialect=ctx.dialect))
        if denied:
            # Never list the allowed tables: that would disclose the schema.
            raise SqlRejected(f"SQL references tables that are not accessible: {', '.join(sorted(denied))}",
                              code="table_access")


class ColumnPermissionCheck:
    """Reject ``*`` on restricted tables and any reference to a hidden column.

    Hidden columns are rejected everywhere (select list, WHERE, JOIN, ORDER BY,
    function arguments) because filters can reveal their values too.
    Unqualified columns are checked against every restricted table in the same
    scope; ambiguity is resolved conservatively.
    """

    name = "column_permission"
    recheck = False

    def check(self, ctx: GuardContext) -> None:
        if ctx.tables is None:
            raise SqlRejected("No table permissions were resolved", code="table_access")
        for scope in scopes_of(ctx.tree()):
            restricted = {}
            for table in physical_tables_in(scope):
                access = ctx.tables.get(table.name)
                if access is not None and access.visible_columns is not None:
                    restricted[table.alias] = access
            if not restricted:
                continue
            self._check_stars(scope, restricted)
            self._check_columns(scope, restricted)

    @staticmethod
    def _check_stars(scope, restricted) -> None:
        select = scope.expression
        if not isinstance(select, exp.Select):
            return
        for projection in select.expressions:
            if isinstance(projection, exp.Star):
                raise SqlRejected("SELECT * is not allowed on tables with column permissions; list the columns",
                                  code="column_access")
            if isinstance(projection, exp.Column) and isinstance(projection.this, exp.Star):
                if projection.table.lower() in restricted:
                    raise SqlRejected(f"{projection.table}.* is not allowed on tables with column permissions",
                                      code="column_access")

    @staticmethod
    def _is_hidden(access, name: str, qualified: bool) -> bool:
        if name in access.visible_columns:
            return False
        if qualified or not access.all_columns:
            # ``t.col`` must be visible on ``t``; with no column catalogue an
            # unqualified name cannot be attributed, so it is treated as hidden.
            return True
        # Unqualified: only names that really exist on the table are hidden.
        # Others belong to another table or are select-list aliases.
        return name in access.all_columns

    @classmethod
    def _check_columns(cls, scope, restricted) -> None:
        for column in scope.columns:
            name = column.name.lower()
            if not name or isinstance(column.this, exp.Star):
                continue
            qualifier = column.table.lower()
            if qualifier:
                candidates = [restricted[qualifier]] if qualifier in restricted else []
            else:
                candidates = list(restricted.values())
            for access in candidates:
                if cls._is_hidden(access, name, qualified=bool(qualifier)):
                    raise SqlRejected(f"Column '{column.name}' is not accessible", code="column_access")


def strict_checks() -> list:
    return [
        AgentDialectCheck(),
        SingleStatementCheck(),
        NestedWriteCheck(),
        LockAndIntoCheck(),
        FunctionDenylistCheck(),
        TableAllowlistCheck(),
        ColumnPermissionCheck(),
    ]
