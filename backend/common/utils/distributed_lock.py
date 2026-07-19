"""Distributed-lock abstraction for process-wide singleton tasks.

The current provider uses PostgreSQL advisory locks. Business callers use
``SingleWorkerGuard``, which delegates lock operations to ``DistributedLock``.
"""

import hashlib
from collections.abc import Callable
from enum import Enum, auto
from functools import wraps
from threading import Lock
from typing import ClassVar, Self

from sqlalchemy import func, select
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError

from common.core.db import engine
from common.utils.utils import SQLBotLogUtil


class LockStatus(Enum):
    """Process-local state of the single-worker lock acquisition attempt."""

    NOT_ATTEMPTED = auto()
    ACQUIRED = auto()
    NOT_ACQUIRED = auto()


class DistributedLock:
    """A lock held by this process until ``release`` or process shutdown."""

    def __init__(
        self,
        advisory_key: int,
        connection: Connection,
    ) -> None:
        self._connection = connection
        self._advisory_key = advisory_key

    @staticmethod
    def _postgres_advisory_key(key: str) -> int:
        """Convert a readable lock key into PostgreSQL's signed 64-bit key."""
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    @classmethod
    def try_acquire(cls, key: str) -> Self | None:
        """Try to acquire a named distributed lock without waiting."""
        advisory_key = cls._postgres_advisory_key(key)
        connection: Connection | None = None
        try:
            connection = engine.connect()
            acquired = connection.execute(
                select(func.pg_try_advisory_lock(advisory_key))
            ).scalar_one()
            # End the implicit transaction; the session-level lock remains held.
            connection.commit()
        except SQLAlchemyError:
            SQLBotLogUtil.exception("Failed to acquire distributed lock: %s", key)
            if connection is not None:
                connection.close()
            return None

        if not acquired:
            connection.close()
            return None

        return cls(advisory_key, connection)

    def release(self) -> None:
        """Release the lock and return its dedicated connection to the pool."""
        if self._connection.closed:
            return

        try:
            self._connection.execute(
                select(func.pg_advisory_unlock(self._advisory_key))
            )
            self._connection.commit()
        finally:
            self._connection.close()


class SingleWorkerGuard:
    """Run startup tasks in only one worker process."""

    _LOCK_KEY = "sqlbot:startup:embedding"
    _lock_status: ClassVar[LockStatus] = LockStatus.NOT_ATTEMPTED
    # Keep the acquired lock and its dedicated connection alive.
    _acquired_lock: ClassVar[DistributedLock | None] = None
    _state_mutex = Lock()

    @classmethod
    def _has_acquired_lock(cls) -> bool:
        with cls._state_mutex:
            if cls._lock_status is LockStatus.NOT_ATTEMPTED:
                lock = DistributedLock.try_acquire(cls._LOCK_KEY)
                if lock is None:
                    cls._lock_status = LockStatus.NOT_ACQUIRED
                    SQLBotLogUtil.info(
                        "Current process FAILED to acquire the single-worker lock"
                    )
                else:
                    cls._acquired_lock = lock
                    cls._lock_status = LockStatus.ACQUIRED
                    SQLBotLogUtil.info(
                        "Current process acquired the single-worker lock"
                    )
            return cls._lock_status is LockStatus.ACQUIRED

    @classmethod
    def once(cls, func: Callable[[], None]) -> Callable[[], None]:
        """Run the decorated startup task in only one worker."""

        @wraps(func)
        def wrapper() -> None:
            if not cls._has_acquired_lock():
                return
            func()

        return wrapper

    @classmethod
    def release(cls) -> None:
        """Release the single-worker lock and reset this process's state."""
        with cls._state_mutex:
            try:
                if cls._acquired_lock is not None:
                    cls._acquired_lock.release()
            finally:
                cls._acquired_lock = None
                cls._lock_status = LockStatus.NOT_ATTEMPTED
