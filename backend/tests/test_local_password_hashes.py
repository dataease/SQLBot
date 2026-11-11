"""Real hashing/SQLModel/routes/middleware on synthetic isolated data.

Default: SQLite, no network. Explicit PostgreSQL: SQLBOT_PASSWORD_TEST_PG=1
and SQLBOT_TEST_DATABASE_URL; a unique schema is created and removed. External
crypto and audit sinks are boundaries; production encryption is checked separately.
"""

# isort: skip_file
# Import system routes before MCP: the released xpack imports these routes.
import asyncio
import importlib.util
import io
import os
import uuid
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
import pandas as pd
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import BigInteger, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlmodel import Session, create_engine, select

from apps.system.api import login, user
from apps.mcp import mcp
from apps.system.crud import user as user_crud, user_excel
from apps.system.middleware import auth
from apps.system.models.system_model import AssistantModel, UserWsModel, WorkspaceModel
from apps.system.models.user import UserModel
from common.audit.schemas import logger_decorator
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.config import settings
from common.core.db import get_session
from apps.system.schemas.permission import RequestContextMiddleware
from common.core.response_middleware import exception_handler
from common.core.deps import get_i18n
from common.core.passwords import (
    WRAPPED_MD5,
    hash_password,
    legacy_md5,
    needs_password_upgrade,
    verify_password,
    wrap_legacy_password,
)
from common.core.security import create_access_token
from common.utils.crypto import (
    sqlbot_decrypt as real_decrypt,
    sqlbot_encrypt as real_encrypt,
)
from apps.chat.models.chat_model import Chat
from sqlbot_xpack.config.model import SysArgModel
from sqlbot_xpack.license.model import LicenseModel

PWD = "SyntheticOnly42!"
NEW = "ReplacementOnly42!"
ROOT = Path(__file__).resolve().parents[2]


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, _compiler, **_kw):
    return "JSON"


@compiles(BigInteger, "sqlite")
def sqlite_bigint(_type, _compiler, **_kw):
    return "INTEGER"


def trans(key, **_kwargs):
    return key


@pytest.fixture
def environment(tmp_path, monkeypatch):
    pg = os.environ.get("SQLBOT_PASSWORD_TEST_PG") == "1"
    admin = None
    schema = "password_" + uuid.uuid4().hex
    if pg:
        admin = create_engine(os.environ["SQLBOT_TEST_DATABASE_URL"])
        with admin.begin() as c:
            c.execute(text(f'CREATE SCHEMA "{schema}"'))
        db = create_engine(
            os.environ["SQLBOT_TEST_DATABASE_URL"],
            connect_args={"options": f"-csearch_path={schema}"},
        )
    else:
        db = create_engine(
            f"sqlite:///{tmp_path / 'synthetic.db'}",
            connect_args={"check_same_thread": False},
        )
    try:
        for model in (
            UserModel,
            UserWsModel,
            WorkspaceModel,
            AssistantModel,
            Chat,
            SysArgModel,
            LicenseModel,
        ):
            model.__table__.create(db)
        monkeypatch.setattr(settings, "CACHE_TYPE", "None")
        monkeypatch.setattr(auth, "engine", db)
        monkeypatch.setattr(logger_decorator, "engine", db)
        monkeypatch.setattr(
            logger_decorator.SystemLogger, "create_log_record", AsyncMock()
        )
        # Keep route validation/transactions/auth real; replace only transport crypto.
        monkeypatch.setattr(login, "sqlbot_decrypt", AsyncMock(side_effect=lambda x: x))
        monkeypatch.setattr(
            "common.utils.crypto.sqlbot_decrypt", AsyncMock(side_effect=lambda x: x)
        )

        class Policy:
            @property
            def return_value(self):
                raise AttributeError("write-only test configuration")

            @return_value.setter
            def return_value(self, value):
                with Session(db) as s:
                    row = s.exec(
                        select(SysArgModel).where(
                            SysArgModel.pkey == "login.initial_pwd_disabled"
                        )
                    ).first()
                    if row is None:
                        row = SysArgModel(
                            pkey="login.initial_pwd_disabled", pval="false"
                        )
                    row.pval = str(value).lower()
                    s.add(row)
                    s.commit()

        policy = Policy()
        app = FastAPI()
        app.include_router(login.router, prefix="/api/v1")
        app.include_router(user.router, prefix="/api/v1")
        app.include_router(mcp.router, prefix="/api/v1")
        from fastapi import Request

        @app.get("/api/v1/password-test/identity")
        def identity(request: Request):
            assistant = getattr(request.state, "assistant", None)
            return {
                "uid": request.state.current_user.id,
                "assistant_type": assistant.type if assistant else None,
            }

        app.add_middleware(RequestContextMiddleware)
        app.add_middleware(RequestContextMiddlewareCommon)
        app.add_exception_handler(Exception, exception_handler.global_exception_handler)
        app.add_middleware(auth.TokenMiddleware)

        def sessions():
            with Session(db) as session:
                try:
                    yield session
                    session.commit()
                except Exception:
                    session.rollback()
                    raise

        monkeypatch.setattr("common.core.db.get_session", sessions)
        app.dependency_overrides[get_session] = sessions
        app.dependency_overrides[get_i18n] = lambda: trans
        with Session(db) as s:
            s.add(WorkspaceModel(id=1, name="synthetic"))
            s.commit()
        with TestClient(app, raise_server_exceptions=False) as client:
            yield SimpleNamespace(db=db, client=client, policy=policy)
    finally:
        db.dispose()
        if admin:
            with admin.begin() as c:
                c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()


