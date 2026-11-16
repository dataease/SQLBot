"""Shared plumbing for SQLBot MCP tools.

A tool is a plain async function that receives the authenticated principal
implicitly and calls ``run_in_session`` for database work. Add a tool by
creating a module that defines ``register(mcp, runtime)`` and listing it in
``tools/__init__.py``.
"""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from mcp.server.fastmcp.exceptions import ToolError as McpToolError
from sqlmodel import Session

from apps.mcp.sqlbot_mcp.auth import AgentPrincipal, current_principal
from apps.mcp.sqlbot_mcp.ratelimit import RateLimited, RateLimiter
from apps.mcp.sqlbot_mcp.service import ToolError
from common.core.db import engine
from common.utils.utils import SQLBotLogUtil

T = TypeVar("T")


class AuditSink:
    """Records tool calls. Replace to ship audit events elsewhere."""

    def record(self, *, principal: AgentPrincipal, tool: str, ok: bool, duration_ms: int,
               detail: str | None = None, resource_id: str | None = None) -> None:  # pragma: no cover
        raise NotImplementedError


@dataclass
class ToolRuntime:
    rate_limiter: RateLimiter
    audit: AuditSink
    session_factory: Callable[[], Session] = lambda: Session(engine)


async def run_tool(runtime: ToolRuntime, tool: str, work: Callable[[Session, AgentPrincipal], T],
                   *, audit: bool = False, resource_id: Callable[[T], str | None] = lambda _: None,
                   heavy: bool = False) -> T:
    """Authenticate, rate-limit, run ``work`` in a thread, audit, map errors."""
    principal = current_principal()
    try:
        slot = runtime.rate_limiter.acquire(principal.credential_kind, principal.credential_id, heavy=heavy)
    except RateLimited as e:
        raise McpToolError(str(e))
    started = time.monotonic()
    ok, detail, result = False, None, None
    try:
        result = await asyncio.to_thread(_in_session, runtime, principal, work)
        ok = True
        return result
    except ToolError as e:
        detail = f"{e.code}: {e.message}"
        raise McpToolError(e.message)
    except McpToolError:
        raise
    except Exception as e:
        SQLBotLogUtil.exception(f"[sqlbot-mcp] tool {tool} failed")
        detail = f"internal: {type(e).__name__}"
        raise McpToolError("Internal error")
    finally:
        slot.release()
        if audit or not ok:
            try:
                runtime.audit.record(principal=principal, tool=tool, ok=ok,
                                     duration_ms=int((time.monotonic() - started) * 1000), detail=detail,
                                     resource_id=resource_id(result) if ok else None)
            except Exception:
                SQLBotLogUtil.exception("[sqlbot-mcp] audit failed")


def _in_session(runtime: ToolRuntime, principal: AgentPrincipal, work: Callable[[Session, AgentPrincipal], Any]):
    with runtime.session_factory() as session:
        return work(session, principal)
