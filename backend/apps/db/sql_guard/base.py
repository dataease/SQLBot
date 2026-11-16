"""Core types of the SQL guard: context, check/rewrite protocols, pipeline.

A guard run takes one SQL string for one datasource and either returns the SQL
to execute or raises ``SqlRejected``. Rules are independent ``SqlCheck`` and
``SqlRewriter`` objects composed into a ``GuardPipeline``; adding a rule means
adding an object to a profile, not editing the pipeline.

Every failure is fatal: an unknown dialect, a parse error or an exception in
any rule rejects the SQL. Nothing is skipped silently.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import sqlglot
from sqlglot import expressions as exp

from apps.db.dialect import DialectPolicy, dialect_registry


class SqlRejected(ValueError):
    """The SQL must not be executed. ``reason`` is safe to show to the caller."""

    def __init__(self, reason: str, *, code: str = "rejected"):
        super().__init__(reason)
        self.reason = reason
        self.code = code


@dataclass
class TableAccess:
    """What the caller may read from one physical table (by lower-cased name)."""

    name: str
    # Visible column names (lower-cased); ``None`` means every column is visible.
    visible_columns: frozenset[str] | None = None
    # All checked column names known for the table (lower-cased), used to
    # attribute unqualified columns. Empty means unknown (treated strictly).
    all_columns: frozenset[str] = frozenset()
    # SQL boolean expression restricting rows, already escaped by its producer
    # and written in the datasource's own dialect.
    row_filter: str | None = None
    # Schema the table belongs to (lower-cased); empty means "not checked".
    schema: str = ""


@dataclass
class GuardContext:
    sql: str
    policy: DialectPolicy
    # Physical tables the caller may read; ``None`` disables table checks.
    tables: dict[str, TableAccess] | None = None
    allow_metadata_queries: bool = False
    max_rows: int | None = None
    # Parse with ``policy.strict_dialect`` instead of the legacy dialect.
    strict: bool = False
    # Free-form values rules may share (e.g. flags for the response).
    notes: dict[str, Any] = field(default_factory=dict)
    _statements: list | None = field(default=None, repr=False)

    @property
    def dialect(self) -> str | None:
        return self.policy.strict_dialect if self.strict else self.policy.sqlglot_dialect

    def statements(self) -> list:
        """Parse lazily; parse failures reject the SQL."""
        if self._statements is None:
            try:
                parsed = sqlglot.parse(self.sql, read=self.dialect)
            except Exception as e:  # sqlglot raises several error types
                raise SqlRejected(f"Parse SQL Error: {e}", code="parse_error") from e
            if not parsed:
                raise SqlRejected("Parse SQL Error", code="parse_error")
            # ``sqlglot.parse`` yields ``None`` for empty segments (e.g. a lone
            # ``;``). They are dropped here; ``tree()`` enforces exactly one
            # real statement where that matters.
            self._statements = [stmt for stmt in parsed if stmt is not None]
        return self._statements

    def tree(self) -> exp.Expression:
        statements = self.statements()
        if len(statements) != 1:
            raise SqlRejected("Only a single SQL statement is allowed", code="multiple_statements")
        return statements[0]

    def replace_sql(self, sql: str) -> None:
        self.sql = sql
        self._statements = None


@runtime_checkable
class SqlCheck(Protocol):
    name: str
    # ``True``: also run on the rewritten SQL. Checks about what the *caller*
    # wrote (column permissions) set ``False`` because rewriters introduce
    # constructs (``SELECT *`` wrappers) the caller is not allowed to write.
    recheck: bool

    def check(self, ctx: GuardContext) -> None:
        """Raise ``SqlRejected`` when the SQL must not run."""


@runtime_checkable
class SqlRewriter(Protocol):
    name: str

    def rewrite(self, ctx: GuardContext) -> str:
        """Return the SQL to continue with (may be unchanged)."""


class GuardPipeline:
    """Runs all checks, then rewriters, then re-runs ``recheck`` checks."""

    def __init__(self, checks: Sequence[SqlCheck] = (), rewriters: Sequence[SqlRewriter] = ()):
        self.checks = tuple(checks)
        self.rewriters = tuple(rewriters)

    def extend(self, checks: Iterable[SqlCheck] = (), rewriters: Iterable[SqlRewriter] = ()) -> "GuardPipeline":
        """Return a new pipeline with extra rules appended (this one is unchanged)."""
        return GuardPipeline(self.checks + tuple(checks), self.rewriters + tuple(rewriters))

    @staticmethod
    def _run_checks(ctx: GuardContext, checks: Sequence[SqlCheck]) -> None:
        for rule in checks:
            try:
                rule.check(ctx)
            except SqlRejected:
                raise
            except Exception as e:
                raise SqlRejected(f"SQL check '{rule.name}' failed: {e}", code="check_error") from e

    def run(self, ctx: GuardContext) -> str:
        self._run_checks(ctx, self.checks)
        if not self.rewriters:
            return ctx.sql
        for rule in self.rewriters:
            try:
                new_sql = rule.rewrite(ctx)
            except SqlRejected:
                raise
            except Exception as e:
                raise SqlRejected(f"SQL rewrite '{rule.name}' failed: {e}", code="rewrite_error") from e
            if not new_sql:
                raise SqlRejected(f"SQL rewrite '{rule.name}' produced no SQL", code="rewrite_error")
            if new_sql != ctx.sql:
                ctx.replace_sql(new_sql)
        self._run_checks(ctx, [c for c in self.checks if getattr(c, "recheck", True)])
        return ctx.sql


def build_context(sql: str, ds_type: str | None, **kwargs) -> GuardContext:
    """Create a context; unknown datasource types are rejected (fail closed)."""
    try:
        policy = dialect_registry.get(ds_type)
    except ValueError as e:
        raise SqlRejected(str(e), code="unsupported_dialect") from e
    return GuardContext(sql=sql, policy=policy, **kwargs)
