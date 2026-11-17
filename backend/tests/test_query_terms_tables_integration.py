# ruff: noqa: F811
"""Opt-in PostgreSQL contracts for completed terminology and table retrieval."""

import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessageChunk
from sqlmodel import Session
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)
from test_table_parameters_integration import (  # noqa: F401
    configure,
    run,
    table_environment,
    task,
)

from apps.terminology.models.terminology_model import Terminology


class CompletedQuestionProvider:
    def __init__(self, completed, keywords="sales", sql_table="sales_alpha"):
        self.sql_table = sql_table
        self.completed = completed
        self.keywords = keywords
        self.requests = []

    def stream(self, messages):
        self.requests.append(list(messages))
        context = "\n".join(message.content for message in messages)
        if messages[0].content.startswith("Complete the current data question"):
            content = json.dumps({"question": self.completed})
        elif "【Schema】" in context:
            content = json.dumps(
                {
                    "success": True,
                    "sql": f"SELECT id FROM {self.sql_table}",
                    "tables": [self.sql_table],
                }
            )
        else:
            content = self.keywords
        yield AIMessageChunk(content=content)


def test_completed_intent_drives_terms_without_reintroducing_revoked_history(
    table_environment,
):
    database, client, ds_id = table_environment
    configure(client, enabled=False, table_enabled=False, keyword_enabled=True)
    with Session(database) as session:
        session.add(
            Terminology(
                oid=1, word="sales", description="Current sales business meaning"
            )
        )
        session.commit()
    current = task(database, ds_id, question="include refunds and use sales_alpha")
    current.generate_sql_logs = [
        SimpleNamespace(
            pid=7,
            messages=[
                {
                    "type": "human",
                    "content": "<user-question>sales excluding refunds by region</user-question>",
                }
            ],
        )
    ]
    completed = "sales including refunds by region using sales_alpha"
    current.llm = CompletedQuestionProvider(completed, "sales,refunds,region")
    schema = run(current)
    assert "sales_alpha" in schema
    assert "Current sales business meaning" in current.chat_question.terminologies
    assert [m.content for m in current.llm.requests[1][1:]] == [completed]
    assert len(current.llm.requests) == 3
    assert current.chat_question.question == "include refunds and use sales_alpha"
    assert "excluding refunds" in "\n".join(m.content for m in current.llm.requests[-1])


def test_keyword_disabled_uses_completed_intent_and_keeps_original_table_mentions(
    table_environment, monkeypatch
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache

    database, client, ds_id = table_environment
    configure(
        client, enabled=False, table_enabled=True, keyword_enabled=False, table_count=1
    )
    with Session(database) as session:
        session.add(
            Terminology(oid=1, word="revenue", description="Completed business meaning")
        )
        session.commit()
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: embedding_model(limit=100, calls=calls),
    )
    current = task(database, ds_id, question="and sales_alpha?")
    current.llm = CompletedQuestionProvider("revenue by region")
    schema = run(current)
    assert calls == ["revenue by region"]
    assert "Completed business meaning" in current.chat_question.terminologies
    assert "sales_alpha" in schema and "vector_beta" not in schema
    assert not current.chat_question.extracted_keywords
    assert len(current.llm.requests) == 2


def test_overlong_business_word_preserves_literal_terminology(
    table_environment, monkeypatch, caplog
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache

    database, client, ds_id = table_environment
    configure(client, enabled=True, table_enabled=False, keyword_enabled=True)
    word = "sales customer region revenue"
    with Session(database) as session:
        session.add(
            Terminology(
                oid=1,
                word=word,
                description="Literal long business term",
                embedding=[0, 1],
            )
        )
        session.commit()
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: embedding_model(limit=5, calls=calls)
    )
    current = task(database, ds_id, question="follow up")
    current.llm = CompletedQuestionProvider("sales", word)
    run(current)
    assert "Literal long business term" in current.chat_question.terminologies
    assert word not in calls
    assert '"stage": "terminology"' in caplog.text
    assert '"reason": "query_too_long"' in caplog.text