def seed(env, stored=None, uid=2, **changes):
    values = {
        "id": uid,
        "account": "admin" if uid == 1 else f"audit{uid}",
        "name": f"Synthetic {uid}",
        "email": f"audit{uid}@example.invalid",
        "oid": 1,
        "status": 1,
        "origin": 0,
        "password": stored or legacy_md5(PWD),
    }
    values.update(changes)
    with Session(env.db) as s:
        model = UserModel(**values)
        s.add(model)
        s.add(UserWsModel(uid=uid, oid=1, weight=0))
        s.commit()
    return values["account"]


def stored(env, uid=2):
    with Session(env.db) as s:
        return s.get(UserModel, uid).password


def headers(uid=2):
    return {
        settings.TOKEN_KEY: "Bearer "
        + create_access_token(
            {"id": uid, "account": "admin" if uid == 1 else f"audit{uid}", "oid": 1},
            timedelta(minutes=5),
        )
    }


def log_in(env, account="audit2", password=PWD):
    return env.client.post(
        "/api/v1/login/access-token", data={"username": account, "password": password}
    )


@pytest.mark.parametrize(
    "encode", [legacy_md5, lambda p: wrap_legacy_password(legacy_md5(p)), hash_password]
)
def test_login_compatibility_and_upgrade(environment, encode):
    e = environment
    seed(e, encode(PWD))
    before = stored(e)
    assert log_in(e, password="Incorrect42!").status_code == 400
    assert log_in(e, account="absent").status_code == 400
    assert stored(e) == before
    response = log_in(e)
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]
    after = stored(e)
    assert after.startswith("$argon2id$") and verify_password(PWD, after)
    assert not needs_password_upgrade(after)
    assert log_in(e).status_code == 200
    assert stored(e) == after
    assert PWD not in response.text and "password" not in response.text


@pytest.mark.parametrize("changes", [{"status": 0}, {"oid": 0}, {"origin": 1}])
def test_rejected_local_account_never_upgrades(environment, changes):
    seed(environment, **changes)
    before = stored(environment)
    assert log_in(environment).status_code == 400
    assert stored(environment) == before


@pytest.mark.parametrize(
    "encode", [legacy_md5, lambda p: wrap_legacy_password(legacy_md5(p)), hash_password]
)
def test_initial_policy_and_first_change(environment, encode):
    e = environment
    seed(e, encode(settings.DEFAULT_PWD))
    e.policy.return_value = True
    response = log_in(e, password=settings.DEFAULT_PWD)
    assert response.status_code == 200, response.text
    assert response.json()["need_change_pwd"] is True
    assert response.json()["access_token"] == ""
    before = stored(e)
    payload = {
        "account": "audit2",
        "pwd": settings.DEFAULT_PWD,
        "new_pwd": settings.DEFAULT_PWD,
    }
    assert e.client.post("/api/v1/login/change-pwd", json=payload).status_code == 400
    assert stored(e) == before
    payload["new_pwd"] = NEW
    response = e.client.post("/api/v1/login/change-pwd", json=payload)
    assert response.status_code == 200, response.text
    assert "password" not in response.text
    assert stored(e).startswith("$argon2id$")
    assert log_in(e, password=NEW).json()["access_token"]
    assert log_in(e, password=settings.DEFAULT_PWD).status_code == 400


