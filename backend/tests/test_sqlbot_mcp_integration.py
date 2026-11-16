"""Opt-in end-to-end acceptance for sqlbot-mcp on a disposable PostgreSQL database.

Run explicitly with SQLBOT_RUN_SQLBOT_MCP_INTEGRATION=1 and
SQLBOT_TEST_DATABASE_URL pointing at an authorized, *empty, disposable*
PostgreSQL database (with the pgvector extension available). The test runs the
real Alembic chain there, seeds its own rows and a ``hr`` schema used as the
queried datasource, and drops what it created.

The production ``main:mcp_app`` runs in a child Uvicorn process with **no AI
model configured**; only the embedding model is replaced. Agent-token
authentication, datasource permissions, the SQL guard, real PostgreSQL
execution, chat records and audit logs are all real.
"""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine, select

pytestmark = pytest.mark.skipif(
    os.environ.get("SQLBOT_RUN_SQLBOT_MCP_INTEGRATION") != "1",
    reason="explicit disposable PostgreSQL integration opt-in required",
)

BACKEND = Path(__file__).parents[1]


def serve_controlled_process(app_name, port):
    """Child entry point: only the embedding model is replaced."""
    import uvicorn
    from test_query_embedding import embedding_model

    from apps.ai_model.embedding import EmbeddingModelCache

    EmbeddingModelCache.get_model = staticmethod(lambda: embedding_model(limit=512))
    uvicorn.run("main:" + app_name, host="127.0.0.1", port=port, lifespan="on", log_level="warning")


@pytest.fixture
def environment(tmp_path):
    url = make_url(os.environ["SQLBOT_TEST_DATABASE_URL"])
    env = dict(os.environ)
    env.update({
        "POSTGRES_SERVER": url.host or "127.0.0.1",
        "POSTGRES_PORT": str(url.port or 5432),
        "POSTGRES_USER": url.username or "",
        "POSTGRES_PASSWORD": url.password or "",
        "POSTGRES_DB": url.database or "",
        "MCP_IMAGE_PATH": str(tmp_path / "images"),
        "EMBEDDING_ENABLED": "false",
        "TABLE_EMBEDDING_ENABLED": "false",
        "TABLE_EMBEDDING_KEYWORD_ENABLED": "false",
        "PYTHONPATH": str(BACKEND / "tests") + os.pathsep + env.get("PYTHONPATH", ""),
    })
    database = create_engine(url.render_as_string(hide_password=False))
    with database.connect() as connection:
        existing = connection.execute(text(
            "select count(*) from information_schema.tables where table_schema = 'public'")).scalar_one()
    assert existing == 0, "SQLBOT_TEST_DATABASE_URL must point at an empty disposable database"
    # Migrate the way the application does (``main.run_migrations`` in the
    # lifespan): model modules are imported first, which some historical
    # migrations rely on (e.g. 039 uses ``pgvector.sqlalchemy`` without
    # importing it), so the bare ``alembic`` CLI is not equivalent.
    migrate = subprocess.run([sys.executable, "-c", "import main; main.run_migrations()"], cwd=BACKEND, env=env,
                             capture_output=True, text=True, timeout=900)
    assert migrate.returncode == 0, migrate.stdout[-2000:] + migrate.stderr[-4000:]
    try:
        yield {"url": url, "database": database, "env": env, "tmp_path": tmp_path}
    finally:
        database.dispose()


def _seed(env_info):
    import sqlbot_xpack  # noqa: F401

    from apps.datasource.models.datasource import (
        CoreDatasource,
        CoreField,
        CoreTable,
        DatasourceConf,
    )
    from apps.datasource.utils.utils import aes_encrypt
    from apps.system.crud import agent_token_manage as tokens
    from apps.system.models.system_model import (
        AiModelDetail,
        UserWsModel,
        WorkspaceModel,
    )
    from apps.system.models.user import UserModel

    url, database = env_info["url"], env_info["database"]
    with database.begin() as connection:
        connection.execute(text("CREATE SCHEMA hr"))
        connection.execute(text("CREATE TABLE hr.emp (id int, name text, salary int, region text)"))
        connection.execute(text("CREATE TABLE hr.secret (id int)"))
        connection.execute(text(
            "INSERT INTO hr.emp VALUES (1,'ann',100,'east'),(2,'bob',200,'west'),(3,'cid',300,'east')"))
    with Session(database) as session:
        assert session.exec(select(AiModelDetail)).first() is None, "no AI model must be configured"
        session.add(WorkspaceModel(id=10, name="ws"))
        session.add(UserModel(id=2, account="agent_user", name="agent", email="a@b.c", oid=10, status=1,
                              origin=0, language="zh-CN"))
        session.add(UserWsModel(uid=2, oid=10, weight=0))
        # Store only the connection fields, like the datasource form does
        # (``DatasourceConf``'s own ``sheets`` default does not round-trip).
        conf = {"host": url.host, "port": url.port or 5432, "username": url.username, "password": url.password,
                "database": url.database, "dbSchema": "hr", "timeout": 10}
        DatasourceConf(**conf)
        # aes_encrypt returns bytes; datasources store the base64 text.
        configuration = aes_encrypt(json.dumps(conf)).decode()
        hr = CoreDatasource(name="hr", description="hr data", type="pg", type_name="PostgreSQL",
                            configuration=configuration, oid=10, create_by=1, status="Success",
                            recommended_config=1)
        other = CoreDatasource(name="other", description="", type="pg", type_name="PostgreSQL",
                               configuration=configuration, oid=99, create_by=1, status="Success",
                               recommended_config=1)
        session.add(hr)
        session.add(other)
        session.flush()
        emp = CoreTable(ds_id=hr.id, checked=True, table_name="emp", table_comment="employees", custom_comment="")
        session.add(emp)
        session.flush()
        for index, (name, kind) in enumerate([("id", "int4"), ("name", "text"), ("salary", "int4"),
                                              ("region", "text")]):
            session.add(CoreField(ds_id=hr.id, table_id=emp.id, checked=True, field_name=name, field_type=kind,
                                  field_comment="", custom_comment="", field_index=index))
        session.commit()
        issued = tokens.create_token(session, uid=2, oid=10, name="it")
        disabled = tokens.create_token(session, uid=2, oid=10, name="off")
        tokens.set_token_status(session, uid=2, token_id=disabled.model.id, status=False)
        return {"token": issued.plain, "disabled": disabled.plain, "token_id": issued.model.id,
                "ds_id": hr.id, "other_ds_id": other.id}


