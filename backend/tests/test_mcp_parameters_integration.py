"""Opt-in independent Uvicorn/MCP SSE acceptance on an isolated PostgreSQL schema.

Only LLM, embedding and external datasource providers are controlled. Authentication,
MCP transport, parameter API, task creation, retrieval and SQL validation stay real.
API lifespan migrations are disabled because the fixture owns its schema; the MCP
process uses the production main:mcp_app with its normal lifespan.
"""

import asyncio
import json
import logging
import os
import secrets
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx
import test_table_parameters_integration as table_contracts
from mcp import ClientSession
from mcp.client.sse import sse_client
from sqlalchemy import text
from sqlmodel import Session
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)

from apps.system.models.system_model import AiModelDetail, UserWsModel
from apps.system.models.user import UserModel
from common.core.security import md5pwd

table_environment = table_contracts.table_environment


def serve_controlled_process(app_name, port):
    """Child entry point: substitute providers before Uvicorn imports main."""
    from types import SimpleNamespace

    import uvicorn
    from langchain_core.messages import AIMessageChunk

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.ai_model.model_factory import BaseLLM, LLMFactory
    from apps.chat.task import llm

    class Provider(BaseLLM):
        def _init_llm(self):
            return self

        def stream(self, messages):
            context = "\n".join(message.content for message in messages)
            with Path(os.environ["SQLBOT_TEST_CONTEXTS"]).open("a") as output:
                output.write(json.dumps(context) + "\n")
            # Chart prompts include the SQL that has just passed validation.
            if "SELECT id FROM vector_beta" in messages[-1].content:
                answer = {"type": "table", "columns": [{"name": "id", "value": "id"}]}
            else:
                answer = {
                    "success": True,
                    "sql": "SELECT id FROM vector_beta",
                    "tables": ["vector_beta"],
                }
            yield AIMessageChunk(content=json.dumps(answer))

    LLMFactory.register_llm("openai", Provider)
    EmbeddingModelCache.get_model = staticmethod(
        lambda: SimpleNamespace(embed_query=lambda _text: [1.0, 0.0])
    )
    llm.get_version = lambda _ds: ""
    llm.check_connection = lambda **_kwargs: True
    llm.exec_sql = lambda **_kwargs: {"fields": ["id"], "data": [{"id": 7}]}
    uvicorn.run(
        "main:" + app_name,
        host="127.0.0.1",
        port=port,
        lifespan="off" if app_name == "app" else "on",
        log_level="warning",
    )