def test_admin_initial_password_exemption(environment):
    seed(environment, legacy_md5(settings.DEFAULT_PWD), uid=1)
    environment.policy.return_value = True
    assert log_in(environment, "admin", settings.DEFAULT_PWD).json()["access_token"]
    assert stored(environment, 1).startswith("$argon2id$")


@pytest.mark.parametrize(
    "encode", [legacy_md5, lambda p: wrap_legacy_password(legacy_md5(p)), hash_password]
)
def test_modify_reset_and_permissions(environment, encode):
    e = environment
    seed(e, uid=1)
    seed(e, encode(PWD))
    before = stored(e)
    assert (
        e.client.put("/api/v1/user/pwd", json={"pwd": PWD, "new_pwd": NEW}).status_code
        == 401
    )
    denied = e.client.patch("/api/v1/user/pwd/2", headers=headers())
    assert denied.status_code == 500
    assert "管理员" in denied.text or "admin" in denied.text.lower()
    assert stored(e) == before
    for old, new in [("Incorrect42!", NEW), (PWD, "weak")]:
        assert (
            e.client.put(
                "/api/v1/user/pwd", headers=headers(), json={"pwd": old, "new_pwd": new}
            ).status_code
            != 200
        )
        assert stored(e) == before
    response = e.client.put(
        "/api/v1/user/pwd", headers=headers(), json={"pwd": PWD, "new_pwd": NEW}
    )
    assert response.status_code == 200, response.text
    assert "password" not in response.text
    assert log_in(e, password=PWD).status_code == 400
    assert log_in(e, password=NEW).status_code == 200
    for _ in range(2):
        prev = stored(e)
        response = e.client.patch("/api/v1/user/pwd/2", headers=headers(1))
        assert response.status_code == 200, response.text
        assert stored(e) != prev
        assert stored(e).startswith("$argon2id$")
        assert verify_password(settings.DEFAULT_PWD, stored(e))
    # Existing signed session still authenticates after credential replacement.
    assert e.client.get("/api/v1/user/ws", headers=headers()).status_code == 200


def test_create_import_and_no_digest_response(environment):
    e = environment
    seed(e, uid=1)
    response = e.client.post(
        "/api/v1/user",
        headers=headers(1),
        json={
            "account": "created",
            "name": "Created",
            "email": "created@example.invalid",
            "oid": 1,
            "oid_list": [1],
        },
    )
    assert response.status_code == 200, response.text
    assert "password" not in response.text
    with Session(e.db) as s:
        created = s.exec(select(UserModel).where(UserModel.account == "created")).one()
        assert created.password.startswith("$argon2id$")
        first = created.password
    # Exercise actual Excel parser/validators/model defaults, not a stub row.
    cols = [
        "account",
        "name",
        "email",
        "workspace",
        "role",
        "status",
        "origin",
        "platform_user_id",
    ]
    frame = pd.DataFrame(
        [
            [
                "imported",
                "Imported",
                "imported@example.invalid",
                "",
                "",
                "已启用",
                "本地创建",
                "",
            ]
        ],
        columns=cols,
    )
    buffer = io.BytesIO()
    frame.to_excel(buffer, index=False)
    buffer.seek(0)
    buffer.filename = "synthetic.xlsx"

    def translation(key):
        return key.split(".")[-1]

    with Session(e.db) as s:
        result = asyncio.run(user_excel.batchUpload(s, translation, buffer))
        assert result.successCount == 1
        imported = s.exec(
            select(UserModel).where(UserModel.account == "imported")
        ).one()
        assert imported.password.startswith("$argon2id$")
        assert imported.password != first
        assert verify_password(settings.DEFAULT_PWD, imported.password)


@pytest.mark.parametrize(
    "encode", [legacy_md5, lambda p: wrap_legacy_password(legacy_md5(p)), hash_password]
)
def test_mcp_password_and_existing_token(environment, encode):
    e = environment
    seed(e, encode(PWD))
    before = stored(e)
    response = e.client.post(
        "/api/v1/mcp/access_token",
        json={"username": "audit2", "password": "Incorrect42!"},
    )
    assert response.status_code == 400 and stored(e) == before
    response = e.client.post(
        "/api/v1/mcp/access_token", json={"username": "audit2", "password": PWD}
    )
    assert response.status_code == 200, response.text
    assert stored(e).startswith("$argon2id$")
    with Session(e.db) as s:
        assert mcp.get_user(s, response.json()["access_token"]).id == 2


