"""Opt-in task contracts using isolated PG; only model/source providers substituted."""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessageChunk
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlbot_xpack.permissions.models.ds_rules import DsRules
from sqlmodel import Session
from test_embedding_parameters import save
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)

from apps.ai_model.model_factory import LLMConfig
from apps.chat.models.chat_model import Chat, ChatFinishStep, ChatQuestion, ChatRecord
from apps.chat.task.llm import LLMService
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from apps.datasource.utils.utils import aes_encrypt
from apps.terminology.models.terminology_model import Terminology
from common.core.config import settings


@pytest.fixture
def table_environment(knowledge_environment, monkeypatch):  # noqa: F811
    database, client, _chat_id = knowledge_environment
    for model in (CoreDatasource, CoreTable, CoreField, DsRules):
        model.__table__.create(database)
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_ENABLED", True)
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_COUNT", 10)
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_KEYWORD_ENABLED", False)
    monkeypatch.setattr(settings, "SAMPLE_DATA_ENABLED", False)
    monkeypatch.setattr("apps.chat.task.llm.get_version", lambda _ds: "")
    monkeypatch.setattr("apps.chat.task.llm.check_connection", lambda **_kw: True)
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    monkeypatch.setattr("apps.chat.task.llm.session_maker", sessions)
    with Session(database) as session:
        ds = CoreDatasource(
            name="accessible",
            description="test",
            type="pg",
            type_name="PostgreSQL",
            configuration=aes_encrypt('{"database":"synthetic"}').decode(),
            oid=1,
            embedding="[1,0]",
        )
        session.add(ds)
        session.flush()
        ds_id = ds.id
        for name, comment, vector, checked in [
            ("sales_alpha", "keyword winner", "[0,1]", True),
            ("vector_beta", "vector winner", "[1,0]", True),
            ("other_gamma", "other", "[0.8,0.6]", True),
            ("hidden_table", "sales", "[1,0]", False),
        ]:
            table = CoreTable(
                ds_id=ds_id,
                table_name=name,
                table_comment=comment,
                embedding=vector,
                checked=checked,
            )
            session.add(table)
            session.flush()
            session.add(
                CoreField(
                    ds_id=ds_id,
                    table_id=table.id,
                    field_name="id",
                    field_type="INTEGER",
                    field_index=1,
                )
            )
        session.commit()
    yield database, client, ds_id
    sessions.remove()


class QuestionProvider:
    def __init__(self, *, datasource=None, on_datasource=None):
        self.datasource = datasource
        self.on_datasource = on_datasource
        self.contexts = []

    def stream(self, messages):
        context = "\n".join(message.content for message in messages)
        self.contexts.append(context)
        if "【Schema】" in context:
            table = (
                "vector_beta"
                if "# Table: synthetic.vector_beta" in context
                else "sales_alpha"
            )
            content = json.dumps(
                {"success": True, "sql": f"SELECT id FROM {table}", "tables": [table]}
            )
        elif self.datasource is not None and self.datasource["name"] in context:
            if self.on_datasource:
                self.on_datasource()
            content = json.dumps({"id": self.datasource["id"]})
        else:
            content = "sales"
        yield AIMessageChunk(content=content)


def task(database, ds_id, *, question="show totals", assistant=None, user_id=1):
    with Session(database) as session:
        chat = Chat(
            oid=1,
            create_by=1,
            create_time=datetime.now(),
            brief="test",
            datasource=ds_id,
            engine_type="PostgreSQL",
        )
        session.add(chat)
        session.commit()
        service = LLMService(
            session,
            SimpleNamespace(id=user_id, oid=1, language="en"),
            ChatQuestion(chat_id=chat.id, question=question),
            current_assistant=assistant,
            config=LLMConfig(
                model_type="openai",
                model_name="test",
                api_key="test",
                api_base_url="http://127.0.0.1:9/v1",
            ),
        )
        service.init_record(session)
    service.llm = QuestionProvider()
    return service


def run(service):
    results = list(
        service.run_task(
            in_chat=False, stream=False, finish_step=ChatFinishStep.GENERATE_SQL
        )
    )
    assert results[-1]["success"], results
    return service.chat_question.db_schema


