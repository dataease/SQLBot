"""Agent access tokens for the SQLBot MCP server.

Format: ``sk-sqlbot-<prefix>-<secret>``. ``prefix`` (8 url-safe chars) locates
the row; only ``sha256(token)`` is stored and compared in constant time.
Plain tokens exist only in the create response.
"""

import hashlib
import hmac
import json
import secrets
import string
import time
from dataclasses import dataclass

from sqlmodel import Session, func, select

from apps.datasource.models.datasource import CoreDatasource
from apps.system.models.system_model import AgentTokenModel, UserWsModel
from apps.system.models.user import UserModel
from common.utils.time import get_timestamp

TOKEN_SCHEME = "sk-sqlbot-"
PREFIX_LENGTH = 8
MAX_TOKENS_PER_USER = 5
# ``last_used_*`` is refreshed at most this often per token.
LAST_USED_WRITE_INTERVAL_MS = 60 * 1000

_PREFIX_ALPHABET = string.ascii_lowercase + string.digits


class AgentTokenError(ValueError):
    """Business rule violation; ``key`` is an i18n key under ``i18n_agent_token``."""

    def __init__(self, key: str, **params):
        super().__init__(key)
        self.key = key
        self.params = params


@dataclass(frozen=True)
class IssuedToken:
    model: AgentTokenModel
    plain: str


@dataclass(frozen=True)
class VerifiedToken:
    """What a valid token resolves to; consumers never see the digest."""

    token_id: int
    name: str
    uid: int
    oid: int
    allowed_ds_ids: frozenset[int] | None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_token() -> tuple[str, str]:
    prefix = "".join(secrets.choice(_PREFIX_ALPHABET) for _ in range(PREFIX_LENGTH))
    return prefix, f"{TOKEN_SCHEME}{prefix}-{secrets.token_urlsafe(32)}"


def parse_prefix(token: str) -> str | None:
    if not token or not token.startswith(TOKEN_SCHEME):
        return None
    rest = token[len(TOKEN_SCHEME):]
    prefix, sep, secret = rest.partition("-")
    if not sep or len(prefix) != PREFIX_LENGTH or not secret:
        return None
    if any(c not in _PREFIX_ALPHABET for c in prefix):
        return None
    return prefix


def dump_ds_ids(ds_ids: list[int] | None) -> str | None:
    if ds_ids is None:
        return None
    return json.dumps(sorted({str(int(i)) for i in ds_ids}))


def load_ds_ids(raw: str | None) -> frozenset[int] | None:
    if raw is None:
        return None
    try:
        return frozenset(int(i) for i in json.loads(raw))
    except (ValueError, TypeError):
        # A corrupt scope must never widen access: allow nothing.
        return frozenset()


def _validate_scope(session: Session, oid: int, ds_ids: list[int] | None) -> None:
    if ds_ids is None:
        return
    if not ds_ids:
        raise AgentTokenError("datasource_required")
    wanted = {int(i) for i in ds_ids}
    found = set(session.exec(
        select(CoreDatasource.id).where(CoreDatasource.id.in_(wanted), CoreDatasource.oid == oid)
    ).all())
    if found != wanted:
        raise AgentTokenError("datasource_invalid")


def list_tokens(session: Session, uid: int) -> list[AgentTokenModel]:
    stmt = select(AgentTokenModel).where(AgentTokenModel.uid == uid).order_by(AgentTokenModel.create_time.desc())
    return list(session.exec(stmt).all())


def create_token(session: Session, *, uid: int, oid: int, name: str,
                 ds_ids: list[int] | None = None) -> IssuedToken:
    name = (name or "").strip()
    if not name or len(name) > 64:
        raise AgentTokenError("name_invalid")
    if not oid:
        raise AgentTokenError("workspace_required")
    count = session.exec(select(func.count()).select_from(AgentTokenModel)
                         .where(AgentTokenModel.uid == uid)).one()
    if count >= MAX_TOKENS_PER_USER:
        raise AgentTokenError("limit", limit=MAX_TOKENS_PER_USER)
    _validate_scope(session, oid, ds_ids)

    for _ in range(5):
        prefix, plain = generate_token()
        exists = session.exec(select(AgentTokenModel.id).where(AgentTokenModel.token_prefix == prefix)).first()
        if not exists:
            break
    else:  # pragma: no cover - 36^8 prefixes make this practically unreachable
        raise AgentTokenError("generate_failed")

    model = AgentTokenModel(
        name=name, uid=uid, oid=oid, token_prefix=prefix, token_hash=hash_token(plain),
        status=True, allowed_ds_ids=dump_ds_ids(ds_ids), create_time=get_timestamp(),
    )
    session.add(model)
    session.commit()
    session.refresh(model)
    return IssuedToken(model=model, plain=plain)


def _owned(session: Session, uid: int, token_id: int) -> AgentTokenModel:
    model = session.get(AgentTokenModel, token_id)
    # Same error for "missing" and "someone else's" so ids cannot be probed.
    if not model or model.uid != uid:
        raise AgentTokenError("not_found")
    return model


def set_token_status(session: Session, *, uid: int, token_id: int, status: bool) -> AgentTokenModel:
    model = _owned(session, uid, token_id)
    if model.status != status:
        model.status = status
        session.add(model)
        session.commit()
        session.refresh(model)
    return model


def delete_token(session: Session, *, uid: int, token_id: int) -> AgentTokenModel:
    model = _owned(session, uid, token_id)
    snapshot = AgentTokenModel.model_validate(model.model_dump())
    session.delete(model)
    session.commit()
    return snapshot


def verify_token(session: Session, token: str) -> VerifiedToken | None:
    """Return the token's identity, or ``None`` for any invalid/disabled token."""
    prefix = parse_prefix(token)
    if prefix is None:
        return None
    model = session.exec(select(AgentTokenModel).where(AgentTokenModel.token_prefix == prefix)).first()
    if model is None:
        # Compare anyway so timing does not reveal whether the prefix exists.
        hmac.compare_digest(hash_token(token), "0" * 64)
        return None
    if not hmac.compare_digest(hash_token(token), model.token_hash):
        return None
    if not model.status:
        return None
    user = session.get(UserModel, model.uid)
    if user is None or user.status != 1:
        return None
    if model.uid != 1:  # the built-in admin may use every workspace
        member = session.exec(select(UserWsModel.id).where(
            UserWsModel.uid == model.uid, UserWsModel.oid == model.oid)).first()
        if member is None:
            return None
    return VerifiedToken(token_id=model.id, name=model.name, uid=model.uid, oid=model.oid,
                         allowed_ds_ids=load_ds_ids(model.allowed_ds_ids))


def touch_token(session: Session, token_id: int, ip: str | None, *, now_ms: int | None = None) -> None:
    """Record last use, throttled so every tool call does not write a row."""
    now_ms = now_ms if now_ms is not None else int(time.time() * 1000)
    model = session.get(AgentTokenModel, token_id)
    if model is None:
        return
    if model.last_used_time and now_ms - model.last_used_time < LAST_USED_WRITE_INTERVAL_MS \
            and model.last_used_ip == ip:
        return
    model.last_used_time = now_ms
    model.last_used_ip = (ip or "")[:64] or None
    session.add(model)
    session.commit()