def test_concurrent_reset_is_not_overwritten(environment):
    e = environment
    seed(e)
    with Session(e.db) as s:
        old = user_crud.get_user_by_account(session=s, account="audit2")
    reset = hash_password(NEW)
    with Session(e.db) as s:
        s.execute(update(UserModel).where(UserModel.id == 2).values(password=reset))
        s.commit()
    with Session(e.db) as s:
        user_crud.upgrade_password(session=s, user=old, password=PWD)
        s.commit()
    assert stored(e) == reset


def test_storage_properties_and_corrupt_formats():
    a, b = hash_password(PWD), hash_password(PWD)
    assert a != b and len(a) <= 255
    wrapped = wrap_legacy_password(legacy_md5(PWD))
    assert len(wrapped) <= 255 and verify_password(PWD, wrapped)
    assert not verify_password(legacy_md5(PWD), wrapped)
    for invalid in [
        "",
        "plaintext",
        "$argon2id$broken",
        WRAPPED_MD5,
        a.replace("m=19456", "m=999999999"),
        "A" * 32,
        None,
    ]:
        assert not verify_password(PWD, invalid)


def test_migration_resumable_and_preserves_changed_password(environment, monkeypatch):
    e = environment
    seed(e, legacy_md5(NEW), uid=1)
    seed(e, uid=2)
    seed(e, hash_password(PWD), uid=3)
    spec = importlib.util.spec_from_file_location(
        "password_migration",
        ROOT / "backend/alembic/versions/075_local_password_hashes.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    original_new = stored(e, 3)
    with e.db.connect() as c:
        context = MigrationContext.configure(c, opts={"transactional_ddl": True})
        with context.begin_transaction():
            monkeypatch.setattr(migration, "op", Operations(context))
            monkeypatch.setattr(migration, "BATCH_SIZE", 1)
            migration.upgrade()
    assert stored(e, 1).startswith(WRAPPED_MD5) and verify_password(NEW, stored(e, 1))
    assert not verify_password(settings.DEFAULT_PWD, stored(e, 1))
    assert stored(e).startswith(WRAPPED_MD5)
    assert stored(e, 3) == original_new
    before = [stored(e, i) for i in (1, 2, 3)]
    with e.db.connect() as c:
        context = MigrationContext.configure(c, opts={"transactional_ddl": True})
        with context.begin_transaction():
            monkeypatch.setattr(migration, "op", Operations(context))
            migration.upgrade()
            migration.downgrade()
    assert [stored(e, i) for i in (1, 2, 3)] == before
    assert log_in(e, "admin", NEW).status_code == 200


def test_real_encrypted_login_transport(environment, monkeypatch):
    e = environment
    seed(e)
    monkeypatch.setattr(login, "sqlbot_decrypt", real_decrypt)
    monkeypatch.setattr("common.utils.crypto.sqlbot_decrypt", real_decrypt)
    from sqlbot_xpack.config import rsa_manage
    from sqlbot_xpack.config.model import RsaModel

    RsaModel.__table__.create(e.db)

    def sessions():
        with Session(e.db) as session:
            yield session

    monkeypatch.setattr(rsa_manage, "dynamic_get_session", lambda: sessions)
    rsa_manage.get_rsa_keypair().rsa_key_check()
    account = asyncio.run(real_encrypt("audit2"))
    password = asyncio.run(real_encrypt(PWD))
    assert account != "audit2" and password != PWD
    response = log_in(e, account, password)
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]
    assert stored(e).startswith("$argon2id$")


