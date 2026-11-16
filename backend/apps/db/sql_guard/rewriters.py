"""Deterministic SQL rewriters (no model involved)."""

import sqlglot
from sqlglot import expressions as exp

from apps.db.sql_guard.base import GuardContext, SqlRejected
from apps.db.sql_guard.tables import physical_tables_in, scopes_of


class RowPermissionRewriter:
    """Replace each restricted table with ``(SELECT * FROM t WHERE <filter>) AS <alias>``.

    Filters come from the permission engine (values already escaped, written in
    the datasource dialect). Every occurrence is wrapped, including tables
    inside CTEs and subqueries, and the original alias is kept so column
    references stay valid.
    """

    name = "row_permission"

    def rewrite(self, ctx: GuardContext) -> str:
        if not ctx.tables or not any(a.row_filter for a in ctx.tables.values()):
            return ctx.sql
        tree = ctx.tree().copy()
        targets = []
        for scope in scopes_of(tree):
            for table in physical_tables_in(scope):
                access = ctx.tables.get(table.name)
                if access is not None and access.row_filter:
                    targets.append((table, access))
        if not targets:
            return ctx.sql
        for table, access in targets:
            try:
                condition = sqlglot.parse_one(access.row_filter, read=ctx.dialect, into=exp.Condition)
            except Exception as e:
                raise SqlRejected(f"Row permission for '{table.name}' cannot be applied", code="row_permission") from e
            alias = table.node.args.get("alias")
            alias_ident = alias.this.copy() if alias is not None else table.node.this.copy()
            source = table.node.copy()
            source.set("alias", None)
            subquery = exp.select("*").from_(source).where(condition).subquery(alias=alias_ident)
            table.node.replace(subquery)
        ctx.notes["row_permission_applied"] = sorted({t.name for t, _ in targets})
        return tree.sql(dialect=ctx.dialect)


class RowLimitRewriter:
    """Cap the number of returned rows at ``ctx.max_rows + 1``.

    One extra row lets the caller report truncation. An existing smaller literal
    limit is kept; a larger one (or none) is replaced with the cap. Dialects
    whose policy disables ``limit_rewrite`` are capped while fetching instead.
    """

    name = "row_limit"

    def rewrite(self, ctx: GuardContext) -> str:
        if not ctx.max_rows or not ctx.policy.limit_rewrite:
            return ctx.sql
        cap = int(ctx.max_rows) + 1
        tree = ctx.tree().copy()
        current = self._current_limit(tree)
        if current is not None and current <= cap:
            return ctx.sql
        return tree.limit(cap).sql(dialect=ctx.dialect)

    @staticmethod
    def _current_limit(tree: exp.Expression):
        node = tree.args.get("limit")
        if node is None:
            return None
        value = node.args.get("expression") or node.args.get("count")
        if isinstance(value, exp.Literal) and value.is_int:
            return int(value.this)
        # Non-literal limits (parameters, expressions) are replaced.
        return None
