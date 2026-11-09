"""Bounded, coalescing metadata work; persisted validity is the recovery ledger."""

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from threading import Lock


class MetadataScheduler:
    """One active batch and one pending batch, never one queued job per save.

    Overflow becomes a full paged scan. Requests received during a running scan
    remain pending, so an edit to an already scanned resource is not lost.
    Futures report completion of their coalesced batch, including its failures.
    """

    def __init__(
        self,
        generate: Callable[[list[int], list[int], bool], None],
        capacity: int = 128,
        executor=None,
    ):
        self._generate = generate
        self._capacity = capacity
        self._executor = executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="metadata-embedding"
        )
        self._lock = Lock()
        self._pending: Future | None = None
        self._ids: dict[str, set[int]] = {"table": set(), "datasource": set()}
        self._scan = False
        self._running = False
        self._closed = False

    def submit(self, resource: str | None = None, ids=()) -> Future:
        with self._lock:
            if self._closed:
                raise RuntimeError("cannot schedule new futures after shutdown")
            if resource not in (None, "table", "datasource"):
                raise ValueError("Unknown metadata resource")
            if self._pending is None:
                self._pending = Future()
                # A shared completion must not be cancellable by one caller.
                self._pending.set_running_or_notify_cancel()
            if resource is None:
                self._scan = True
            elif not self._scan:
                for key in ids:
                    self._ids[resource].add(key)
                    if sum(map(len, self._ids.values())) > self._capacity:
                        self._scan = True
                        break
            if self._scan:
                for keys in self._ids.values():
                    keys.clear()
            future = self._pending
            if not self._running:
                self._running = True
                self._executor.submit(self._drain)
            return future

    def _drain(self):
        while True:
            with self._lock:
                if self._pending is None:
                    self._running = False
                    return
                future, self._pending = self._pending, None
                tables = sorted(self._ids["table"])
                datasources = sorted(self._ids["datasource"])
                scan, self._scan = self._scan, False
                for keys in self._ids.values():
                    keys.clear()
            try:
                self._generate(tables, datasources, scan)
            except Exception as exc:
                future.set_exception(exc)
            else:
                future.set_result(None)

    def shutdown(self, wait: bool = True):
        with self._lock:
            self._closed = True
        self._executor.shutdown(wait=wait)
