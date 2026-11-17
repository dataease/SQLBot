"""Explicit disposable PostgreSQL tests of task-level question completion/recall."""

import json
import os
import re
from types import SimpleNamespace

import pytest
import test_embedding_parameters_integration as contracts
import test_table_parameters_integration as table_contracts
from langchain_core.messages import AIMessageChunk
from sqlmodel import Session, select

from apps.chat.curd.chat import get_chat_log_history
from apps.chat.models.chat_model import ChatLog
from apps.data_training.models.data_training_model import DataTraining

knowledge_environment = contracts.knowledge_environment
table_environment = table_contracts.table_environment
pytestmark = pytest.mark.skipif(
    os.environ.get("SQLBOT_RUN_EMBEDDING_INTEGRATION") != "1",
    reason="explicit disposable PostgreSQL integration opt-in required",
)


@pytest.mark.parametrize("outcome", ["completed", "invalid_output", "model_error"])
def test_completion_persists_model_process_and_counts_usage_once(
    table_environment, outcome
):
    database, client, ds_id = table_environment
    table_contracts.configure(
        client, enabled=False, table_enabled=False, keyword_enabled=False
    )
    current = table_contracts.task(database, ds_id, question="last year instead")
    current.chat_question.ai_modal_id = 123
    response = (
        json.dumps({"question": "sales for last year"})
        if outcome == "completed"
        else "partial output"
    )

    def stream(messages):
        if "【Schema】" in "\n".join(m.content for m in messages):
            yield AIMessageChunk(
                content=json.dumps(
                    {
                        "success": True,
                        "sql": "SELECT id FROM sales_alpha",
                        "tables": ["sales_alpha"],
                    }
                )
            )
            return
        yield AIMessageChunk(
            content=response,
            additional_kwargs={"reasoning_content": "controlled reasoning"},
            usage_metadata={
                "input_tokens": 25,
                "output_tokens": 15,
                "total_tokens": 40,
            },
        )
        if outcome == "model_error":
            raise RuntimeError("controlled stream failure")

    current.llm = SimpleNamespace(stream=stream)
    table_contracts.run(current)
    # Reusing completion must neither call the provider nor write another log.
    current.complete_question(None)
    with Session(database) as session:
        logs = session.exec(
            select(ChatLog).where(ChatLog.pid == current.record.id)
        ).all()
        completion_logs = [
            log for log in logs if log.operate.name == "COMPLETE_QUESTION"
        ]
        assert len(completion_logs) == 1
        log = completion_logs[0]
        assert log.ai_modal_id == 123
        assert log.base_modal == current.chat_question.ai_modal_name
        assert log.finish_time >= log.start_time
        assert not log.local_operation
        assert log.error == (outcome != "completed")
        assert log.reasoning_content == "controlled reasoning"
        assert log.token_usage["total_tokens"] == 40
        assert (
            json.loads(log.messages[1]["content"])["current"]["question"]
            == "last year instead"
        )
        assert log.messages[-1]["content"] == response
        assert log.messages[-1]["completion"] == {
            "reason": outcome,
            "question": "sales for last year"
            if outcome == "completed"
            else "last year instead",
        }
        history = get_chat_log_history(session, current.record.id, current.current_user)
        step = next(
            step for step in history.steps if step.operate == "COMPLETE_QUESTION"
        )
        assert step.total_tokens == 40
        assert step.error == log.error
        assert step.duration is not None
        assert history.total_tokens == 40
        assert (
            get_chat_log_history(
                session, current.record.id, current.current_user, True
            ).total_tokens
            == 40
        )
    assert current.chat_question.question == "last year instead"