@contextmanager
def server(app_name, env, directory):
    with socket.socket() as bound:
        bound.bind(("127.0.0.1", 0))
        port = bound.getsockname()[1]
    log_path = directory / (app_name + ".log")
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "from test_mcp_parameters_integration import serve_controlled_process; "
                f"serve_controlled_process({app_name!r}, {port})",
            ],
            cwd=Path(__file__).parents[1],
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            deadline = time.monotonic() + 40
            while True:
                assert process.poll() is None, log_path.read_text()
                try:
                    with socket.create_connection(("127.0.0.1", port), timeout=0.1):
                        break
                except OSError:
                    assert time.monotonic() < deadline, log_path.read_text()
                    time.sleep(0.05)
            yield f"http://127.0.0.1:{port}"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def test_mcp_network_task_uses_parameter_saved_by_another_api_process(
    table_environment, tmp_path, caplog
):
    # MCP debug messages contain request bodies, including this disposable token.
    caplog.set_level(logging.WARNING, logger="mcp.client.sse")
    database, _client, ds_id = table_environment
    for model in (UserModel, UserWsModel, AiModelDetail):
        model.__table__.create(database)
    password = secrets.token_urlsafe(24)
    with Session(database) as session:
        schema = session.execute(text("SELECT current_schema()")).scalar_one()
        session.add(
            UserModel(
                id=1,
                account="admin",
                name="MCP test",
                oid=1,
                email="mcp@example.invalid",
                password=md5pwd(password),
                status=1,
            )
        )
        session.add(UserWsModel(uid=1, oid=1, weight=1))
        session.add(
            AiModelDetail(
                supplier=1,
                name="controlled",
                model_type=1,
                base_model="controlled",
                default_model=True,
                api_domain="http://127.0.0.1:9/v1",
                api_key="unused",
                config="[]",
            )
        )
        session.commit()
    for name in ("logs", "images", "scripts", "files", "excel", "models"):
        (tmp_path / name).mkdir()
    env = {
        **os.environ,
        "SQLBOT_DB_URL": database.url.update_query_dict(
            {"options": f"-csearch_path={schema},public"}
        ).render_as_string(hide_password=False),
        "PYTHONPATH": os.pathsep.join(
            [str(Path(__file__).parent), str(Path(__file__).parents[1])]
        ),
        "SECRET_KEY": secrets.token_urlsafe(48),
        "CACHE_TYPE": "None",
        "CONTEXT_PATH": "",
        "BASE_DIR": str(tmp_path),
        "LOG_DIR": str(tmp_path / "logs"),
        "MCP_IMAGE_PATH": str(tmp_path / "images"),
        "SCRIPT_DIR": str(tmp_path / "scripts"),
        "UPLOAD_DIR": str(tmp_path / "files"),
        "EXCEL_PATH": str(tmp_path / "excel"),
        "LOCAL_MODEL_PATH": str(tmp_path / "models"),
        "LOG_FORMAT": "%(levelname)s %(message)s",
        "LOG_LEVEL": "WARNING",
        "SQLBOT_TEST_CONTEXTS": str(tmp_path / "contexts.jsonl"),
        "EMBEDDING_ENABLED": "false",
        "TABLE_EMBEDDING_ENABLED": "true",
        "TABLE_EMBEDDING_COUNT": "10",
        "TABLE_EMBEDDING_KEYWORD_ENABLED": "false",
        "SAMPLE_DATA_ENABLED": "false",
    }
    with (
        server("app", env, tmp_path) as api,
        server("mcp_app", env, tmp_path) as mcp_url,
    ):
        with httpx.Client(base_url=api, timeout=15) as client:
            response = client.post(
                "/api/v1/mcp/access_token",
                json={"username": "admin", "password": password},
            )
            assert response.status_code == 200, response.text
            token = response.json()["data"]["access_token"]
            client.headers["X-SQLBOT-TOKEN"] = "Bearer " + token

            async def ask_twice():
                async with sse_client(
                    mcp_url + "/mcp", timeout=15, sse_read_timeout=30
                ) as streams:
                    async with ClientSession(*streams) as session:
                        await session.initialize()
                        assert "mcp_question" in {
                            tool.name for tool in (await session.list_tools()).tools
                        }
                        rejected = await session.call_tool(
                            "mcp_question",
                            {
                                "token": "invalid",
                                "chat_id": 0,
                                "question": "show totals",
                                "stream": False,
                            },
                        )
                        assert rejected.isError
                        for count in (1, 2):
                            response = client.post(
                                "/api/v1/system/parameter",
                                data={
                                    "data": json.dumps(
                                        [
                                            {
                                                "pkey": "embedding.table_count",
                                                "pval": count,
                                            },
                                        ]
                                    )
                                },
                            )
                            assert response.status_code == 200, response.text
                            started = await session.call_tool(
                                "mcp_start", {"token": token}
                            )
                            assert not started.isError, started
                            chat_id = json.loads(started.content[0].text)["data"][
                                "chat_id"
                            ]
                            result = await session.call_tool(
                                "mcp_question",
                                {
                                    "token": token,
                                    "chat_id": chat_id,
                                    "datasource_id": str(ds_id),
                                    "question": "show totals",
                                    "stream": False,
                                    "return_img": False,
                                    "lang": "en",
                                },
                            )
                            assert not result.isError, result
                            answer = json.loads(result.content[0].text)
                            assert (
                                answer["success"]
                                and answer["sql"] == "SELECT id FROM vector_beta"
                            )
                            assert answer["data"]
                            contexts = [
                                json.loads(line)
                                for line in (tmp_path / "contexts.jsonl")
                                .read_text()
                                .splitlines()
                            ]
                            sql_context = contexts[-2]
                            assert "# Table: synthetic.vector_beta" in sql_context
                            assert (
                                "# Table: synthetic.other_gamma" in sql_context
                            ) == (count == 2)
                            assert "# Table: synthetic.hidden_table" not in sql_context
                            assert "# Table: synthetic.sales_alpha" not in sql_context

            asyncio.run(ask_twice())
