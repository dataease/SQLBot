"""Per-datasource SQL dialect policy.

A policy describes how SQLBot parses, guards and bounds SQL for one datasource
type. New datasource types are supported by registering a new policy (see
``registry.py``); guard and execution code only depends on this interface.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# Applies a per-statement execution timeout on an open SQLAlchemy connection
# that is about to run one query. Returns an optional ``restore`` callable that
# undoes any session-level change before the connection goes back to the pool;
# appliers that only affect the current transaction return ``None``.
TimeoutApplier = Callable[[Any, int], Callable[[], None] | None]


@dataclass(frozen=True)
class DialectPolicy:
    # Datasource type code, must equal ``DB.<member>.type`` (case-insensitive).
    ds_type: str
    # sqlglot dialect used by the shared read-only check (``check_sql_read``).
    # ``None`` is sqlglot's generic dialect. Kept as-is for compatibility:
    # changing it changes how existing web-flow SQL is parsed.
    sqlglot_dialect: str | None = None
    # Precise sqlglot dialect used to parse and *render* SQL that SQLBot
    # rewrites (strict profile). ``None`` falls back to ``sqlglot_dialect``.
    precise_dialect: str | None = None
    # Extra dangerous functions (case-insensitive names) on top of the common set.
    dangerous_functions: frozenset[str] = field(default_factory=frozenset)
    # Functions that can stall or exhaust the database (sleep, benchmark...).
    # Enforced by strict guard profiles only.
    resource_functions: frozenset[str] = field(default_factory=frozenset)
    # Whether the strict guard (external agent SQL) supports this datasource.
    agent_supported: bool = True
    # Whether a row cap may be added by rewriting the SQL (LIMIT/TOP/FETCH).
    # When ``False`` the cap is enforced only while fetching rows.
    limit_rewrite: bool = True
    # How to apply a per-statement timeout; ``None`` means "not supported".
    apply_timeout: TimeoutApplier | None = None

    def key(self) -> str:
        return self.ds_type.lower()

    @property
    def strict_dialect(self) -> str | None:
        return self.precise_dialect or self.sqlglot_dialect