@pytest.mark.parametrize("fence", [None, "json", ""])
def test_follow_up_recalls_complete_sql_example_without_replacing_original(
    table_environment,
    fence,
):
    database, client, ds_id = table_environment
    table_contracts.configure(
        client, enabled=False, table_enabled=False, keyword_enabled=False
    )
    completed = "去年按地区统计销售额，排除退款"
    with Session(database) as session:
        session.add(
            DataTraining(
                oid=1,
                datasource=ds_id,
                enabled=True,
                question=completed,
                description="SELECT region, SUM(amount) FROM sales WHERE year = 2025 AND NOT refunded GROUP BY region",
            )
        )
        session.commit()
        task = table_contracts.task(database, ds_id)
        task.chat_question.question = "那去年呢"
        task.generate_sql_logs = [
            SimpleNamespace(
                pid=7,
                messages=[
                    {
                        "type": "human",
                        "content": "<user-question>今年按地区统计销售额，排除退款</user-question>",
                    },
                    {"type": "ai", "content": "untrusted generated SQL"},
                ],
            )
        ]
        requests = []

        def stream(messages):
            requests.append(messages)
            if "【Schema】" in "\n".join(m.content for m in messages):
                yield AIMessageChunk(
                    content=json.dumps(
                        {
                            "success": True,
                            "sql": "SELECT id FROM sales_alpha",
                            "tables": ["sales_alpha"],
                        }
                    )
                )
                return
            response = json.dumps({"question": completed})
            if fence is not None:
                response = f"```{fence}\n{response}\n```"
            yield AIMessageChunk(
                content=response,
                usage_metadata={
                    "input_tokens": 25,
                    "output_tokens": 15,
                    "total_tokens": 40,
                },
            )

        task.llm = SimpleNamespace(stream=stream)
        table_contracts.run(task)
        assert completed in task.chat_question.data_training
        assert "SELECT region" in task.chat_question.data_training
        assert task.chat_question.question == "那去年呢"
        assert len(requests) == 2
        assert completed in "\n".join(m.content for m in requests[-1])
        assert re.search(
            r"<user-question>\s*那去年呢\s*</user-question>",
            "\n".join(m.content for m in requests[-1]),
        )
        assert json.loads(requests[0][-1].content) == {
            "history": [{"turn": 1, "question": "今年按地区统计销售额，排除退款"}],
            "current": {"turn": 2, "question": "那去年呢"},
        }


def test_overlong_completed_query_keeps_literal_example_without_vector_call(
    table_environment, monkeypatch, caplog
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache

    database, client, ds_id = table_environment
    table_contracts.configure(
        client, enabled=True, table_enabled=False, keyword_enabled=False
    )
    completed = "a a a a"
    with Session(database) as session:
        session.add(
            DataTraining(
                oid=1,
                datasource=ds_id,
                enabled=True,
                question=completed,
                description="SELECT id FROM sales_alpha",
            )
        )
        session.commit()
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: embedding_model(limit=5, calls=calls)
    )
    current = table_contracts.task(database, ds_id, question="follow up")

    def stream(messages):
        if "【Schema】" in "\n".join(m.content for m in messages):
            yield AIMessageChunk(
                content=json.dumps(
                    {
                        "success": True,
                        "sql": "SELECT id FROM sales_alpha",
                        "tables": ["sales_alpha"],
                    }
                )
            )
        else:
            yield AIMessageChunk(content=json.dumps({"question": completed}))

    current.llm = SimpleNamespace(stream=stream)
    table_contracts.run(current)
    assert completed in current.chat_question.data_training
    assert completed not in calls
    assert '"reason": "query_too_long"' in caplog.text


@pytest.mark.parametrize(
    "response,reason",
    [
        ("invalid JSON", "invalid_output"),
        (None, "model_error"),
        ('{"question": ""}', "invalid_output"),
        ('```json\n{"question": "wrong",}\n```', "invalid_output"),
        ('```json\n{"question": "wrong"}\n', "invalid_output"),
        ('```json\n{"question": "one"} {"question": "two"}\n```', "invalid_output"),
        ('```json\n{"outer": {"question": "wrong"},}\n```', "invalid_output"),
        ('```json\n[{"question": "wrong"}]\n```', "invalid_output"),
    ],
)
def test_failed_completion_falls_back_to_original_and_preserves_sql_flow(
    table_environment, response, reason, caplog
):
    database, client, ds_id = table_environment
    table_contracts.configure(
        client, enabled=False, table_enabled=False, keyword_enabled=False
    )
    with Session(database) as session:
        session.add(
            DataTraining(
                oid=1,
                datasource=ds_id,
                enabled=True,
                question="sales query",
                description="SELECT id FROM sales_alpha",
            )
        )
        session.commit()
    current = table_contracts.task(database, ds_id, question="sales query")

    def stream(messages):
        if "【Schema】" in "\n".join(m.content for m in messages):
            yield AIMessageChunk(
                content=json.dumps(
                    {
                        "success": True,
                        "sql": "SELECT id FROM sales_alpha",
                        "tables": ["sales_alpha"],
                    }
                )
            )
        elif response is None:
            raise RuntimeError("controlled model failure")
        else:
            yield AIMessageChunk(content=response)

    current.llm = SimpleNamespace(stream=stream)
    table_contracts.run(current)
    assert "sales query" in current.chat_question.data_training
    assert current.chat_question.question == "sales query"
    assert f'"reason": "{reason}"' in caplog.text


