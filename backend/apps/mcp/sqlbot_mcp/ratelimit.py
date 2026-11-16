"""Per-credential rate limiting for SQLBot MCP tools.

``RateLimiter`` is a protocol so a shared backend (e.g. Redis) can replace the
in-process implementation when running several workers.
"""

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Protocol


class RateLimited(Exception):
    pass


class Slot(Protocol):
    def release(self) -> None: ...


class RateLimiter(Protocol):
    def acquire(self, kind: str, key: str, *, heavy: bool = False) -> Slot:
        """Reserve one call (and a concurrency slot when ``heavy``) or raise ``RateLimited``."""


class _NoopSlot:
    def release(self) -> None:
        return None


@dataclass
class _Bucket:
    calls: deque
    running: int = 0


class InMemoryRateLimiter:
    """Sliding one-minute window per credential plus a cap on concurrent heavy calls."""

    def __init__(self, per_minute: int = 60, max_concurrent_heavy: int = 2, *, enabled: bool = True,
                 clock=time.monotonic):
        self.per_minute = per_minute
        self.max_concurrent_heavy = max_concurrent_heavy
        self.enabled = enabled
        self._clock = clock
        self._buckets: dict[tuple[str, str], _Bucket] = {}
        self._lock = threading.Lock()

    def acquire(self, kind: str, key: str, *, heavy: bool = False) -> Slot:
        if not self.enabled:
            return _NoopSlot()
        now = self._clock()
        with self._lock:
            bucket = self._buckets.setdefault((kind, key), _Bucket(deque()))
            while bucket.calls and now - bucket.calls[0] >= 60:
                bucket.calls.popleft()
            if len(bucket.calls) >= self.per_minute:
                raise RateLimited("Rate limit exceeded, retry later")
            if heavy and bucket.running >= self.max_concurrent_heavy:
                raise RateLimited("Too many queries running for this token, retry later")
            bucket.calls.append(now)
            if heavy:
                bucket.running += 1
        return _HeavySlot(self, bucket) if heavy else _NoopSlot()

    def _release(self, bucket: _Bucket) -> None:
        with self._lock:
            bucket.running = max(0, bucket.running - 1)


class _HeavySlot:
    def __init__(self, limiter: InMemoryRateLimiter, bucket: _Bucket):
        self._limiter = limiter
        self._bucket = bucket
        self._released = False

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._limiter._release(self._bucket)
