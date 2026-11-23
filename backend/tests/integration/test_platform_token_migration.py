"""Explicit PostgreSQL regression using only disposable random schemas.

SQLBOT_TEST_DATABASE_URL must be supplied deliberately. No default database or
application configuration is loaded. Optional XPACK_TEST_ROOT enables the real
cache function bodies with synthetic provider responses.
"""

import ast
import asyncio
import hashlib
import importlib.util
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy.exc import DataError, SQLAlchemyError
from sqlmodel import Session, select

BACKEND = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    os.environ.get("SQLBOT_PLATFORM_TOKEN_TEST_PG") != "1"
    or not os.environ.get("SQLBOT_TEST_DATABASE_URL"),
    reason="Explicit isolated PostgreSQL test database required",
)


def migration(filename):
    spec = importlib.util.spec_from_file_location(
        filename, BACKEND / "alembic/versions" / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def migrate(engine, filename, direction):
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            getattr(migration(filename), direction)()


@pytest.fixture
def db():
    url = os.environ["SQLBOT_TEST_DATABASE_URL"]
    schema = "platform_token_" + uuid.uuid4().hex
    admin = sa.create_engine(url)
    with admin.begin() as conn:
        conn.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine = sa.create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        migrate(engine, "060_platform_token_ddl.py", "upgrade")
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as conn:
            conn.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_upgrade_preserves_all_platforms_and_downgrade_refuses_truncation(db):
    legacy = [
        {"id": i, "token": "synthetic-" + str(i), "created": 17, "expires": 29}
        for i in range(6, 10)
    ]
    with db.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO sys_platform_token VALUES (:id,:token,:created,:expires)"
            ),
            legacy,
        )
    payload = json.dumps(
        {"version": 1, "credential_fingerprint": "f" * 64, "access_token": "x" * 512}
    )
    with pytest.raises(DataError):
        with db.begin() as conn:
            conn.execute(
                sa.text("UPDATE sys_platform_token SET token=:value WHERE id=6"),
                {"value": payload},
            )
    migrate(db, "077_platform_token_text.py", "upgrade")
    with db.begin() as conn:
        assert conn.execute(
            sa.text(
                "SELECT id,token,create_time,exp_time FROM sys_platform_token ORDER BY id"
            )
        ).all() == [(r["id"], r["token"], 17, 29) for r in legacy]
        conn.execute(
            sa.text("UPDATE sys_platform_token SET token=:value WHERE id=6"),
            {"value": payload},
        )
    with pytest.raises(RuntimeError, match="values exceed 255 characters"):
        migrate(db, "077_platform_token_text.py", "downgrade")
    with db.begin() as conn:
        assert (
            conn.execute(
                sa.text("SELECT token FROM sys_platform_token WHERE id=6")
            ).scalar_one()
            == payload
        )
        conn.execute(
            sa.text("UPDATE sys_platform_token SET token=:value WHERE id=6"),
            {"value": "界" * 255},
        )
    migrate(db, "077_platform_token_text.py", "downgrade")
    column = next(
        c
        for c in sa.inspect(db).get_columns("sys_platform_token")
        if c["name"] == "token"
    )
    assert column["type"].length == 255
    assert column["nullable"] is False
    migrate(db, "077_platform_token_text.py", "upgrade")
    with db.connect() as conn:
        assert (
            conn.execute(
                sa.text("SELECT token FROM sys_platform_token WHERE id=6")
            ).scalar_one()
            == "界" * 255
        )
    assert sa.inspect(db).get_pk_constraint("sys_platform_token")[
        "constrained_columns"
    ] == ["id"]
    assert any(
        i["column_names"] == ["id"]
        for i in sa.inspect(db).get_indexes("sys_platform_token")
    )


def test_real_cache_writes_long_tokens_refreshes_and_preserves_fingerprints(db):
    source_root = os.environ.get("XPACK_TEST_ROOT")
    if not source_root:
        pytest.skip("Explicit extension source needed for cache integration")
    from sqlbot_xpack.platform.dto.platform_models import SysPlatformTokenModel

    from apps.system.models.system_model import AuthenticationModel

    AuthenticationModel.__table__.create(db)
    good = {
        "corpid": "synthetic-corp",
        "corpsecret": "synthetic-secret",
        "agent_id": "1001",
    }
    with Session(db) as session:
        session.add(
            AuthenticationModel(
                id=6,
                name="wecom",
                type=6,
                config=json.dumps(good),
                enable=True,
                valid=True,
                create_time=0,
            )
        )
        session.commit()

    def sessions():
        with Session(db) as session:
            yield session

    calls = []

    async def request_token(_config):
        calls.append(True)
        return "synthetic-" + "x" * 512, 7195

    ns = {
        "datetime": datetime,
        "timezone": timezone,
        "hashlib": hashlib,
        "json": json,
        "Optional": Optional,
        "SQLAlchemyError": SQLAlchemyError,
        "select": select,
        "dynamic_get_session": lambda: sessions,
        "SysPlatformTokenModel": SysPlatformTokenModel,
        "AuthenticationModel": AuthenticationModel,
    }
    filename = Path(source_root) / "src/sqlbot_xpack/platform/wecom_manage.py"
    tree = ast.parse(filename.read_text())
    names = {
        "PlatformTokenCacheError",
        "credential_fingerprint",
        "cached_token",
        "get_token",
    }
    nodes = [
        n
        for n in tree.body
        if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name in names
    ]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(filename), "exec"), ns)
    ns.update(origin=6, request_token=request_token)
    # Actual PostgreSQL rejects the pre-migration cache write, safely wrapped.
    expected_error = ns.get("PlatformTokenCacheError", DataError)
    with pytest.raises(expected_error):
        asyncio.run(ns["get_token"](good))
    migrate(db, "077_platform_token_text.py", "upgrade")
    token = asyncio.run(ns["get_token"](good))
    assert len(token) > 255
    assert asyncio.run(ns["get_token"](good)) == token
    assert len(calls) == 2  # failed pre-migration fetch and successful initial fetch
    with Session(db) as session:
        row = session.get(SysPlatformTokenModel, 6)
        assert json.loads(row.token)["access_token"] == token
        row.exp_time = 0
        session.add(row)
        session.commit()
    assert asyncio.run(ns["get_token"](good)) == token
    assert len(calls) == 3
    changed = {**good, "agent_id": "1002"}
    with Session(db) as session:
        auth = session.get(AuthenticationModel, 6)
        auth.config = json.dumps(changed)
        session.add(auth)
        session.commit()
    assert asyncio.run(ns["get_token"](changed)) == token
    assert len(calls) == 4
    with Session(db) as session:
        row = session.get(SysPlatformTokenModel, 6)
        assert json.loads(row.token)["credential_fingerprint"] == ns[
            "credential_fingerprint"
        ](changed)
        row.token = "legacy-raw-token"
        session.add(row)
        session.commit()
    assert asyncio.run(ns["get_token"](changed)) == token
    assert len(calls) == 5
