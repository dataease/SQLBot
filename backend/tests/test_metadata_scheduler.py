"""The metadata scheduling seam bounds backlog without blocking save callers."""

from threading import Event

from common.utils.metadata_scheduler import MetadataScheduler


def test_save_burst_coalesces_to_recovery_scan_without_blocking():
    entered, release = Event(), Event()
    completed = []

    def generate(tables, datasources, scan):
        if not completed:
            entered.set()
            assert release.wait(5)
        completed.append((tables, datasources, scan))

    scheduler = MetadataScheduler(generate, capacity=4)
    try:
        active = scheduler.submit("table", [1])
        assert entered.wait(5)
        pending = scheduler.submit("table", [2])
        for index in range(3, 1003):
            assert scheduler.submit("table", [index]) is pending
        assert not pending.done()
        release.set()
        active.result(5)
        pending.result(5)
        assert completed == [([1], [], False), ([], [], True)]
    finally:
        release.set()
        scheduler.shutdown()


def test_failed_batch_reports_error_and_later_edits_still_run():
    import pytest

    entered, release = Event(), Event()
    calls = []

    def generate(tables, _datasources, _scan):
        calls.append(tables)
        if len(calls) == 1:
            entered.set()
            assert release.wait(5)
            raise ValueError("provider failed")

    scheduler = MetadataScheduler(generate)
    try:
        first = scheduler.submit("table", [1])
        assert entered.wait(5)
        later = scheduler.submit("table", [1])
        release.set()
        with pytest.raises(ValueError, match="provider failed"):
            first.result(5)
        later.result(5)
        assert calls == [[1], [1]]
    finally:
        release.set()
        scheduler.shutdown()
    with pytest.raises(RuntimeError, match="shutdown"):
        scheduler.submit()