def configure(client, **parameters):
    response = save(
        client,
        [
            {"pkey": f"embedding.{key}", "pval": value}
            for key, value in parameters.items()
        ],
    )
    assert response.status_code == 200, response.text


def test_question_table_count_and_in_flight_snapshot(table_environment):
    database, client, ds_id = table_environment
    configure(client, table_count=1)
    old = task(database, ds_id)
    configure(client, table_count=2)
    old_schema = run(old)
    assert "vector_beta" in old_schema
    assert "sales_alpha" not in old_schema and "other_gamma" not in old_schema
    current = task(database, ds_id)
    schema = run(current)
    assert "vector_beta" in schema and "other_gamma" in schema
    assert "hidden_table" not in schema and "sales_alpha" not in schema
    assert any(schema in context for context in current.llm.contexts)
    with Session(database) as session:
        assert (
            session.get(ChatRecord, current.record.id).sql
            == "SELECT id FROM vector_beta"
        )


def test_keyword_switch_and_weight_change_question_context(table_environment):
    database, client, ds_id = table_environment
    with Session(database) as session:
        term = Terminology(
            oid=1, word="sales", description="keyword-only-term", embedding=[0, 1]
        )
        session.add(term)
        session.flush()
        session.add(Terminology(oid=1, pid=term.id, word="revenue", embedding=[0, 1]))
        session.commit()
    configure(client, table_count=1, table_alpha=0, keyword_enabled=True)
    keyword_task = task(database, ds_id)
    configure(client, keyword_enabled=False)
    schema = run(keyword_task)
    assert "sales_alpha" in schema and "vector_beta" not in schema
    with Session(database) as session:
        record = session.get(ChatRecord, keyword_task.record.id)
        assert record.extracted_keywords == "sales"
        assert "revenue" in record.expanded_keywords
    assert "keyword-only-term" in keyword_task.chat_question.terminologies
    disabled = task(database, ds_id)
    schema = run(disabled)
    assert "vector_beta" in schema and "sales_alpha" not in schema
    with Session(database) as session:
        assert not session.get(ChatRecord, disabled.record.id).extracted_keywords
    assert "keyword-only-term" not in disabled.chat_question.terminologies
    configure(client, keyword_enabled=True, table_alpha=1)
    schema = run(task(database, ds_id))
    assert "vector_beta" in schema and "sales_alpha" not in schema


def test_keywords_remain_independent_of_table_vectors(table_environment, monkeypatch):
    database, client, ds_id = table_environment
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_ENABLED", False)
    configure(client, keyword_enabled=True, table_count=1)
    current = task(database, ds_id)
    schema = run(current)
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    with Session(database) as session:
        assert session.get(ChatRecord, current.record.id).extracted_keywords == "sales"


@pytest.mark.parametrize(
    "bad_vector", [None, "[]", "broken", "[0,0]", "[NaN,1]", "[1,0,0]"]
)
def test_incomplete_table_vectors_preserve_all_eligible_context(
    table_environment, bad_vector
):
    database, client, ds_id = table_environment
    configure(client, table_count=1)
    with Session(database) as session:
        table = (
            session.query(CoreTable).filter(CoreTable.table_name == "sales_alpha").one()
        )
        table.embedding = bad_vector
        session.add(table)
        session.commit()
    schema = run(task(database, ds_id))
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    assert "hidden_table" not in schema


def test_failed_query_vectors_preserve_all_eligible_context(
    table_environment, monkeypatch
):
    from apps.ai_model.embedding import EmbeddingModelCache

    database, client, ds_id = table_environment
    configure(client, table_count=1, keyword_enabled=True)

    def fail(_query):
        raise RuntimeError("controlled embedding failure")

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: SimpleNamespace(embed_query=fail)
    )
    # Knowledge vectors are separate from this test; keep literal knowledge active.
    monkeypatch.setattr(settings, "EMBEDDING_ENABLED", False)
    schema = run(task(database, ds_id))
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    assert "hidden_table" not in schema


