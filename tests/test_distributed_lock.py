"""Focused tests for the startup embedding distributed lock."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError


BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from common.utils import distributed_lock as lock_module  # noqa: E402
from common.utils.distributed_lock import (  # noqa: E402
    DistributedLock,
    LockStatus,
    SingleWorkerGuard,
)


class DistributedLockTestCase(unittest.TestCase):
    """Verify PostgreSQL advisory-lock acquisition and cleanup behavior."""

    @staticmethod
    def _connection(acquired: bool = True) -> MagicMock:
        connection = MagicMock(spec=Connection)
        connection.closed = False
        connection.execute.return_value.scalar_one.return_value = acquired
        return connection

    def test_advisory_key_is_stable_across_processes(self) -> None:
        key = DistributedLock._postgres_advisory_key("sqlbot:startup:embedding")

        self.assertEqual(6735965423478359195, key)
        self.assertGreaterEqual(key, -(2**63))
        self.assertLessEqual(key, 2**63 - 1)

    def test_try_acquire_keeps_successful_connection_open(self) -> None:
        connection = self._connection(acquired=True)

        with patch.object(lock_module, "engine") as engine:
            engine.connect.return_value = connection

            acquired_lock = DistributedLock.try_acquire("startup-task")

        self.assertIsInstance(acquired_lock, DistributedLock)
        connection.commit.assert_called_once_with()
        connection.close.assert_not_called()

    def test_try_acquire_closes_connection_when_lock_is_busy(self) -> None:
        connection = self._connection(acquired=False)

        with patch.object(lock_module, "engine") as engine:
            engine.connect.return_value = connection

            acquired_lock = DistributedLock.try_acquire("startup-task")

        self.assertIsNone(acquired_lock)
        connection.commit.assert_called_once_with()
        connection.close.assert_called_once_with()

    def test_try_acquire_closes_connection_on_sqlalchemy_error(self) -> None:
        connection = self._connection()
        connection.execute.side_effect = SQLAlchemyError("database error")

        with (
            patch.object(lock_module, "engine") as engine,
            patch.object(lock_module.SQLBotLogUtil, "exception") as log_error,
        ):
            engine.connect.return_value = connection

            acquired_lock = DistributedLock.try_acquire("startup-task")

        self.assertIsNone(acquired_lock)
        connection.close.assert_called_once_with()
        log_error.assert_called_once()

    def test_release_unlocks_commits_and_closes_connection(self) -> None:
        connection = self._connection()
        acquired_lock = DistributedLock(1234, connection)

        acquired_lock.release()

        connection.execute.assert_called_once()
        connection.commit.assert_called_once_with()
        connection.close.assert_called_once_with()

    def test_release_still_closes_connection_when_unlock_fails(self) -> None:
        connection = self._connection()
        connection.execute.side_effect = SQLAlchemyError("unlock error")
        acquired_lock = DistributedLock(1234, connection)

        with self.assertRaises(SQLAlchemyError):
            acquired_lock.release()

        connection.commit.assert_not_called()
        connection.close.assert_called_once_with()


class SingleWorkerGuardTestCase(unittest.TestCase):
    """Verify that only the process holding the lock runs startup tasks."""

    def setUp(self) -> None:
        SingleWorkerGuard._lock_status = LockStatus.NOT_ATTEMPTED
        SingleWorkerGuard._acquired_lock = None

    def tearDown(self) -> None:
        SingleWorkerGuard._lock_status = LockStatus.NOT_ATTEMPTED
        SingleWorkerGuard._acquired_lock = None

    def test_acquired_worker_runs_all_tasks_with_one_lock_attempt(self) -> None:
        acquired_lock = MagicMock(spec=DistributedLock)
        executed_tasks: list[str] = []

        @SingleWorkerGuard.once
        def first_task() -> None:
            executed_tasks.append("first")

        @SingleWorkerGuard.once
        def second_task() -> None:
            executed_tasks.append("second")

        with patch.object(
            DistributedLock,
            "try_acquire",
            return_value=acquired_lock,
        ) as try_acquire:
            first_task()
            second_task()

        self.assertEqual(["first", "second"], executed_tasks)
        try_acquire.assert_called_once_with(SingleWorkerGuard._LOCK_KEY)

    def test_non_acquired_worker_skips_tasks_without_retrying(self) -> None:
        task = MagicMock()
        guarded_task = SingleWorkerGuard.once(task)

        with (
            patch.object(
                DistributedLock,
                "try_acquire",
                return_value=None,
            ) as try_acquire,
            patch.object(lock_module.SQLBotLogUtil, "info"),
        ):
            guarded_task()
            guarded_task()

        task.assert_not_called()
        try_acquire.assert_called_once_with(SingleWorkerGuard._LOCK_KEY)

    def test_release_releases_lock_and_resets_process_state(self) -> None:
        acquired_lock = MagicMock(spec=DistributedLock)
        SingleWorkerGuard._lock_status = LockStatus.ACQUIRED
        SingleWorkerGuard._acquired_lock = acquired_lock

        SingleWorkerGuard.release()

        acquired_lock.release.assert_called_once_with()
        self.assertIsNone(SingleWorkerGuard._acquired_lock)
        self.assertIs(
            LockStatus.NOT_ATTEMPTED,
            SingleWorkerGuard._lock_status,
        )


if __name__ == "__main__":
    unittest.main()