async def _session_call(url, token, calls):
    headers = {"Authorization": f"Bearer {token}"}
    async with streamablehttp_client(url, headers=headers, timeout=30) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return [await session.call_tool(name, args) for name, args in calls]


def _status(url, token):
    import httpx

    headers = {"Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    return httpx.post(url, json=body, headers=headers, timeout=10).status_code


def test_agent_queries_without_any_model(environment):
    from test_mcp_parameters_integration import server

    from apps.chat.models.chat_model import Chat, ChatRecord
    from apps.system.models.system_model import AgentTokenModel
    from common.audit.models.log_model import SystemLog

    seed = _seed(environment)
    ds = str(seed["ds_id"])
    with server("mcp_app", environment["env"], environment["tmp_path"],
                provider_module="test_sqlbot_mcp_integration") as base:
        url = base + "/sqlbot-mcp"
        for bad in ("", "sk-sqlbot-zzzzzzzz-nope", seed["disabled"]):
            assert _status(url, bad) == 401
        assert _status(base + "/api/v1/system/agent-token", seed["token"]) in (401, 404)

        results = asyncio.run(_session_call(url, seed["token"], [
            ("agent_list_datasources", {}),
            ("agent_get_query_context", {"datasource_id": ds, "question": "average salary by region"}),
            ("agent_execute_sql", {"datasource_id": ds, "question": "average salary by region",
                                   "sql": "SELECT region, avg(salary) AS avg_salary FROM emp "
                                          "GROUP BY region ORDER BY region"}),
            ("agent_execute_sql", {"datasource_id": ds, "sql": "SELECT * FROM secret", "question": "q"}),
            ("agent_execute_sql", {"datasource_id": ds, "question": "q",
                                   "sql": "WITH x AS (DELETE FROM emp RETURNING *) SELECT * FROM x"}),
            ("agent_execute_sql", {"datasource_id": str(seed["other_ds_id"]), "sql": "SELECT id FROM emp",
                                   "question": "q"}),
            ("agent_execute_sql", {"datasource_id": ds, "sql": "SELECT name FROM emp ORDER BY id",
                                   "question": "names", "max_rows": 2}),
        ]))
    listed, context, ok, denied_table, denied_write, denied_ds, capped = results

    assert not listed.isError, listed
    assert {d["name"] for d in listed.structuredContent["result"]} == {"hr"}
    assert not context.isError, context
    assert "emp" in context.structuredContent["schema"]
    assert context.structuredContent["engine"].startswith("PostgreSQL")
    assert not ok.isError, ok
    assert [r["region"] for r in ok.structuredContent["data"]] == ["east", "west"]
    assert denied_table.isError and "not accessible" in denied_table.content[0].text
    assert denied_write.isError and "write operation" in denied_write.content[0].text
    assert denied_ds.isError and "not found" in denied_ds.content[0].text.lower()
    assert not capped.isError and capped.structuredContent["truncated"] is True
    assert [r["name"] for r in capped.structuredContent["data"]] == ["ann", "bob"]

    with Session(environment["database"]) as session:
        # The queried data is intact (the nested DELETE never ran).
        assert session.exec(text("SELECT count(*) FROM hr.emp")).one()[0] == 3
        record = session.get(ChatRecord, int(ok.structuredContent["record_id"]))
        chat = session.get(Chat, record.chat_id)
        assert chat.origin == 1 and chat.create_by == 2 and chat.oid == 10
        assert record.finish and not record.error and "GROUP BY region" in record.sql
        audits = session.exec(select(SystemLog).where(SystemLog.module == "agent_mcp")).all()
        assert {a.operation_status for a in audits} == {"success", "failed"}
        assert session.get(AgentTokenModel, seed["token_id"]).last_used_time is not None