def test_regeneration_uses_its_own_history_and_new_task_result(table_environment):
    database, client, ds_id = table_environment
    table_contracts.configure(
        client, enabled=False, table_enabled=False, keyword_enabled=False
    )
    current = table_contracts.task(database, ds_id, question="那去年呢")
    current.chat_question.regenerate_record_id = 7
    current.generate_sql_logs = [
        SimpleNamespace(
            pid=7,
            messages=[
                {
                    "type": "human",
                    "content": "<user-question>今年按地区统计销售额，排除退款</user-question>",
                }
            ],
        ),
        SimpleNamespace(
            pid=8,
            messages=[
                {
                    "type": "human",
                    "content": "<user-question>切换到库存</user-question>",
                }
            ],
        ),
    ]
    requests = []

    def stream(messages):
        requests.append(list(messages))
        if "【Schema】" in "\n".join(m.content for m in messages):
            yield AIMessageChunk(
                content=json.dumps(
                    {
                        "success": True,
                        "sql": "SELECT id FROM sales_alpha",
                        "tables": ["sales_alpha"],
                    }
                )
            )
        else:
            yield AIMessageChunk(
                content=json.dumps({"question": "去年按地区统计销售额，排除退款"})
            )

    current.llm = SimpleNamespace(stream=stream)
    table_contracts.run(current)
    assert json.loads(requests[0][-1].content) == {
        "history": [{"turn": 1, "question": "今年按地区统计销售额，排除退款"}],
        "current": {"turn": 2, "question": "那去年呢"},
    }
    assert "切换到库存" not in "\n".join(m.content for m in requests[-1])
    # Reuse within a task never asks the model for a different interpretation.
    current.complete_question(None)
    assert len(requests) == 2
    following = table_contracts.task(database, ds_id, question="这次包含退款")
    following.llm = SimpleNamespace(stream=stream)
    table_contracts.run(following)
    assert len(requests) == 4
    assert json.loads(requests[2][-1].content) == {
        "history": [],
        "current": {"turn": 1, "question": "这次包含退款"},
    }


def test_successive_updates_reach_completion_in_order_and_preserve_sql_history(
    table_environment,
):
    database, client, ds_id = table_environment
    table_contracts.configure(
        client, enabled=False, table_enabled=False, keyword_enabled=False
    )
    history = ["今年按地区统计销售额，排除退款", "那去年呢", "这次包含退款"]
    completed = "去年按产品统计销售额，包含退款"
    current = table_contracts.task(database, ds_id, question="改为按产品统计")
    current.generate_sql_logs = [
        SimpleNamespace(
            pid=7,
            messages=[
                message
                for question in history
                for message in [
                    {
                        "type": "human",
                        "content": f"<user-question>{question}</user-question>",
                    },
                    {"type": "ai", "content": "SELECT id FROM sales_alpha"},
                ]
            ],
        )
    ]
    with Session(database) as session:
        session.add(
            DataTraining(
                oid=1,
                datasource=ds_id,
                enabled=True,
                question=completed,
                description="SELECT id FROM sales_alpha",
            )
        )
        session.commit()
    requests = []

    def stream(messages):
        requests.append(list(messages))
        if "【Schema】" in "\n".join(m.content for m in messages):
            yield AIMessageChunk(
                content=json.dumps(
                    {
                        "success": True,
                        "sql": "SELECT id FROM sales_alpha",
                        "tables": ["sales_alpha"],
                    }
                )
            )
        else:
            yield AIMessageChunk(
                content=json.dumps(
                    {
                        "history_intents": [
                            "今年按地区统计销售额，排除退款",
                            "去年按地区统计销售额，排除退款",
                            "去年按地区统计销售额，包含退款",
                        ],
                        "question": completed,
                    }
                )
            )

    current.llm = SimpleNamespace(stream=stream)
    table_contracts.run(current)
    payload = json.loads(requests[0][-1].content)
    assert payload == {
        "history": [
            {"turn": 1, "question": "今年按地区统计销售额，排除退款"},
            {"turn": 2, "question": "那去年呢"},
            {"turn": 3, "question": "这次包含退款"},
        ],
        "current": {"turn": 4, "question": "改为按产品统计"},
    }
    assert completed in current.chat_question.data_training
    assert current.chat_question.question == "改为按产品统计"
    sql_input = "\n".join(m.content for m in requests[-1])
    for question in [*history, "改为按产品统计"]:
        assert re.search(
            r"<user-question>\s*" + question + r"\s*</user-question>", sql_input
        )
    current.complete_question(None)
    assert len(requests) == 2
