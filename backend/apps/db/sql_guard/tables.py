"""Physical table discovery shared by checks and rewriters.

A physical table is a ``Table`` node that does not resolve to a CTE or derived
table in its scope. CTEs may shadow physical names
(``WITH t AS (SELECT * FROM t)``); scope resolution keeps the inner reference
physical, unlike name-based filtering.

Scopes are built once per call: ``Scope`` objects from different
``traverse_scope`` runs are not comparable.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from sqlglot import expressions as exp
from sqlglot.optimizer.scope import Scope, traverse_scope

from apps.db.sql_guard.base import GuardContext, SqlRejected


@dataclass(frozen=True)
class PhysicalTable:
    node: exp.Table
    scope: Scope

    @property
    def name(self) -> str:
        return self.node.name.lower()

    @property
    def alias(self) -> str:
        return self.node.alias_or_name.lower()

    @property
    def schema(self) -> str:
        return (self.node.db or "").lower()

    @property
    def catalog(self) -> str:
        return (self.node.catalog or "").lower()


def scopes_of(tree: exp.Expression) -> list[Scope]:
    try:
        return traverse_scope(tree)
    except Exception as e:  # sqlglot raises OptimizeError and others
        raise SqlRejected(f"Unable to analyse SQL structure: {e}", code="parse_error") from e


def physical_tables_in(scope: Scope) -> list[PhysicalTable]:
    found = []
    for table in scope.tables:
        if not table.name:
            # Table-valued functions (``FROM generate_series(...)``) have no name.
            raise SqlRejected("Table functions are not allowed", code="table_function")
        if isinstance(scope.sources.get(table.alias_or_name), Scope) and not table.args.get("db"):
            continue  # resolves to a CTE or derived table in this scope
        found.append(PhysicalTable(table, scope))
    return found


def iter_physical_tables(tree: exp.Expression) -> Iterator[PhysicalTable]:
    for scope in scopes_of(tree):
        yield from physical_tables_in(scope)


def physical_table_names(ctx: GuardContext) -> set[str]:
    return {t.name for t in iter_physical_tables(ctx.tree())}