def test_expanded_table_query_is_checked_after_synonyms_and_preserves_allowed_candidates(
    table_environment, monkeypatch
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache

    database, client, ds_id = table_environment
    configure(
        client, enabled=False, table_enabled=True, keyword_enabled=True, table_count=1
    )
    with Session(database) as session:
        term = Terminology(oid=1, word="sales", description="Sales meaning")
        session.add(term)
        session.flush()
        session.add(
            Terminology(oid=1, pid=term.id, word="revenue region customer refund")
        )
        session.commit()
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: embedding_model(limit=5, calls=calls)
    )
    current = task(database, ds_id, question="sales_alpha and hidden_table")
    current.llm = CompletedQuestionProvider("sales")
    schema = run(current)
    assert (
        current.chat_question.expanded_keywords
        == "sales,revenue region customer refund"
    )
    assert calls == []
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    assert "hidden_table" not in schema


def add_synonym(session, synonym, **scope):
    term = Terminology(word="sales", description=synonym + " meaning", **scope)
    session.add(term)
    session.flush()
    session.add(Terminology(pid=term.id, word=synonym, **scope))


def test_synonym_expansion_obeys_current_datasource_knowledge_scope(table_environment):
    database, client, ds_id = table_environment
    configure(client, enabled=False, table_enabled=False, keyword_enabled=True)
    with Session(database) as session:
        add_synonym(session, "workspace_revenue", oid=1)
        add_synonym(
            session, "source_revenue", oid=1, specific_ds=True, datasource_ids=[ds_id]
        )
        add_synonym(
            session,
            "other_source_revenue",
            oid=1,
            specific_ds=True,
            datasource_ids=[ds_id + 100],
        )
        add_synonym(
            session,
            "application_revenue",
            oid=1,
            specific_ds=True,
            advanced_application=99,
        )
        add_synonym(session, "other_workspace_revenue", oid=2)
        session.commit()
    current = task(database, ds_id)
    current.llm = CompletedQuestionProvider("sales")
    run(current)
    assert set(current.chat_question.expanded_keywords.split(",")) == {
        "sales",
        "workspace_revenue",
        "source_revenue",
    }
    assert "other_source_revenue" not in current.chat_question.terminologies
    assert "application_revenue" not in current.chat_question.terminologies


@pytest.mark.parametrize("assistant_type", [1, 3])
def test_advanced_application_synonyms_and_dynamic_tables_keep_their_boundaries(
    table_environment, monkeypatch, assistant_type
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.data_training.models.data_training_model import DataTraining

    database, client, _ds_id = table_environment
    configure(
        client, enabled=False, table_enabled=True, keyword_enabled=True, table_count=1
    )
    with Session(database) as session:
        add_synonym(session, "workspace_revenue", oid=1)
        add_synonym(
            session,
            "application_revenue",
            oid=1,
            specific_ds=True,
            advanced_application=99,
        )
        add_synonym(
            session,
            "other_application_revenue",
            oid=1,
            specific_ds=True,
            advanced_application=100,
        )
        session.add(
            DataTraining(
                oid=1,
                advanced_application=99,
                enabled=True,
                question="sales by region",
                description="current application example",
            )
        )
        session.add(
            DataTraining(
                oid=1,
                advanced_application=100,
                enabled=True,
                question="sales by region",
                description="other application example",
            )
        )
        session.commit()
    dynamic = [
        {
            "id": 901,
            "name": "dynamic",
            "type": "pg",
            "dataBase": "synthetic",
            "tables": [
                {
                    "name": name,
                    "comment": "",
                    "fields": [{"name": "id", "type": "INTEGER", "comment": ""}],
                }
                for name in ("sales_alpha", "vector_beta", "other_gamma")
            ],
        }
    ]
    monkeypatch.setattr(
        "apps.system.crud.assistant.requests.get",
        lambda **_kw: SimpleNamespace(
            status_code=200, text=json.dumps({"code": 0, "data": dynamic})
        ),
    )
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: embedding_model(limit=5, calls=calls)
    )
    assistant = SimpleNamespace(
        type=assistant_type,
        id=99,
        oid=1,
        certificate="[]",
        request_origin=None,
        configuration=json.dumps({"endpoint": "https://host.invalid/datasources"}),
    )
    current = task(database, None, assistant=assistant)
    current.llm = CompletedQuestionProvider("sales by region")
    schema = run(current)
    assert current.chat_question.expanded_keywords == "sales,application_revenue"
    assert "current application example" in current.chat_question.data_training
    assert "other application example" not in current.chat_question.data_training
    assert "application_revenue meaning" in current.chat_question.terminologies
    assert "workspace_revenue" not in current.chat_question.terminologies
    assert "other_application_revenue" not in current.chat_question.terminologies
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    assert calls == []
    assert len(current.llm.requests) == 3