def add_datasource_candidates(database):
    with Session(database) as session:
        session.add(
            CoreDatasource(
                name="second_candidate",
                description="test",
                type="pg",
                oid=1,
                embedding="[0,1]",
            )
        )
        session.add(
            CoreDatasource(
                name="foreign_workspace",
                description="test",
                type="pg",
                oid=2,
                embedding="[1,0]",
            )
        )
        session.commit()


def test_datasource_preselection_and_following_steps_share_task_snapshot(
    table_environment,
):
    database, client, ds_id = table_environment
    add_datasource_candidates(database)
    configure(client, datasource_count=1, table_count=1, keyword_enabled=False)
    old = task(database, None)
    old.llm = QuestionProvider(
        datasource={"id": ds_id, "name": "accessible"},
        on_datasource=lambda: configure(
            client,
            datasource_count=2,
            table_count=2,
            keyword_enabled=True,
            table_alpha=0,
        ),
    )
    schema = run(old)
    assert "second_candidate" not in old.llm.contexts[0]
    assert "foreign_workspace" not in old.llm.contexts[0]
    assert (
        "vector_beta" in schema
        and "sales_alpha" not in schema
        and "other_gamma" not in schema
    )
    current = task(database, None)
    current.llm = QuestionProvider(datasource={"id": ds_id, "name": "accessible"})
    schema = run(current)
    assert "second_candidate" in current.llm.contexts[0]
    assert "foreign_workspace" not in current.llm.contexts[0]
    assert "sales_alpha" in schema
    with Session(database) as session:
        assert not session.get(ChatRecord, old.record.id).extracted_keywords
        assert session.get(ChatRecord, current.record.id).extracted_keywords == "sales"


@pytest.mark.parametrize(
    "bad_vector", [None, "[]", "broken", "[0,0]", "[NaN,1]", "[1,0,0]"]
)
def test_incomplete_datasource_vectors_keep_original_candidate_dtos(
    table_environment, bad_vector
):
    database, client, ds_id = table_environment
    add_datasource_candidates(database)
    configure(client, datasource_count=1)
    with Session(database) as session:
        ds = (
            session.query(CoreDatasource)
            .filter(CoreDatasource.name == "second_candidate")
            .one()
        )
        ds.embedding = bad_vector
        session.add(ds)
        session.commit()
    current = task(database, None)
    current.llm = QuestionProvider(datasource={"id": ds_id, "name": "accessible"})
    run(current)
    assert "second_candidate" in current.llm.contexts[0]
    assert "foreign_workspace" not in current.llm.contexts[0]
    assert "configuration" not in current.llm.contexts[0]


def test_explicit_tables_and_relations_preserved_without_unchecked_tables(
    table_environment,
):
    database, client, ds_id = table_environment
    configure(client, table_count=1)
    with Session(database) as session:
        tables = {table.table_name: table for table in session.query(CoreTable).all()}
        fields = {field.table_id: field for field in session.query(CoreField).all()}

        def edge(source, target):
            return {
                "shape": "edge",
                "source": {
                    "cell": str(tables[source].id),
                    "port": str(fields[tables[source].id].id),
                },
                "target": {
                    "cell": str(tables[target].id),
                    "port": str(fields[tables[target].id].id),
                },
            }

        ds = session.get(CoreDatasource, ds_id)
        ds.table_relation = [
            edge("vector_beta", "other_gamma"),
            edge("vector_beta", "hidden_table"),
        ]
        session.add(ds)
        session.commit()
    schema = run(task(database, ds_id))
    assert "vector_beta" in schema and "other_gamma" in schema
    assert "vector_beta.id=other_gamma.id" in schema
    assert "hidden_table" not in schema and "sales_alpha" not in schema
    schema = run(task(database, ds_id, question="compare sales_alpha and other_gamma"))
    assert all(name in schema for name in ("sales_alpha", "other_gamma", "vector_beta"))
    assert "hidden_table" not in schema


