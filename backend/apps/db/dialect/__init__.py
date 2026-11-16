"""Datasource dialect policies (sqlglot dialect, denylists, timeouts).

Importing this package registers the built-in policies.
"""

from apps.db.dialect import builtin  # noqa: F401  # register built-in policies
from apps.db.dialect.base import DialectPolicy, TimeoutApplier
from apps.db.dialect.registry import (
    DialectRegistry,
    UnsupportedDialectError,
    dialect_registry,
)

__all__ = [
    "DialectPolicy",
    "DialectRegistry",
    "TimeoutApplier",
    "UnsupportedDialectError",
    "dialect_registry",
]
