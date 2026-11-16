"""Offline regressions for sqlbot-mcp agent tokens (SQLite, no services)."""

import json

import pytest
import sqlbot_xpack  # noqa: F401  # Initialize the published wheel before app imports.
from sqlalchemy import BigInteger, Column, MetaData, Text
from sqlalchemy.pool import StaticPool
from sqlmodel import Field, Session, SQLModel, create_engine, select

from apps.system.crud import agent_token_manage as tokens
from apps.system.models.system_model import AgentTokenModel, UserWsModel


# Minimal stand-ins on their own metadata: the real user and datasource models
# use PostgreSQL-only column types and must not be redefined.
class _FakeBase(SQLModel):
    metadata = MetaData()


class FakeUser(_FakeBase, table=True):
    __tablename__ = "sys_user"
    id: int = Field(primary_key=True)
    account: str = "u"
    name: str = "u"
    oid: int = 1
    status: int = 1


class FakeDatasource(_FakeBase, table=True):
    __tablename__ = "core_datasource"
    id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    oid: int = Field(sa_column=Column(BigInteger()))
    name: str = Field(sa_column=Column(Text), default="ds")


@pytest.fixture
def session(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(engine, tables=[AgentTokenModel.__table__, UserWsModel.__table__])
    _FakeBase.metadata.create_all(engine)
    monkeypatch.setattr(tokens, "UserModel", FakeUser)
    monkeypatch.setattr(tokens, "CoreDatasource", FakeDatasource)
    with Session(engine) as s:
        s.add(FakeUser(id=2, status=1))
        s.add(UserWsModel(uid=2, oid=10, weight=0))
        s.add(FakeDatasource(id=101, oid=10))
        s.add(FakeDatasource(id=202, oid=99))
        s.commit()
        yield s


def issue(session, **kwargs):
    defaults = {"uid": 2, "oid": 10, "name": "claude"}
    defaults.update(kwargs)
    return tokens.create_token(session, **defaults)


def test_token_format_and_storage(session):
    issued = issue(session)
    assert issued.plain.startswith("sk-sqlbot-")
    assert tokens.parse_prefix(issued.plain) == issued.model.token_prefix
    stored = session.exec(select(AgentTokenModel)).one()
    # Only the digest is persisted.
    assert stored.token_hash == tokens.hash_token(issued.plain)
    assert issued.plain not in json.dumps(stored.model_dump(), default=str)


def test_verify_resolves_owner_workspace_and_scope(session):
    issued = issue(session, ds_ids=[101])
    verified = tokens.verify_token(session, issued.plain)
    assert (verified.uid, verified.oid, verified.allowed_ds_ids) == (2, 10, frozenset({101}))


@pytest.mark.parametrize("mutate", [
    lambda t: t[:-1] + ("A" if t[-1] != "A" else "B"),
    lambda t: "sk-sqlbot-zzzzzzzz-" + t.split("-", 3)[-1],
    lambda t: t.replace("sk-sqlbot-", "sk-other-"),
    lambda t: "",
    lambda t: "Bearer " + t,
])
def test_tampered_tokens_are_rejected(session, mutate):
    issued = issue(session)
    assert tokens.verify_token(session, mutate(issued.plain)) is None


def test_disabled_or_deleted_tokens_are_rejected(session):
    issued = issue(session)
    tokens.set_token_status(session, uid=2, token_id=issued.model.id, status=False)
    assert tokens.verify_token(session, issued.plain) is None
    tokens.set_token_status(session, uid=2, token_id=issued.model.id, status=True)
    assert tokens.verify_token(session, issued.plain) is not None
    tokens.delete_token(session, uid=2, token_id=issued.model.id)
    assert tokens.verify_token(session, issued.plain) is None


def test_owner_disabled_or_removed_from_workspace_invalidates_token(session):
    issued = issue(session)
    user = session.get(FakeUser, 2)
    user.status = 0
    session.add(user)
    session.commit()
    assert tokens.verify_token(session, issued.plain) is None
    user.status = 1
    session.add(user)
    for ws in session.exec(select(UserWsModel)).all():
        session.delete(ws)
    session.commit()
    assert tokens.verify_token(session, issued.plain) is None


def test_users_cannot_manage_other_users_tokens(session):
    issued = issue(session)
    for action in (
        lambda: tokens.set_token_status(session, uid=3, token_id=issued.model.id, status=False),
        lambda: tokens.delete_token(session, uid=3, token_id=issued.model.id),
    ):
        with pytest.raises(tokens.AgentTokenError) as info:
            action()
        assert info.value.key == "not_found"
    assert tokens.list_tokens(session, 3) == []
    assert tokens.verify_token(session, issued.plain) is not None


@pytest.mark.parametrize("ds_ids,key", [([202], "datasource_invalid"), ([999], "datasource_invalid"),
                                        ([], "datasource_required")])
def test_scope_must_stay_inside_the_workspace(session, ds_ids, key):
    with pytest.raises(tokens.AgentTokenError) as info:
        issue(session, ds_ids=ds_ids)
    assert info.value.key == key


def test_per_user_limit(session):
    for i in range(tokens.MAX_TOKENS_PER_USER):
        issue(session, name=f"t{i}")
    with pytest.raises(tokens.AgentTokenError) as info:
        issue(session, name="one-too-many")
    assert info.value.key == "limit"


@pytest.mark.parametrize("name", ["", "   ", "x" * 65])
def test_name_is_validated(session, name):
    with pytest.raises(tokens.AgentTokenError):
        issue(session, name=name)


def test_corrupt_scope_never_widens_access():
    assert tokens.load_ds_ids("not json") == frozenset()
    assert tokens.load_ds_ids(None) is None


def test_last_used_is_throttled(session):
    issued = issue(session)
    tokens.touch_token(session, issued.model.id, "1.1.1.1", now_ms=1_000_000)
    tokens.touch_token(session, issued.model.id, "1.1.1.1", now_ms=1_010_000)
    model = session.get(AgentTokenModel, issued.model.id)
    assert model.last_used_time == 1_000_000
    tokens.touch_token(session, issued.model.id, "1.1.1.1", now_ms=1_000_000 + tokens.LAST_USED_WRITE_INTERVAL_MS)
    session.refresh(model)
    assert model.last_used_time == 1_000_000 + tokens.LAST_USED_WRITE_INTERVAL_MS
