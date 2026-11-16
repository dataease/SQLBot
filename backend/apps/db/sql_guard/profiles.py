"""Named guard profiles.

``basic`` is what every SQL execution path enforces (``check_sql_read``).
``agent`` is used for SQL written by an external caller: basic checks, strict
checks, then row permissions and a row cap.

Register a new profile (or extend one) with ``register_profile``; callers pick
profiles by name so they never assemble rules themselves.
"""

import threading
from collections.abc import Callable

from apps.db.sql_guard.base import GuardPipeline
from apps.db.sql_guard.basic import basic_checks
from apps.db.sql_guard.rewriters import RowLimitRewriter, RowPermissionRewriter
from apps.db.sql_guard.strict import strict_checks

PipelineFactory = Callable[[], GuardPipeline]

BASIC = "basic"
AGENT = "agent"

_profiles: dict[str, PipelineFactory] = {}
_lock = threading.Lock()


def register_profile(name: str, factory: PipelineFactory, *, replace: bool = False) -> None:
    with _lock:
        if name in _profiles and not replace:
            raise ValueError(f"Guard profile already registered: {name}")
        _profiles[name] = factory


def get_pipeline(name: str) -> GuardPipeline:
    factory = _profiles.get(name)
    if factory is None:
        raise ValueError(f"Unknown guard profile: {name}")
    return factory()


def _basic() -> GuardPipeline:
    return GuardPipeline(basic_checks())


def _agent() -> GuardPipeline:
    # Callers must build the context with ``strict=True`` so SQL is parsed and
    # re-rendered with the datasource's precise dialect.
    return GuardPipeline(
        basic_checks() + strict_checks(),
        rewriters=[RowPermissionRewriter(), RowLimitRewriter()],
    )


register_profile(BASIC, _basic)
register_profile(AGENT, _agent)
