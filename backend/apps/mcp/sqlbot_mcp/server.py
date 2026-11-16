"""Assemble the ``sqlbot-mcp`` server (model-free tools for external agents).

``build_sqlbot_mcp`` wires the FastMCP instance, tools, authenticator, rate
limiter and audit sink. ``mount_sqlbot_mcp`` attaches it to an ASGI app at a
path and returns a lifespan context manager the host app must enter.

Transport is MCP Streamable HTTP (stateless, JSON responses), so any worker
can serve any request. Swap or add parts by passing them in; nothing here is
hard-wired to a specific authenticator or backend.
"""

import contextlib
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.types import ASGIApp, Receive, Scope, Send

from apps.mcp.sqlbot_mcp.audit import SystemLogAuditSink
from apps.mcp.sqlbot_mcp.auth import (
    AgentTokenAuthenticator,
    Authenticator,
    AuthMiddleware,
)
from apps.mcp.sqlbot_mcp.ratelimit import InMemoryRateLimiter, RateLimiter
from apps.mcp.sqlbot_mcp.tools import TOOL_MODULES, register_tools
from apps.mcp.sqlbot_mcp.tools.base import AuditSink, ToolRuntime
from common.core.security_config import get_security_config

SERVER_NAME = "sqlbot-mcp"
DEFAULT_MOUNT_PATH = "/sqlbot-mcp"
INSTRUCTIONS = (
    "SQLBot data access for agents. Typical flow: agent_list_datasources -> "
    "agent_get_query_context -> write SQL -> agent_execute_sql. If a table is "
    "missing from the context, use agent_list_tables and agent_describe_tables. "
    "SQLBot never calls a model; you write the SQL."
)


@dataclass
class SqlbotMcp:
    mcp: FastMCP
    app: ASGIApp


def default_rate_limiter() -> RateLimiter:
    config = get_security_config()
    return InMemoryRateLimiter(per_minute=config.rate_limit_per_minute, enabled=config.enable_rate_limiting)


def build_sqlbot_mcp(*, authenticator: Authenticator | None = None, rate_limiter: RateLimiter | None = None,
                     audit: AuditSink | None = None, tool_modules=TOOL_MODULES,
                     transport_security: TransportSecuritySettings | None = None,
                     session_factory: Callable[[], Any] | None = None) -> SqlbotMcp:
    mcp = FastMCP(
        SERVER_NAME,
        instructions=INSTRUCTIONS,
        stateless_http=True,
        json_response=True,
        streamable_http_path="/",
        # Host/Origin checks are done by the deployment (reverse proxy /
        # network policy); requests here are already bearer-authenticated.
        transport_security=transport_security or TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
    runtime = ToolRuntime(rate_limiter=rate_limiter or default_rate_limiter(), audit=audit or SystemLogAuditSink())
    if session_factory is not None:
        runtime.session_factory = session_factory
    register_tools(mcp, runtime, tool_modules)
    app = AuthMiddleware(mcp.streamable_http_app(), authenticator or AgentTokenAuthenticator())
    return SqlbotMcp(mcp=mcp, app=app)


class _TrailingSlash:
    """Serve ``/sqlbot-mcp`` and ``/sqlbot-mcp/`` alike, without a redirect.

    A 307 to the slash form would answer unauthenticated requests before
    ``AuthMiddleware`` runs and breaks clients that do not follow redirects.
    """

    def __init__(self, app: ASGIApp, path: str):
        self.app = app
        self.path = path.rstrip("/")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == self.path:
            scope = dict(scope, path=self.path + "/", raw_path=(self.path + "/").encode())
        await self.app(scope, receive, send)


def mount_sqlbot_mcp(host, server: SqlbotMcp, path: str = DEFAULT_MOUNT_PATH):
    """Mount on a Starlette/FastAPI ``host`` and return the lifespan to enter.

    Returns an async context manager running the MCP session manager; enter it
    from the host's lifespan.
    """
    host.mount(path, server.app)
    host.add_middleware(_TrailingSlash, path=path)

    @contextlib.asynccontextmanager
    async def lifespan():
        async with server.mcp.session_manager.run():
            yield

    return lifespan