@pytest.mark.parametrize("assistant_type", [0, 2, 4])
def test_ordinary_and_embedded_tasks_apply_saved_selection(
    table_environment, assistant_type
):
    database, client, ds_id = table_environment
    add_datasource_candidates(database)
    configure(client, table_count=1, keyword_enabled=False, datasource_count=1)
    assistant = SimpleNamespace(
        type=assistant_type,
        id=99,
        oid=1,
        online=False,
        configuration=json.dumps({"oid": 1, "public_list": [ds_id]}),
    )
    current = task(database, None, assistant=assistant)
    current.llm = QuestionProvider(datasource={"id": ds_id, "name": "accessible"})
    schema = run(current)
    assert "vector_beta" in schema and "sales_alpha" not in schema
    assert "second_candidate" not in "\n".join(current.llm.contexts)
    assert "foreign_workspace" not in "\n".join(current.llm.contexts)


def test_advanced_application_keeps_full_dynamic_candidates(
    table_environment, monkeypatch
):
    database, client, _ds_id = table_environment
    configure(client, table_count=1, datasource_count=1, keyword_enabled=False)
    dynamic = [
        {
            "id": index,
            "name": name,
            "type": "pg",
            "dataBase": "synthetic",
            "tables": [
                {
                    "name": table,
                    "comment": "",
                    "fields": [{"name": "id", "type": "INTEGER", "comment": ""}],
                }
                for table in ("sales_alpha", "vector_beta", "other_gamma")
            ],
        }
        for index, name in [(901, "dynamic_first"), (902, "dynamic_second")]
    ]
    monkeypatch.setattr(
        "apps.system.crud.assistant.requests.get",
        lambda **_kw: SimpleNamespace(
            status_code=200, text=json.dumps({"code": 0, "data": dynamic})
        ),
    )
    assistant = SimpleNamespace(
        type=1,
        id=99,
        oid=1,
        certificate="[]",
        request_origin=None,
        configuration=json.dumps({"endpoint": "https://host.invalid/datasources"}),
    )
    current = task(database, None, assistant=assistant)
    current.llm = QuestionProvider(datasource={"id": 901, "name": "dynamic_first"})
    schema = run(current)
    assert "dynamic_second" in current.llm.contexts[0]
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))