def test_vector_only_long_completion_keeps_allowed_tables_without_keyword_extraction(
    table_environment, monkeypatch
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache

    database, client, ds_id = table_environment
    configure(
        client, enabled=False, table_enabled=True, keyword_enabled=False, table_count=1
    )
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: embedding_model(limit=5, calls=calls)
    )
    current = task(database, ds_id)
    current.llm = CompletedQuestionProvider("sales revenue by customer region")
    schema = run(current)
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    assert "hidden_table" not in schema
    assert calls == []
    assert len(current.llm.requests) == 2


def test_failed_keyword_extraction_keeps_resolved_vector_query_and_closes_log(
    table_environment, monkeypatch, caplog
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.chat.models.chat_model import ChatLog, OperationEnum

    database, client, ds_id = table_environment
    configure(
        client,
        enabled=False,
        table_enabled=True,
        keyword_enabled=True,
        table_count=1,
        table_alpha=0,
    )
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: embedding_model(limit=100, calls=calls),
    )

    class FailedKeywords(CompletedQuestionProvider):
        def stream(self, messages):
            if not messages[0].content.startswith(
                "Complete the current data question"
            ) and "【Schema】" not in "\n".join(m.content for m in messages):
                raise RuntimeError("controlled extraction failure")
            yield from super().stream(messages)

    current = task(database, ds_id, question="and by region?")
    current.llm = FailedKeywords("sales by customer region", sql_table="vector_beta")
    run(current)
    assert calls == ["sales by customer region"]
    assert not current.chat_question.extracted_keywords
    assert not current.chat_question.expanded_keywords
    assert '"stage": "keyword_extraction"' in caplog.text
    assert '"reason": "model_error"' in caplog.text
    with Session(database) as session:
        log = (
            session.query(ChatLog)
            .filter(
                ChatLog.pid == current.record.id,
                ChatLog.operate == OperationEnum.EXTRACT_KEYWORDS,
            )
            .one()
        )
        assert log.finish_time is not None


@pytest.mark.parametrize("keywords", ["", "EMPTY", "ERROR:NOT_DATA_QUERY"])
def test_empty_extraction_does_not_enable_keyword_scoring(table_environment, keywords):
    database, client, ds_id = table_environment
    configure(
        client,
        enabled=False,
        table_enabled=True,
        keyword_enabled=True,
        table_count=1,
        table_alpha=0,
    )
    current = task(database, ds_id)
    current.llm = CompletedQuestionProvider(
        "sales by region", keywords, sql_table="vector_beta"
    )
    schema = run(current)
    assert "vector_beta" in schema and "sales_alpha" not in schema
    assert not current.chat_question.extracted_keywords
    assert not current.chat_question.expanded_keywords


def test_long_query_fallback_still_rejects_sql_for_a_hidden_table(
    table_environment, monkeypatch
):
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.chat.models.chat_model import ChatFinishStep

    database, client, ds_id = table_environment
    configure(
        client, enabled=False, table_enabled=True, keyword_enabled=False, table_count=1
    )
    calls = []
    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: embedding_model(limit=5, calls=calls)
    )
    current = task(database, ds_id, question="use hidden_table")
    current.llm = CompletedQuestionProvider(
        "sales by customer region with refunds", sql_table="hidden_table"
    )
    results = list(
        current.run_task(
            in_chat=False, stream=False, finish_step=ChatFinishStep.GENERATE_SQL
        )
    )
    assert results[-1]["success"] is False
    assert "unauthorized tables: hidden_table" in results[-1]["message"]
    assert "hidden_table" not in current.chat_question.db_schema
    assert all(
        name in current.chat_question.db_schema
        for name in ("sales_alpha", "vector_beta", "other_gamma")
    )
    assert calls == []