@pytest.mark.parametrize(
    "encode", [legacy_md5, lambda p: wrap_legacy_password(legacy_md5(p)), hash_password]
)
def test_mcp_start_persists_chat_and_upgrades(environment, encode):
    e = environment
    seed(e, encode(PWD))
    response = e.client.post(
        "/api/v1/mcp/mcp_start", json={"username": "audit2", "password": PWD}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"] and body["chat_id"]
    assert stored(e).startswith("$argon2id$")
    response = e.client.post(
        "/api/v1/mcp/mcp_start", json={"token": body["access_token"]}
    )
    assert response.status_code == 200, response.text


@pytest.mark.parametrize("endpoint", ["access_token", "mcp_start"])
@pytest.mark.parametrize("changes", [{"status": 0}, {"origin": 1}, {"oid": 0}])
def test_mcp_ineligible_credentials_never_upgrade(environment, endpoint, changes):
    e = environment
    seed(e, **changes)
    before = stored(e)
    response = e.client.post(
        f"/api/v1/mcp/{endpoint}", json={"username": "audit2", "password": PWD}
    )
    # mcp_start's existing save_on_success_only audit wrapper suppresses an
    # exception into null; either way it must never yield a token or write.
    assert response.status_code == 400 or response.json() is None
    assert stored(e) == before


@pytest.mark.parametrize(
    "encode", [legacy_md5, lambda p: wrap_legacy_password(legacy_md5(p)), hash_password]
)
def test_embedded_and_assistant_tokens_survive_hash_changes(environment, encode):
    e = environment
    seed(e, encode(PWD))
    seed(e, uid=1)
    secret = "synthetic-embedded-secret-" + uuid.uuid4().hex
    with Session(e.db) as s:
        for aid, typ in [(7, 4), (8, 0), (9, 1)]:
            s.add(
                AssistantModel(
                    id=aid,
                    name=f"Synthetic app {aid}",
                    type=typ,
                    domain="http://example.invalid",
                    app_secret=secret,
                    oid=1,
                )
            )
        s.commit()
    endpoint = "/api/v1/password-test/identity"

    def embedded(account="audit2", aid=7, key=secret):
        token = jwt.encode(
            {"account": account, "embeddedId": aid, "appId": "synthetic"},
            key,
            algorithm="HS256",
        )
        return {settings.ASSISTANT_TOKEN_KEY: "Embedded " + token}

    initial = embedded()
    assert e.client.get(endpoint, headers=initial).status_code == 200
    assert log_in(e).status_code == 200
    assert e.client.get(endpoint, headers=initial).json()["uid"] == 2
    for invalid in [
        embedded("admin"),
        embedded(aid=8),
        embedded(key="wrong-synthetic-signature-key-123456"),
    ]:
        assert e.client.get(endpoint, headers=invalid).status_code == 401
    # Ordinary and advanced assistants use their own signed identity, independent
    # of local password storage. Exercise actual middleware and assistant lookup.
    for aid in [8, 9]:
        token = create_access_token(
            {"id": -1, "assistant_id": aid, "oid": 1}, timedelta(minutes=5)
        )
        response = e.client.get(
            endpoint, headers={settings.ASSISTANT_TOKEN_KEY: "Assistant " + token}
        )
        assert response.status_code == 200, response.text
        assert response.json()["assistant_type"] in (0, 1)
    with Session(e.db) as s:
        s.execute(update(UserModel).where(UserModel.id == 2).values(status=0))
        s.commit()
    assert e.client.get(endpoint, headers=initial).status_code == 401


def test_historical_admin_initialization_then_migration(environment, monkeypatch):
    e = environment

    def migration_file(filename, name):
        spec = importlib.util.spec_from_file_location(
            name, ROOT / "backend/alembic/versions" / filename
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    init = migration_file("001_ddl.py", "historical_user_init")
    upgrade = migration_file("075_local_password_hashes.py", "password_upgrade_init")
    # Only the historical user initialization and this data migration; the full
    # migration chain is checked separately. No existing application rows exist.
    UserModel.__table__.drop(e.db)
    with e.db.connect() as c:
        context = MigrationContext.configure(c, opts={"transactional_ddl": True})
        with context.begin_transaction():
            monkeypatch.setattr(init, "op", Operations(context))
            init.upgrade()
            monkeypatch.setattr(upgrade, "op", Operations(context))
            upgrade.upgrade()
        value = c.scalar(text("SELECT password FROM sys_user WHERE id=1"))
        assert value.startswith(WRAPPED_MD5)
        assert verify_password("SQLBot@123456", value)


def test_migration_interruption_is_resumable(environment, monkeypatch):
    e = environment
    seed(e, uid=1)
    seed(e, uid=2)
    spec = importlib.util.spec_from_file_location(
        "password_interrupted",
        ROOT / "backend/alembic/versions/075_local_password_hashes.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    calls = 0

    def interrupt(stored):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("synthetic interruption")
        return wrap_legacy_password(stored)

    monkeypatch.setattr(migration, "wrap_legacy_password", interrupt)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        with e.db.connect() as c:
            context = MigrationContext.configure(c, opts={"transactional_ddl": True})
            with context.begin_transaction():
                monkeypatch.setattr(migration, "op", Operations(context))
                migration.upgrade()
    first = stored(e, 1)
    assert first.startswith(WRAPPED_MD5)
    assert stored(e) == legacy_md5(PWD)
    monkeypatch.setattr(migration, "wrap_legacy_password", wrap_legacy_password)
    with e.db.connect() as c:
        context = MigrationContext.configure(c, opts={"transactional_ddl": True})
        with context.begin_transaction():
            monkeypatch.setattr(migration, "op", Operations(context))
            migration.upgrade()
    assert stored(e, 1) == first
    assert stored(e).startswith(WRAPPED_MD5)


@pytest.mark.skipif(
    os.environ.get("SQLBOT_PASSWORD_TEST_PG") != "1",
    reason="full migration chain requires explicit isolated PostgreSQL opt-in",
)
def test_full_fresh_install_and_upgrade_head(environment, monkeypatch):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.engine import make_url

    e = environment
    with e.db.begin() as c:
        schema = c.scalar(text("SELECT current_schema()"))
        assert schema.startswith("password_") and len(schema) == 41
        c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        c.execute(text(f'CREATE SCHEMA "{schema}"'))
        assert (
            c.scalar(text("SELECT count(*) FROM pg_extension WHERE extname='vector'"))
            == 1
        )
    uri = make_url(os.environ["SQLBOT_TEST_DATABASE_URL"]).update_query_dict(
        {"options": f"-csearch_path={schema}"}
    )
    monkeypatch.setattr(
        settings, "SQLBOT_DB_URL", uri.render_as_string(hide_password=False)
    )
    config = Config(str(ROOT / "backend/alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "backend/alembic"))
    # Qualify only the already-installed vector type, never shared app tables.
    from pgvector.sqlalchemy import VECTOR

    original_spec = VECTOR.get_col_spec
    monkeypatch.setattr(
        VECTOR, "get_col_spec", lambda self, **kw: "public." + original_spec(self, **kw)
    )
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    def guard_schema(
        connection, cursor, _statement, _parameters, _context, _executemany
    ):
        if connection.info.get("password_test_schema") != schema:
            check = cursor.connection.cursor()
            try:
                check.execute("SELECT current_schema(), current_setting('search_path')")
                assert check.fetchone() == (schema, schema), (
                    "Refusing a non-isolated migration connection"
                )
            finally:
                check.close()
            connection.info["password_test_schema"] = schema

    event.listen(Engine, "before_cursor_execute", guard_schema)
    try:
        command.upgrade(config, "head")
    finally:
        event.remove(Engine, "before_cursor_execute", guard_schema)
    with e.db.connect() as c:
        assert (
            c.scalar(text("SELECT version_num FROM alembic_version")) == "d91543ca7b21"
        )
        value = c.scalar(text("SELECT password FROM sys_user WHERE id=1"))
        assert value.startswith(WRAPPED_MD5)
        assert verify_password("SQLBot@123456", value)
        assert (
            c.scalar(
                text("SELECT count(*) FROM sys_user WHERE password ~ '^[0-9a-f]{32}$'")
            )
            == 0
        )
    command.downgrade(config, "-1")
    with e.db.connect() as c:
        assert c.scalar(text("SELECT password FROM sys_user WHERE id=1")) == value
    command.upgrade(config, "head")
    with e.db.connect() as c:
        assert c.scalar(text("SELECT password FROM sys_user WHERE id=1")) == value


@pytest.mark.skipif(
    os.environ.get("SQLBOT_PASSWORD_TEST_PG") != "1", reason="PostgreSQL schema guard"
)
def test_migration_requires_users_in_current_schema(environment, monkeypatch):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    e = environment
    UserModel.__table__.drop(e.db)
    spec = importlib.util.spec_from_file_location(
        "password_schema_guard",
        ROOT / "backend/alembic/versions/075_local_password_hashes.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with e.db.connect() as c:
        context = MigrationContext.configure(c, opts={"transactional_ddl": True})
        with context.begin_transaction():
            monkeypatch.setattr(migration, "op", Operations(context))
            with pytest.raises(RuntimeError, match="current migration schema"):
                migration.upgrade()


def test_user_list_and_default_helpers_do_not_expose_digests(environment):
    from common.core.security import (
        default_password_hash,
        default_md5_pwd,
        verify_md5pwd,
    )

    e = environment
    seed(e, uid=1)
    seed(e, hash_password(PWD), uid=2)
    response = e.client.get("/api/v1/user/pager/1/10", headers=headers(1))
    # The existing route name is asserted rather than accepting a missing route.
    assert response.status_code == 200, response.text
    assert "password" not in response.text
    a, b = default_password_hash(), default_md5_pwd()
    assert a != b and a.startswith("$argon2id$") and b.startswith("$argon2id$")
    assert verify_md5pwd(settings.DEFAULT_PWD, a)