def test_saved_selection_visible_to_independent_task_processes(table_environment):
    import os
    import subprocess
    import sys
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path

    from sqlalchemy import text

    database, client, ds_id = table_environment
    add_datasource_candidates(database)
    configure(
        client, table_count=1, table_alpha=0, keyword_enabled=True, datasource_count=1
    )
    with database.connect() as connection:
        schema = connection.execute(text("select current_schema()")).scalar_one()
    script = """
import json, os
from types import SimpleNamespace
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session, create_engine
import test_table_parameters_integration as contract
from apps.ai_model.embedding import EmbeddingModelCache
import apps.chat.task.llm as tasks
EmbeddingModelCache.get_model = staticmethod(lambda: SimpleNamespace(embed_query=lambda _: [1.0, 0.0]))
db = create_engine(os.environ['SQLBOT_TEST_DATABASE_URL'], connect_args={'options': '-csearch_path=' + os.environ['SQLBOT_TEST_SCHEMA'] + ',public'})
tasks.session_maker = scoped_session(sessionmaker(bind=db, class_=Session))
tasks.get_version = lambda _: ''
tasks.check_connection = lambda **_: True
service = contract.task(db, None)
service.llm = contract.QuestionProvider(datasource={'id': int(os.environ['SQLBOT_TEST_DS_ID']), 'name': 'accessible'})
schema = contract.run(service)
print('RESULT:' + json.dumps({'schema': schema, 'candidates': service.llm.contexts[0]}))
tasks.session_maker.remove()
db.dispose()
"""
    env = {
        **os.environ,
        "SQLBOT_TEST_SCHEMA": schema,
        "SQLBOT_TEST_DS_ID": str(ds_id),
        "TABLE_EMBEDDING_ENABLED": "true",
        "TABLE_EMBEDDING_COUNT": "10",
        "TABLE_EMBEDDING_ALPHA": "1",
        "TABLE_EMBEDDING_KEYWORD_ENABLED": "false",
        "DS_EMBEDDING_COUNT": "10",
        "SAMPLE_DATA_ENABLED": "false",
        "EMBEDDING_ENABLED": "false",
        "PYTHONPATH": os.pathsep.join(
            [str(Path(__file__).parent), str(Path(__file__).parents[1])]
        ),
    }

    def process(_index):
        result = subprocess.run(
            [sys.executable, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, result.stderr
        return json.loads(
            next(
                line.removeprefix("RESULT:")
                for line in result.stdout.splitlines()
                if line.startswith("RESULT:")
            )
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(process, range(2)))
    for result in results:
        assert (
            "sales_alpha" in result["schema"] and "vector_beta" not in result["schema"]
        )
        assert "second_candidate" not in result["candidates"]
        assert "foreign_workspace" not in result["candidates"]


def test_column_permissions_also_bound_relation_context(table_environment):
    from sqlbot_xpack.permissions.models.ds_permission import DsPermission

    from apps.system.models.system_model import UserWsModel

    database, client, ds_id = table_environment
    configure(client, table_count=1)
    for model in (DsPermission, UserWsModel):
        model.__table__.create(database)
    with Session(database) as session:
        session.add(UserWsModel(uid=2, oid=1, weight=0))
        beta = (
            session.query(CoreTable).filter(CoreTable.table_name == "vector_beta").one()
        )
        alpha = (
            session.query(CoreTable).filter(CoreTable.table_name == "sales_alpha").one()
        )
        alpha_field = (
            session.query(CoreField).filter(CoreField.table_id == alpha.id).one()
        )
        hidden = CoreField(
            ds_id=ds_id,
            table_id=beta.id,
            field_name="secret_join",
            field_type="INTEGER",
            field_index=2,
        )
        session.add(hidden)
        session.flush()
        permission = DsPermission(
            name="hide secret",
            type="column",
            ds_id=ds_id,
            table_id=beta.id,
            permissions=json.dumps([{"field_id": hidden.id, "enable": False}]),
            enable=True,
        )
        session.add(permission)
        session.flush()
        session.add(
            DsRules(
                oid=1,
                name="restricted",
                permission_list=[permission.id],
                user_list=[2],
                enable=True,
            )
        )
        ds = session.get(CoreDatasource, ds_id)
        ds.table_relation = [
            {
                "shape": "edge",
                "source": {"cell": str(beta.id), "port": str(hidden.id)},
                "target": {"cell": str(alpha.id), "port": str(alpha_field.id)},
            }
        ]
        session.add(ds)
        session.commit()
    schema = run(task(database, ds_id, user_id=2))
    assert "vector_beta" in schema and "secret_join" not in schema
    assert "sales_alpha" not in schema and "Foreign keys" not in schema


def test_sample_data_uses_the_selected_tables(table_environment, monkeypatch):
    database, client, ds_id = table_environment
    configure(client, table_count=1)
    monkeypatch.setattr(settings, "SAMPLE_DATA_ENABLED", True)
    # Substitute the external datasource query, keeping sample filtering/formatting real.
    monkeypatch.setattr(
        "apps.datasource.crud.datasource.exec_sql", lambda **_kw: {"data": [{"id": 42}]}
    )
    current = task(database, ds_id)
    run(current)
    assert "# Table: vector_beta" in current.chat_question.sample_data
    assert '"id": 42' in current.chat_question.sample_data
    assert (
        "sales_alpha" not in current.chat_question.sample_data
        and "hidden_table" not in current.chat_question.sample_data
    )
    assert any(
        current.chat_question.sample_data in context for context in current.llm.contexts
    )


def test_datasource_answer_persistence_uses_original_task_switch(
    table_environment, monkeypatch
):
    database, client, ds_id = table_environment
    add_datasource_candidates(database)
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_ENABLED", False)
    configure(client, table_count=1, datasource_count=1, keyword_enabled=False)
    current = task(database, None)
    current.llm = QuestionProvider(
        datasource={"id": ds_id, "name": "accessible"},
        on_datasource=lambda: monkeypatch.setattr(
            settings, "TABLE_EMBEDDING_ENABLED", True
        ),
    )
    schema = run(current)
    assert "second_candidate" in current.llm.contexts[0]
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    with Session(database) as session:
        answer = session.get(ChatRecord, current.record.id).datasource_select_answer
        assert json.loads(json.loads(answer)["content"])["id"] == ds_id
