"""Read-only checks shared by every SQL execution path.

These rules keep the behaviour ``check_sql_read`` had before it was split into
a pipeline. Each rule is independent so profiles can reuse or extend them.
"""

import re
from collections.abc import Iterable

from sqlglot import expressions as exp

from apps.db.sql_guard.base import GuardContext, SqlRejected

# Applies to every datasource type, on top of ``DialectPolicy.dangerous_functions``.
COMMON_DANGEROUS_FUNCTIONS = frozenset({"version", "current_user", "user", "database"})

DANGEROUS_PATTERNS = (
    r"\bINTO\s+OUTFILE\b",
    r"\bINTO\s+DUMPFILE\b",
    r"\bEXEC\s*\(",
    r"\bCOPY\s+.*\bTO\s+PROGRAM\b",
)

READ_COMMANDS = frozenset({"SELECT", "WITH"})
METADATA_COMMANDS = frozenset({"SHOW", "DESCRIBE", "DESC", "EXPLAIN"})
DENIED_COMMANDS = frozenset({
    "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER",
    "TRUNCATE", "MERGE", "COPY", "REPLACE", "GRANT", "REVOKE",
    "USE", "SET", "CALL",
})
WRITE_STATEMENT_TYPES = (
    exp.Insert, exp.Update, exp.Delete,
    exp.Create, exp.Drop, exp.Alter,
    exp.Merge, exp.Copy,
)


def first_keyword(sql: str) -> str:
    normalized = sql.strip().lstrip("(").strip()
    return normalized.split(None, 1)[0].upper() if normalized else ""


def dangerous_functions_for(ctx: GuardContext) -> frozenset[str]:
    return COMMON_DANGEROUS_FUNCTIONS | ctx.policy.dangerous_functions


class LeadingKeywordCheck:
    """Reject empty SQL and SQL that starts with a write/admin keyword."""

    name = "leading_keyword"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        keyword = first_keyword(ctx.sql)
        if not keyword:
            raise SqlRejected("Parse SQL Error", code="parse_error")
        if keyword in DENIED_COMMANDS:
            raise SqlRejected(f"Write operation '{keyword}' is not allowed", code="write_operation")


class DangerousPatternCheck:
    name = "dangerous_pattern"
    recheck = True

    def __init__(self, patterns: Iterable[str] = DANGEROUS_PATTERNS):
        self.patterns = tuple(patterns)

    def check(self, ctx: GuardContext) -> None:
        for pattern in self.patterns:
            if re.search(pattern, ctx.sql, re.IGNORECASE):
                raise SqlRejected(f"SQL contains dangerous pattern: {pattern}", code="dangerous_pattern")


class AnonymousFunctionCheck:
    """Reject denylisted functions that sqlglot parses as ``Anonymous`` calls."""

    name = "anonymous_function"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        denied = {f.upper() for f in dangerous_functions_for(ctx)}
        for stmt in ctx.statements():
            for func in stmt.find_all(exp.Anonymous):
                if func.name.upper() in denied:
                    raise SqlRejected(f"SQL contains dangerous function: {func.name}", code="dangerous_function")


class WriteStatementCheck:
    name = "write_statement"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        for stmt in ctx.statements():
            if isinstance(stmt, WRITE_STATEMENT_TYPES):
                raise SqlRejected(f"SQL contains write operation: {type(stmt).__name__}", code="write_operation")


class ReadCommandCheck:
    name = "read_command"
    recheck = True

    def check(self, ctx: GuardContext) -> None:
        allowed = READ_COMMANDS | (METADATA_COMMANDS if ctx.allow_metadata_queries else frozenset())
        keyword = first_keyword(ctx.sql)
        if keyword not in allowed:
            raise SqlRejected(
                f"SQL command '{keyword}' is not allowed. Only SELECT and WITH are permitted",
                code="command_not_allowed",
            )


def basic_checks() -> list:
    """Order matches the legacy ``check_sql_read`` so reasons stay the same."""
    return [
        LeadingKeywordCheck(),
        DangerousPatternCheck(),
        AnonymousFunctionCheck(),
        WriteStatementCheck(),
        ReadCommandCheck(),
    ]
