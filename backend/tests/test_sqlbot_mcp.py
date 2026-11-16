"""Offline regressions for the sqlbot-mcp server wiring.

A real FastMCP server is mounted on a fresh Starlette app and driven by the
official MCP Streamable HTTP client over an in-process ASGI transport. The
authenticator, audit sink and services are test doubles; no database, model
or network is used.
"""

import contextlib
import json
from types import SimpleNamespace

import httpx
import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before app imports.
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from starlette.applications import Starlette

from apps.mcp.sqlbot_mcp import service
from apps.mcp.sqlbot_mcp.auth import (
    AgentPrincipal,
    AuthenticationFailed,
    current_principal,
)
from apps.mcp.sqlbot_mcp.ratelimit import InMemoryRateLimiter
from apps.mcp.sqlbot_mcp.server import SERVER_NAME, build_sqlbot_mcp, mount_sqlbot_mcp
from apps.mcp.sqlbot_mcp.tools import base as tool_base

GOOD = "sk-sqlbot-goodgood-secret"


class FakeAuthenticator:
    async def authenticate(self, request):
        if request.headers.get("authorization") != f"Bearer {GOOD}":
            raise AuthenticationFailed("bad")
        user = SimpleNamespace(id=2, oid=10, account="u", name="u")
        return AgentPrincipal(user=user, credential_id="7", credential_kind="agent_token",
                              allowed_ds_ids=frozenset({101}), client_ip="1.2.3.4")


class RecordingAudit(tool_base.AuditSink):
    def __init__(self):
        self.events = []

    def record(self, **kwargs):
        self.events.append(kwargs)


@pytest.fixture
def harness(monkeypatch):
    audit = RecordingAudit()
    seen = {}

    def list_datasources(_session, principal):
        seen["principal"] = principal
        return [{"id": "101", "name": "sales"}]

    def execute_sql(_session, _principal, _datasource_id, sql, *_rest):
        if "forbidden" in sql:
            raise service.ToolError("SQL references tables that are not accessible: forbidden", code="table_access")
        if "boom" in sql:
            raise RuntimeError("database password=secret leaked?")
        return {"chat_id": "1", "record_id": "9", "fields": ["n"], "data": [{"n": 1}], "truncated": False}

    monkeypatch.setattr(service, "list_datasources", list_datasources)
    monkeypatch.setattr(service, "execute_sql", execute_sql)

    server = build_sqlbot_mcp(authenticator=FakeAuthenticator(), audit=audit,
                              rate_limiter=InMemoryRateLimiter(per_minute=5, max_concurrent_heavy=1),
                              session_factory=lambda: contextlib.nullcontext(None))
    host = Starlette()
    lifespan = mount_sqlbot_mcp(host, server, "/sqlbot-mcp")
    return SimpleNamespace(app=host, lifespan=lifespan, audit=audit, seen=seen)


@contextlib.asynccontextmanager
async def client(harness, token=GOOD, path="/sqlbot-mcp"):
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    def factory(headers=None, timeout=None, auth=None):
        return httpx.AsyncClient(transport=httpx.ASGITransport(app=harness.app), base_url="http://test",
                                 headers=headers, timeout=timeout, auth=auth)

    async with harness.lifespan():
        async with streamablehttp_client(f"http://test{path}", headers=headers,
                                         httpx_client_factory=factory) as (read, write, _):
            async with ClientSession(read, write) as session:
                yield session


def payload(result):
    return json.loads(result.content[0].text)


@pytest.mark.anyio
@pytest.mark.parametrize("path", ["/sqlbot-mcp", "/sqlbot-mcp/"])
async def test_tools_are_listed_under_the_server_name(harness, path):
    async with client(harness, path=path) as session:
        init = await session.initialize()
        tools = await session.list_tools()
    assert init.serverInfo.name == SERVER_NAME
    assert {t.name for t in tools.tools} == {
        "agent_list_datasources", "agent_get_query_context", "agent_list_tables",
        "agent_describe_tables", "agent_execute_sql",
    }


@pytest.mark.anyio
@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer nope"}, {"Authorization": GOOD}])
@pytest.mark.parametrize("path", ["/sqlbot-mcp", "/sqlbot-mcp/"])
async def test_unauthenticated_requests_get_401_without_redirect(harness, headers, path):
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    async with harness.lifespan():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=harness.app), base_url="http://test") as c:
            response = await c.post(path, json=body, headers={**headers, "Accept": "application/json, text/event-stream"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")


@pytest.mark.anyio
async def test_tools_receive_the_authenticated_principal(harness):
    async with client(harness) as session:
        await session.initialize()
        result = await session.call_tool("agent_list_datasources", {})
    assert not result.isError
    assert (result.structuredContent or {}).get("result") == [{"id": "101", "name": "sales"}]
    assert harness.seen["principal"].credential_id == "7"


@pytest.mark.anyio
async def test_rejections_are_returned_and_audited(harness):
    async with client(harness) as session:
        await session.initialize()
        ok = await session.call_tool("agent_execute_sql", {"datasource_id": "101", "sql": "SELECT 1 FROM t",
                                                          "question": "q"})
        denied = await session.call_tool("agent_execute_sql", {"datasource_id": "101",
                                                              "sql": "SELECT * FROM forbidden", "question": "q"})
    assert not ok.isError
    assert denied.isError and "not accessible" in denied.content[0].text
    outcomes = [(e["tool"], e["ok"]) for e in harness.audit.events]
    assert outcomes == [("agent_execute_sql", True), ("agent_execute_sql", False)]
    assert harness.audit.events[0]["resource_id"] == "9"
    assert "table_access" in harness.audit.events[1]["detail"]


@pytest.mark.anyio
async def test_internal_errors_do_not_leak_details(harness):
    async with client(harness) as session:
        await session.initialize()
        result = await session.call_tool("agent_execute_sql", {"datasource_id": "101", "sql": "SELECT boom FROM t",
                                                              "question": "q"})
    assert result.isError
    assert "secret" not in result.content[0].text
    assert result.content[0].text.endswith("Internal error")


@pytest.mark.anyio
async def test_rate_limit_applies_per_credential(harness):
    async with client(harness) as session:
        await session.initialize()
        results = [await session.call_tool("agent_list_datasources", {}) for _ in range(6)]
    assert [r.isError for r in results] == [False] * 5 + [True]
    assert "Rate limit" in results[-1].content[0].text


def test_tools_refuse_to_run_without_a_principal():
    with pytest.raises(PermissionError):
        current_principal()


def test_heavy_calls_are_capped_and_released():
    limiter = InMemoryRateLimiter(per_minute=100, max_concurrent_heavy=1)
    slot = limiter.acquire("agent_token", "7", heavy=True)
    with pytest.raises(Exception, match="Too many queries"):
        limiter.acquire("agent_token", "7", heavy=True)
    limiter.acquire("agent_token", "8", heavy=True)  # other credentials are independent
    slot.release()
    limiter.acquire("agent_token", "7", heavy=True)
