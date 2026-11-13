# isort: skip_file
import base64
import json
import os
import secrets
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock

import pytest
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlmodel import Session, create_engine

from apps.system.api import login  # noqa: F401 (initialize wheel route dependencies)
from apps.datasource.api import datasource
from apps.datasource.models.datasource import CoreDatasource, CoreField, CoreTable
from apps.datasource.models.metadata_embedding import MetadataEmbedding
from apps.datasource.utils.configuration_migration import (
    has_versioned_configurations,
    migrate_datasource_configurations,
)
from apps.datasource.utils.utils import (
    DatasourceConfigurationError,
    DatasourceKeyError,
    aes_decrypt,
    aes_encrypt,
    initialize_datasource_keys,
    load_datasource_keys,
)
from apps.db.db import exec_sql, pool_manager
from apps.system.crud.assistant import get_out_ds_conf
from apps.system.schemas import permission
from apps.system.schemas.system_schema import AssistantOutDsSchema, UserInfoDTO
from common.audit.schemas import logger_decorator
from common.audit.schemas.request_context import RequestContextMiddlewareCommon
from common.core.config import settings
from common.core.db import get_session

PUBLIC_KEY = b"SQLBot1234567890"


def legacy(plaintext):
    return base64.b64encode(
        AES.new(PUBLIC_KEY, AES.MODE_ECB).encrypt(pad(plaintext.encode(), 16))
    ).decode()


def write_keys(path, active, **keys):
    path.write_text(
        json.dumps(
            {
                "active": active,
                "keys": {
                    name: base64.b64encode(value).decode()
                    for name, value in keys.items()
                },
            }
        )
    )


@pytest.fixture
def key_file(tmp_path, monkeypatch):
    path = tmp_path / "keys.json"
    write_keys(path, "first", first=secrets.token_bytes(32))
    monkeypatch.setenv("SQLBOT_DATASOURCE_KEYS_FILE", str(path))
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    return path


def test_public_key_baseline_and_authenticated_envelopes(key_file, monkeypatch):
    plaintext = '{"password":"合成-only"}'
    old = legacy(plaintext)
    assert old == legacy(plaintext)
    assert (
        unpad(
            AES.new(PUBLIC_KEY, AES.MODE_ECB).decrypt(base64.b64decode(old)), 16
        ).decode()
        == plaintext
    )

    value = aes_encrypt(plaintext)
    header, key_id, payload = value.split(b":")
    assert (
        base64.b64decode(payload)[:12]
        != base64.b64decode(aes_encrypt(plaintext).split(b":")[2])[:12]
    )
    assert aes_decrypt(value) == plaintext
    raw = base64.b64decode(payload)
    public_cipher = AES.new(PUBLIC_KEY, AES.MODE_GCM, nonce=raw[:12])
    public_cipher.update(header + b":" + key_id + b":")
    with pytest.raises(ValueError, match="MAC check failed"):
        public_cipher.decrypt_and_verify(raw[28:], raw[12:28])
    with pytest.raises(DatasourceConfigurationError):
        aes_decrypt(old)
    for offset in (0, 12, 28):
        raw = bytearray(base64.b64decode(payload))
        raw[offset] ^= 1
        with pytest.raises(DatasourceConfigurationError):
            aes_decrypt(b":".join((header, key_id, base64.b64encode(raw))))
    write_keys(key_file, "first", first=secrets.token_bytes(32))
    with pytest.raises(DatasourceConfigurationError):
        aes_decrypt(value)
    monkeypatch.delenv("SQLBOT_DATASOURCE_KEYS_FILE")
    with pytest.raises(DatasourceKeyError):
        aes_encrypt(plaintext)
    with pytest.raises(DatasourceKeyError):
        aes_decrypt(value)


def test_default_key_creation_restart_and_loss(tmp_path, monkeypatch):
    monkeypatch.delenv("SQLBOT_DATASOURCE_KEYS_FILE", raising=False)
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    with ThreadPoolExecutor(max_workers=8) as workers:
        keys = list(workers.map(initialize_datasource_keys, [False] * 8))
    assert all(key == keys[0] for key in keys)
    path = tmp_path / ".secrets" / "datasource-keys.json"
    assert path.stat().st_mode & 0o777 == 0o600
    encrypted = aes_encrypt('{"password":"synthetic"}')
    original = path.read_bytes()
    assert initialize_datasource_keys(True) == keys[0]
    path.unlink()
    with pytest.raises(DatasourceKeyError, match="missing"):
        initialize_datasource_keys(True)
    assert not path.exists()
    path.write_bytes(original)
    assert aes_decrypt(encrypted) == '{"password":"synthetic"}'


