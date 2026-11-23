"""Offline task regressions with model, persistence and database I/O replaced."""

from types import SimpleNamespace
from unittest.mock import Mock

import orjson
import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before app imports.
from pydantic import ValidationError

from apps.chat.curd.chat import format_record
from apps.chat.models.chat_model import ChatFinishStep, ChatRecordResult
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
    service.chat_question = SimpleNamespace(question="sales", selected_clarification=None)
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
    "request_text,question,options",
    [
        ("Which product sells best?", "Which metric should determine rank?", ["Units sold", "Paid amount"]),
        ("Count October support tickets", "Which ticket date defines October?", ["Created date", "Closed date"]),
        ("Count workers by department", "Which workers should be included?", ["Employees", "Contractors", "Everyone"]),
        ("Group shipments by region", "Which region should be used?", ["Origin region", "Destination region"]),
    ],
)
def test_clarification_pauses_before_sql_validation_and_execution(task, monkeypatch, request_text, question, options):
    task.record.question = request_text
    clarification = {"question": question, "options": options}
    task.record.regenerate_record_id = None
    task.generate_sql.return_value = [
        {"content": orjson.dumps({"success": False, "clarification": clarification}).decode()}
    ]
    save_answer = Mock(return_value=task.record)
    monkeypatch.setattr(llm, "save_sql_answer", save_answer)

    events = list(llm.LLMService.run_task(task))

    assert orjson.loads(events[-1].removeprefix("data:")) == {
        "type": "clarification", "content": clarification
    }
    stored = ChatRecordResult(sql_answer=save_answer.call_args.kwargs["answer"])
    assert format_record(stored)["clarification"] == clarification
    task.check_sql.assert_not_called()
    task.execute_sql.assert_not_called()
    task.finish.assert_called_once()


@pytest.mark.parametrize("verdict,executed", [('{"matches":true}', True), ('{"matches":false}', False), ('unknown', False)])
def test_selected_clarification_validates_final_sql_before_execution(task, verdict, executed):
    date_field = "closed_at" if executed else "created_at"
    generated_sql = f"SELECT COUNT(*) FROM sales WHERE {date_field} IS NOT NULL"
    final_sql = generated_sql + " AND tenant_id = 1"
    task.record.question = "Count records by closed date"
    task.record.regenerate_record_id = None
    task.chat_question.question = task.record.question
    task.chat_question.db_schema = "sales(created_at, closed_at, tenant_id)"
    task.chat_question.selected_clarification = "By closed date"
    task.check_sql.return_value = generated_sql, ["sales"]
    task.check_save_sql.return_value = final_sql
    task.llm = SimpleNamespace(invoke=Mock(return_value=SimpleNamespace(content=verdict)))
    task.trans = lambda key: key
    task.verify_sql_clarification.side_effect = (
        lambda sql, selection: llm.LLMService.verify_sql_clarification(task, sql, selection)
    )

    events = list(llm.LLMService.run_task(task, finish_step=ChatFinishStep.QUERY_DATA))

    task.verify_sql_clarification.assert_called_once_with(final_sql, "By closed date")
    payload = orjson.loads(task.llm.invoke.call_args.args[0][1].content)
    assert payload["sql"] == final_sql
    assert payload["selection"] == "By closed date"
    if executed:
        task.execute_sql.assert_called_once_with(sql=final_sql)
    else:
        task.execute_sql.assert_not_called()
        assert orjson.loads(events[-1].removeprefix("data:"))["type"] == "error"


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


@pytest.mark.parametrize("skip", [False, True])
@pytest.mark.parametrize("sql", ["SELECT 1", "SELECT ("])
def test_missing_tables_are_rejected_even_when_whitelist_check_is_skipped(
    task, monkeypatch, sql, skip
):
    monkeypatch.setattr(llm.settings, "SQLBOT_SKIP_TABLE_CHECK", skip)
    result = run(task, sql)
    assert result["success"] is False
    assert "unable to extract table names" in result["message"]
    task.save_error.assert_called_once()
    task.generate_filter.assert_not_called()
    task.check_save_sql.assert_not_called()
    task.execute_sql.assert_not_called()


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM secret_payroll",
        "SELECT id FROM sales UNION ALL SELECT id FROM secret_payroll",
    ],
)
def test_explicit_skip_only_bypasses_whitelist_check_and_keeps_remaining_flow(
    task, monkeypatch, sql
):
    monkeypatch.setattr(llm.settings, "SQLBOT_SKIP_TABLE_CHECK", True)
    extract = Mock(wraps=llm.extract_tables_from_sql)
    monkeypatch.setattr(llm, "extract_tables_from_sql", extract)
    result = run(task, sql)
    assert result["success"] is True
    extract.assert_called_once_with(sql, ds_type="pg")
    task.generate_filter.assert_called_once()
    task.check_save_sql.assert_called_once()
    task.execute_sql.assert_called_once_with(sql=sql)
    task.save_error.assert_not_called()


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM sales",
        "SELECT pg_read_file('/etc/passwd') FROM sales",
        "DESCRIBE sales",
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
