"""Authentication for the SQLBot MCP server.

An ``Authenticator`` turns an incoming HTTP request into an ``AgentPrincipal``
(or rejects it). Tools and services only depend on ``AgentPrincipal``, so a new
scheme (e.g. OAuth 2.1) is a new ``Authenticator`` and no tool changes.

``AuthMiddleware`` runs the authenticator for every request to the MCP mount
and exposes the principal through a context variable; the value is inherited
by ``asyncio.to_thread`` workers.
"""

import asyncio
import contextvars
from dataclasses import dataclass
from typing import Protocol

from sqlmodel import Session, select
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from apps.system.crud import agent_token_manage as tokens
from apps.system.models.system_model import UserWsModel
from apps.system.models.user import UserModel
from apps.system.schemas.system_schema import UserInfoDTO
from common.core.db import engine
from common.utils.utils import SQLBotLogUtil


@dataclass(frozen=True)
class AgentPrincipal:
    """Who is calling, and what their credential narrows access to."""

    user: UserInfoDTO
    credential_id: str
    credential_kind: str
    # ``None`` follows the user's datasource permissions.
    allowed_ds_ids: frozenset[int] | None = None
    client_ip: str | None = None

    @property
    def oid(self) -> int:
        return self.user.oid

    def allows_datasource(self, ds_id: int) -> bool:
        return self.allowed_ds_ids is None or int(ds_id) in self.allowed_ds_ids


class AuthenticationFailed(Exception):
    pass


class Authenticator(Protocol):
    async def authenticate(self, request: Request) -> AgentPrincipal:
        """Return the caller or raise ``AuthenticationFailed``."""


_principal: contextvars.ContextVar[AgentPrincipal | None] = contextvars.ContextVar(
    "sqlbot_mcp_principal", default=None)


def current_principal() -> AgentPrincipal:
    principal = _principal.get()
    if principal is None:
        # Tools must never run without an authenticated caller.
        raise PermissionError("Not authenticated")
    return principal


def client_ip(request: Request) -> str | None:
    for header in ("x-real-ip", "x-forwarded-for", "x-client-ip"):
        value = request.headers.get(header)
        if value:
            return value.split(",")[0].strip()[:64]
    return request.client.host if request.client else None


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


class AgentTokenAuthenticator:
    """``Authorization: Bearer sk-sqlbot-...`` tokens issued to a SQLBot user."""

    kind = "agent_token"

    async def authenticate(self, request: Request) -> AgentPrincipal:
        token = bearer_token(request)
        if not token:
            raise AuthenticationFailed("missing bearer token")
        ip = client_ip(request)
        verified, user = await asyncio.to_thread(self._verify, token, ip)
        if verified is None or user is None:
            raise AuthenticationFailed("invalid token")
        return AgentPrincipal(user=user, credential_id=str(verified.token_id), credential_kind=self.kind,
                              allowed_ds_ids=verified.allowed_ds_ids, client_ip=ip)

    @staticmethod
    def _verify(token: str, ip: str | None):
        with Session(engine) as session:
            verified = tokens.verify_token(session, token)
            if verified is None:
                return None, None
            user = load_principal_user(session, verified.uid, verified.oid)
            if user is None:
                return None, None
            try:
                tokens.touch_token(session, verified.token_id, ip)
            except Exception:
                SQLBotLogUtil.exception("Failed to record agent token usage")
            return verified, user


def load_principal_user(session: Session, uid: int, oid: int) -> UserInfoDTO | None:
    """Build the caller's identity in workspace ``oid`` straight from the database.

    Mirrors ``get_user_info`` but is not cached, so disabling a user or removing
    them from the workspace takes effect on the next tool call. The token is
    bound to one workspace: the caller acts there, whatever workspace they last
    selected in the web UI.
    """
    db_user = session.get(UserModel, uid)
    if db_user is None or db_user.status != 1:
        return None
    user = UserInfoDTO.model_validate(db_user.model_dump())
    user.isAdmin = user.id == 1 and user.account == "admin"
    user.oid = oid
    if user.isAdmin:
        return user
    membership = session.exec(select(UserWsModel).where(UserWsModel.uid == uid, UserWsModel.oid == oid)).first()
    if membership is None:
        return None
    user.weight = membership.weight
    return user


class AuthMiddleware:
    """Reject unauthenticated requests before they reach the MCP transport."""

    def __init__(self, app: ASGIApp, authenticator: Authenticator):
        self.app = app
        self.authenticator = authenticator

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope, receive)
        try:
            principal = await self.authenticator.authenticate(request)
        except AuthenticationFailed:
            response = JSONResponse({"error": "invalid_token", "error_description": "Authentication required"},
                                    status_code=401, headers={"WWW-Authenticate": 'Bearer realm="sqlbot-mcp"'})
            await response(scope, receive, send)
            return
        token = _principal.set(principal)
        try:
            await self.app(scope, receive, send)
        finally:
            _principal.reset(token)