def test_explicit_missing_key_is_not_generated(tmp_path, monkeypatch):
    path = tmp_path / "managed.json"
    monkeypatch.setenv("SQLBOT_DATASOURCE_KEYS_FILE", str(path))
    with pytest.raises(DatasourceKeyError, match="missing"):
        initialize_datasource_keys(False)
    assert not path.exists()


@pytest.fixture
def pg():
    url = os.getenv("SQLBOT_DATASOURCE_TEST_DATABASE_URL")
    if not url:
        pytest.skip(
            "Set SQLBOT_DATASOURCE_TEST_DATABASE_URL to a disposable PostgreSQL database"
        )
    engine = create_engine(url)
    schema = "ds_crypto_" + secrets.token_hex(8)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA {schema}"))
    database = engine.execution_options(schema_translate_map={None: schema})
    try:
        for model in (CoreDatasource, CoreTable, CoreField, MetadataEmbedding):
            model.__table__.create(database)
        yield database, schema
    finally:
        with engine.begin() as connection:
            connection.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        engine.dispose()


def test_migration_restart_rotation_and_compare_and_swap(pg, key_file, monkeypatch):
    database, _ = pg
    original = legacy('{"password":"synthetic"}')
    with Session(database) as session:
        row = CoreDatasource(name="history", type="pg", configuration=original, oid=1)
        session.add(row)
        session.commit()
        row_id = row.id
    keys = load_datasource_keys()
    concurrent = aes_encrypt('{"password":"concurrent"}').decode()
    with Session(database) as session:
        execute = session.execute

        def interrupt(statement, *args, **kwargs):
            if statement.is_update:
                raise RuntimeError("interrupted")
            return execute(statement, *args, **kwargs)

        with monkeypatch.context() as scoped:
            scoped.setattr(session, "execute", interrupt)
            with pytest.raises(RuntimeError, match="interrupted"):
                migrate_datasource_configurations(session, keys)
    with Session(database) as session:
        assert not has_versioned_configurations(session)
        assert session.get(CoreDatasource, row_id).configuration == original
        execute = session.execute

        def edit_before_write(statement, *args, **kwargs):
            if statement.is_update:
                with Session(database) as editor:
                    editor.get(CoreDatasource, row_id).configuration = concurrent
                    editor.commit()
            return execute(statement, *args, **kwargs)

        with monkeypatch.context() as scoped:
            scoped.setattr(session, "execute", edit_before_write)
            migrate_datasource_configurations(session, keys)
    with Session(database) as session:
        assert session.get(CoreDatasource, row_id).configuration == concurrent
        session.get(CoreDatasource, row_id).configuration = original
        session.commit()
        migrate_datasource_configurations(session, keys)
        assert has_versioned_configurations(session)
        first = session.get(CoreDatasource, row_id).configuration
        assert aes_decrypt(first) == '{"password":"synthetic"}'
        migrate_datasource_configurations(session, load_datasource_keys())
        assert session.get(CoreDatasource, row_id).configuration == first
        second_key = secrets.token_bytes(32)
        write_keys(key_file, "second", first=keys.keys["first"], second=second_key)
        migrate_datasource_configurations(session, load_datasource_keys())
        second = session.get(CoreDatasource, row_id).configuration
        assert second.startswith("gcm1:second:")
        write_keys(key_file, "second", second=second_key)
        assert aes_decrypt(second) == '{"password":"synthetic"}'
        with pytest.raises(DatasourceKeyError):
            aes_decrypt(first)
        write_keys(key_file, "first", first=keys.keys["first"])
        assert aes_decrypt(first) == '{"password":"synthetic"}'


