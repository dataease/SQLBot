"""Offline task regressions with model, persistence and database I/O replaced."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before app imports.
from pydantic import ValidationError

from apps.chat.models.chat_model import ChatFinishStep
from apps.chat.task import llm
from common.core.config import Settings


@pytest.mark.parametrize(
    "value,expected",
    [(None, False), ("false", False), ("true", True), (" TRUE ", True)],
)
def test_startup_configuration(monkeypatch, value, expected):
    monkeypatch.delenv("SQLBOT_SKIP_TABLE_CHECK", raising=False)
    if value is not None:
        monkeypatch.setenv("SQLBOT_SKIP_TABLE_CHECK", value)
    config = Settings(_env_file=None)
    assert config.SQLBOT_SKIP_TABLE_CHECK is expected
    monkeypatch.setenv("SQLBOT_SKIP_TABLE_CHECK", str(not expected))
    assert config.SQLBOT_SKIP_TABLE_CHECK is expected


def test_invalid_startup_configuration_is_rejected(monkeypatch):
    monkeypatch.setenv("SQLBOT_SKIP_TABLE_CHECK", "invalid")
    with pytest.raises(ValidationError, match="SQLBOT_SKIP_TABLE_CHECK"):
        Settings(_env_file=None)


@pytest.fixture
def task(monkeypatch):
    monkeypatch.setattr(llm.settings, "SQLBOT_SKIP_TABLE_CHECK", False)
    monkeypatch.setattr(llm, "session_maker", Mock())
    monkeypatch.setattr(llm, "check_connection", Mock(return_value=True))
    monkeypatch.setattr(llm, "start_log", Mock())
    monkeypatch.setattr(llm, "end_log", Mock())
    monkeypatch.setattr(llm, "get_chat_chart_data", Mock(return_value=[]))
    service = Mock(spec=llm.LLMService)
    service.ds = SimpleNamespace(id=1, type="pg")
    service.chat_question = SimpleNamespace(question="sales")
    service.record = SimpleNamespace(id=1)
    service.get_record.return_value = service.record
    service.current_user = SimpleNamespace(id=2, isAdmin=False, weight=0)
    service.current_assistant = None
    service.change_title = False
    service.table_name_list = ["sales"]
    service.current_logs = {}
    service.generate_sql.return_value = [{"content": "{}"}]
    service.generate_filter.return_value = None
    service.execute_sql.return_value = {"data": []}
    return service


def run(task, sql, reported_tables=None):
    # Model-reported tables are deliberately independent of the real SQL.
    task.check_sql.return_value = sql, reported_tables or ["sales"]
    task.check_save_sql.return_value = sql
    results = list(
        llm.LLMService.run_task(
            task, in_chat=False, stream=False, finish_step=ChatFinishStep.QUERY_DATA
        )
    )
    assert len(results) == 1
    return results[0]


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id FROM sales",
        "WITH totals AS (SELECT id FROM sales) SELECT * FROM totals",
    ],
)
def test_default_allows_known_tables_and_cte_aliases(task, sql):
    result = run(task, sql)
    assert result["success"] is True
    task.execute_sql.assert_called_once_with(sql=sql)
    task.check_save_sql.assert_called_once()
    task.save_error.assert_not_called()


@pytest.mark.parametrize(
    "sql,error",
    [
        ("SELECT * FROM secret_payroll", "unauthorized tables: secret_payroll"),
        (
            "SELECT id FROM sales UNION ALL SELECT id FROM secret_payroll",
            "unauthorized tables: secret_payroll",
        ),
        ("SELECT 1", "unable to extract table names"),
        ("SELECT (", "unable to extract table names"),
    ],
)
def test_default_rejects_invalid_or_unknown_tables_before_save_and_execute(
    task, sql, error
):
    result = run(task, sql, reported_tables=["sales"])
    assert result["success"] is False
    assert error in result["message"]
    task.save_error.assert_called_once()
    task.check_save_sql.assert_not_called()
    task.execute_sql.assert_not_called()


@pytest.mark.parametrize("sql", ["SELECT * FROM secret_payroll", "SELECT 1"])
def test_explicit_skip_bypasses_extraction_and_keeps_remaining_flow(
    task, monkeypatch, sql
):
    monkeypatch.setattr(llm.settings, "SQLBOT_SKIP_TABLE_CHECK", True)
    extract = Mock(side_effect=AssertionError("table extraction must be skipped"))
    monkeypatch.setattr(llm, "extract_tables_from_sql", extract)
    result = run(task, sql)
    assert result["success"] is True
    extract.assert_not_called()
    task.generate_filter.assert_called_once()
    task.check_save_sql.assert_called_once()
    task.execute_sql.assert_called_once_with(sql=sql)
    task.save_error.assert_not_called()


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM sales",
        "SELECT pg_read_file('/etc/passwd')",
        "SHOW TABLES",
    ],
)
def test_skip_keeps_database_execution_guards(task, monkeypatch, sql):
    from apps.db import db

    monkeypatch.setattr(llm.settings, "SQLBOT_SKIP_TABLE_CHECK", True)
    monkeypatch.setattr(llm.settings, "SQLBOT_ALLOW_METADATA_QUERIES", False)
    connect = Mock(side_effect=AssertionError("database must not be contacted"))
    monkeypatch.setattr(db, "get_session", connect)
    task.execute_sql.side_effect = lambda sql: llm.LLMService.execute_sql(task, sql)
    result = run(task, sql)
    assert result["success"] is False
    assert "SQL can only contain read operations" in result["message"]
    task.execute_sql.assert_called_once_with(sql=sql)
    connect.assert_not_called()