@pytest.mark.usefixtures("key_file")
def test_datasource_http_postgres(pg, monkeypatch, caplog):
    database, schema = pg
    with database.begin() as connection:
        connection.execute(text(f"CREATE TABLE {schema}.synthetic_sample (id integer)"))
        connection.execute(text(f"INSERT INTO {schema}.synthetic_sample VALUES (42)"))
    monkeypatch.setattr(permission, "engine", database)
    monkeypatch.setattr(datasource, "run_save_ds_embeddings", lambda *_: None)
    monkeypatch.setattr(datasource, "run_save_table_embeddings", lambda *_: None)
    monkeypatch.setattr(
        "apps.datasource.crud.datasource.run_save_ds_embeddings", lambda *_: None
    )
    monkeypatch.setattr(
        "apps.datasource.crud.datasource.run_save_table_embeddings", lambda *_: None
    )
    monkeypatch.setattr(logger_decorator.SystemLogger, "create_log_record", AsyncMock())
    app = FastAPI()
    app.include_router(datasource.router)
    app.add_middleware(permission.RequestContextMiddleware)
    app.add_middleware(RequestContextMiddlewareCommon)

    @app.middleware("http")
    async def identity(request, call_next):
        request.state.current_user = UserInfoDTO(
            id=1,
            oid=int(request.headers.get("workspace", "1")),
            weight=1,
            account="synthetic",
            name="synthetic",
            email="synthetic@example.invalid",
        )
        return await call_next(request)

    def sessions():
        with Session(database) as session:
            yield session

    app.dependency_overrides[get_session] = sessions
    url = database.url
    config = {
        "host": url.host,
        "port": url.port,
        "username": url.username,
        "password": "synthetic-only",
        "database": url.database,
        "dbSchema": schema,
    }
    request = {
        "name": "synthetic",
        "description": "",
        "type": "pg",
        "configuration": legacy(json.dumps(config)),
    }
    client = TestClient(app)

    def post(path, **kwargs):
        return client.post("/datasource" + path, **kwargs)

    assert post("/check", json=request).json() is True
    tables = post("/getTablesByConf", json=request)
    assert tables.status_code == 200, tables.text
    assert "synthetic_sample" in tables.text
    added = post(
        "/add", json={**request, "tables": [{"table_name": "synthetic_sample"}]}
    )
    assert added.status_code == 200, added.text
    ds_id = added.json()["id"]
    assert "configuration" not in added.json()
    assert "SQLBOT_DATASOURCE_KEYS_FILE" not in added.text
    assert "configuration" not in client.get("/datasource/list").json()[0]
    details = post(f"/get/{ds_id}")
    assert details.status_code == 200, details.text
    assert "password" not in json.loads(details.json()["configuration"])
    assert (
        post(
            "/check", json={**request, "id": ds_id}, headers={"workspace": "2"}
        ).status_code
        == 404
    )
    with Session(database) as session:
        stored = session.get(CoreDatasource, ds_id).configuration
    for bad in (stored, "invalid!"):
        assert (
            post(
                "/update", json={**request, "id": ds_id, "configuration": bad}
            ).status_code
            == 400
        )
    with Session(database) as session:
        assert session.get(CoreDatasource, ds_id).configuration == stored
    del config["password"]
    edited = post(
        "/update",
        json={**request, "id": ds_id, "configuration": legacy(json.dumps(config))},
    )
    assert edited.status_code == 200, edited.text
    with Session(database) as session:
        saved = session.get(CoreDatasource, ds_id).configuration
    assert saved != stored
    assert json.loads(aes_decrypt(saved))["password"] == "synthetic-only"
    assert client.get(f"/datasource/check/{ds_id}").json() is True
    assert post(f"/getFields/{ds_id}/synthetic_sample").status_code == 200
    table = post(f"/tableList/{ds_id}").json()[0]
    preview = post(f"/previewData/{ds_id}", json={"table": table})
    assert preview.status_code == 200 and "42" in preview.text, preview.text
    with Session(database) as session:
        ds = session.get(CoreDatasource, ds_id)
        try:
            assert exec_sql(ds, "select id from synthetic_sample")["data"] == [
                {"id": 42}
            ]
        finally:
            pool_manager.remove_pool(ds_id)
    redirected = legacy(json.dumps({**config, "host": "redirect.invalid"}))
    assert (
        post(
            "/check", json={**request, "id": ds_id, "configuration": redirected}
        ).status_code
        == 400
    )

    excel_config = {
        "filename": "synthetic.xlsx",
        "sheets": [{"tableName": "synthetic_sample"}],
    }
    excel = post(
        "/add",
        json={
            **request,
            "name": "synthetic Excel",
            "type": "excel",
            "configuration": legacy(json.dumps(excel_config)),
        },
    )
    assert excel.status_code == 200, excel.text
    with Session(database) as session:
        excel_ds = session.get(CoreDatasource, excel.json()["id"])
        assert json.loads(aes_decrypt(excel_ds.configuration)) == excel_config
    assert "synthetic_sample" in post(f"/getTables/{excel_ds.id}").text
    assistant = AssistantOutDsSchema(
        name="synthetic", type="pg", password="assistant-only"
    )
    assert (
        json.loads(aes_decrypt(get_out_ds_conf(assistant)))["password"]
        == "assistant-only"
    )
    monkeypatch.delenv("SQLBOT_DATASOURCE_KEYS_FILE")
    assert post("/update", json={**request, "id": ds_id}).status_code == 503
    with Session(database) as session:
        assert session.get(CoreDatasource, ds_id).configuration == saved
    assert "synthetic-only" not in caplog.text
    assert saved not in caplog.text
