"""Opt-in datasource lifecycle acceptance at parameter/resource/task entries."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session
from test_embedding_parameters import save, values
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)
from test_table_parameters_integration import table_environment  # noqa: F401


@pytest.fixture
def lifecycle_environment(table_environment, monkeypatch):  # noqa: F811
    database, client, ds_id = table_environment
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    monkeypatch.setattr("common.utils.embedding_threads.session_maker", sessions)
    monkeypatch.setattr("apps.system.schemas.permission.engine", database)
    with ThreadPoolExecutor(max_workers=4) as executor:
        monkeypatch.setattr("common.utils.embedding_threads.executor", executor)
        yield database, client, ds_id
    sessions.remove()


def test_table_switch_is_read_and_saved_through_parameter_api(lifecycle_environment):
    _database, client, _ds_id = lifecycle_environment
    assert values(client)["embedding.table_enabled"] == "true"
    response = save(client, [{"pkey": "embedding.table_enabled", "pval": False}])
    assert response.status_code == 200, response.text
    assert values(client)["embedding.table_enabled"] == "false"


def test_field_edit_while_disabled_invalidates_table_and_parent(
    lifecycle_environment, monkeypatch
):
    from sqlmodel import Session

    from apps.datasource.crud.datasource import get_ds, updateField
    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.models.datasource import CoreField
    from common.core.config import settings

    database, client, ds_id = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_ENABLED", False)
    with Session(database) as session:
        table = get_tables_by_ds_id(session, ds_id)[0]
        table_id = table.id
        field = session.query(CoreField).filter(CoreField.table_id == table.id).first()
        updateField(
            session,
            CoreField(
                id=field.id,
                ds_id=ds_id,
                table_id=table.id,
                custom_comment="updated field",
                checked=True,
            ),
        )
    with Session(database) as session:
        assert get_ds(session, ds_id).embedding is None
        assert (
            next(
                t for t in get_tables_by_ds_id(session, ds_id) if t.id == table_id
            ).embedding
            is None
        )


def test_generation_reads_persisted_switch_at_task_start(
    lifecycle_environment, monkeypatch
):
    from types import SimpleNamespace

    from sqlalchemy.orm import scoped_session, sessionmaker
    from sqlmodel import Session

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.datasource import get_ds
    from apps.datasource.crud.table import run_fill_empty_table_and_ds_embedding
    from apps.datasource.models.datasource import CoreDatasource, CoreTable

    database, client, ds_id = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    with Session(database) as session:
        session.query(CoreDatasource).update({"embedding": None})
        session.query(CoreTable).update({"embedding": None})
        session.commit()
    inputs = []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(
            embed_query=lambda value: inputs.append(value) or [1, 0]
        ),
    )
    run_fill_empty_table_and_ds_embedding(sessions)
    assert inputs == []
    with Session(database) as session:
        assert get_ds(session, ds_id).embedding is None


@pytest.mark.parametrize("operation", ["rename", "table", "sync", "choose"])
def test_metadata_operations_invalidate_parent_while_disabled(
    lifecycle_environment, monkeypatch, operation
):
    from types import SimpleNamespace

    from apps.datasource.crud import datasource as crud
    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.models.datasource import (
        ColumnSchema,
        CoreDatasource,
        CoreTable,
    )

    database, client, ds_id = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    monkeypatch.setattr(
        crud,
        "getFieldsByDs",
        lambda *_args: [ColumnSchema("updated_id", "BIGINT", "synced")],
    )
    monkeypatch.setattr(crud, "get_tables", lambda *_args: [])
    monkeypatch.setattr(crud, "check_status", lambda *_args: True)
    with Session(database) as session:
        table = get_tables_by_ds_id(session, ds_id)[0]
        table_id = table.id
        if operation == "rename":
            crud.update_ds(
                session,
                lambda value: value,
                SimpleNamespace(oid=1),
                CoreDatasource(id=ds_id, name="renamed", description="new description"),
            )
        elif operation == "table":
            crud.updateTable(
                session,
                CoreTable(
                    id=table_id, ds_id=ds_id, checked=False, custom_comment="new table"
                ),
            )
        elif operation == "sync":
            monkeypatch.setattr(
                crud,
                "getTablesByDs",
                lambda *_args: [SimpleNamespace(tableName=table.table_name)],
            )
            crud.sync_single_fields(session, lambda value: value, ds_id, table_id)
        else:
            crud.chooseTables(session, lambda value: value, ds_id, [])
    with Session(database) as session:
        assert crud.get_ds(session, ds_id).embedding is None
        if operation in ("table", "sync"):
            assert (
                next(
                    t for t in get_tables_by_ds_id(session, ds_id) if t.id == table_id
                ).embedding
                is None
            )
        elif operation == "choose":
            assert get_tables_by_ds_id(session, ds_id) == []


def test_backfill_repairs_invalid_json_but_keeps_valid_vectors(
    lifecycle_environment, monkeypatch
):
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.datasource import get_ds
    from apps.datasource.crud.table import (
        get_tables_by_ds_id,
        run_fill_empty_table_and_ds_embedding,
    )
    from apps.datasource.models.datasource import CoreDatasource, CoreTable

    database, _client, ds_id = lifecycle_environment
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    with Session(database) as session:
        tables = get_tables_by_ds_id(session, ds_id)
        ids = [table.id for table in tables]
        for table, vector in zip(
            tables, ["[]", "not-json", "[0,0]", "[0,1]"], strict=True
        ):
            table.embedding = vector
            session.add(table)
        session.get(CoreDatasource, ds_id).embedding = "null"
        session.commit()
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_query=lambda _value: [1, 0]),
    )
    try:
        run_fill_empty_table_and_ds_embedding(sessions)
        with Session(database) as session:
            assert [session.get(CoreTable, i).embedding for i in ids] == [
                "[1.0, 0.0]"
            ] * 3 + ["[0,1]"]
            assert get_ds(session, ds_id).embedding == "[1.0, 0.0]"
    finally:
        sessions.remove()


def test_imported_schema_invalidates_edited_tables_and_parent(lifecycle_environment):
    import io

    import pandas as pd

    from apps.datasource.api.datasource import (
        f_c_col,
        f_n_col,
        t_c_col,
        t_n_col,
        t_s_col,
        t_sheet,
        upload_ds_schema,
    )
    from apps.datasource.crud.datasource import get_ds
    from apps.datasource.crud.table import get_tables_by_ds_id

    database, client, ds_id = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    # Route handler and real permission middleware, scoped session and admin identity
    # are inherited from the parameter app; only the external upload is synthetic.
    client.app.add_api_route("/test/schema/{id}", upload_ds_schema, methods=["POST"])
    with Session(database) as session:
        table = get_tables_by_ds_id(session, ds_id)[0]
        table_name, table_id = table.table_name, table.id
    workbook = io.BytesIO()
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        pd.DataFrame(
            [{t_s_col: "fields", t_n_col: table_name, t_c_col: "Imported table"}]
        ).to_excel(writer, sheet_name=t_sheet, index=False)
        pd.DataFrame([{f_n_col: "id", f_c_col: "Imported field"}]).to_excel(
            writer, sheet_name="fields", index=False
        )
    response = client.post(
        f"/test/schema/{ds_id}",
        files={
            "file": (
                "schema.xlsx",
                workbook.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )
    assert response.status_code == 200, response.text
    with Session(database) as session:
        assert get_ds(session, ds_id).embedding is None
        edited = next(
            table
            for table in get_tables_by_ds_id(session, ds_id)
            if table.id == table_id
        )
        assert edited.custom_comment == "Imported table"
        assert edited.embedding is None
        assert all(
            table.embedding in ("[1,0]", "[0,1]", "[0.8,0.6]")
            for table in get_tables_by_ds_id(session, ds_id)
            if table.id != table_id
        )


def test_reenable_asynchronously_fills_invalidated_metadata(
    lifecycle_environment, monkeypatch
):
    import time
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.datasource import get_ds, updateField
    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.models.datasource import CoreField

    database, client, ds_id = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    with Session(database) as session:
        table = get_tables_by_ds_id(session, ds_id)[0]
        field = session.query(CoreField).filter(CoreField.table_id == table.id).first()
        updateField(
            session,
            CoreField(
                id=field.id,
                ds_id=ds_id,
                table_id=table.id,
                checked=True,
                custom_comment="after enable",
            ),
        )
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_query=lambda _value: [0.6, 0.8]),
    )
    started = time.monotonic()
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": True}]).status_code
        == 200
    )
    assert time.monotonic() - started < 1
    while time.monotonic() - started < 3:
        with Session(database) as session:
            vectors = [t.embedding for t in get_tables_by_ds_id(session, ds_id)]
            if get_ds(session, ds_id).embedding == "[0.6, 0.8]" and all(vectors):
                break
        time.sleep(0.02)
    else:
        pytest.fail("enabling did not fill missing metadata vectors")
    assert vectors.count("[0.6, 0.8]") == 1


@pytest.mark.parametrize("resource", ["table", "datasource", "datasource_field"])
def test_in_flight_generation_never_publishes_superseded_metadata(
    lifecycle_environment, monkeypatch, resource
):
    from threading import Event
    from types import SimpleNamespace

    from test_table_parameters_integration import configure, run, task

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud import datasource as crud
    from apps.datasource.crud.table import (
        get_tables_by_ds_id,
        save_ds_embedding,
        save_table_embedding,
    )
    from apps.datasource.models.datasource import CoreDatasource, CoreField

    database, client, ds_id = lifecycle_environment
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    entered, release = Event(), Event()
    inputs = []

    def embed(value):
        inputs.append(value)
        if len(inputs) == 1:
            entered.set()
            assert release.wait(5)
        return [0, 1] if "latest content" in value else [1, 0]

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: SimpleNamespace(embed_query=embed)
    )
    with Session(database) as session:
        table = next(t for t in get_tables_by_ds_id(session, ds_id) if t.checked)
        table_id = table.id
        field = session.query(CoreField).filter(CoreField.table_id == table_id).first()
        field_id = field.id
        if resource == "table":
            table.embedding = None
        else:
            session.get(CoreDatasource, ds_id).embedding = None
        session.commit()
    generator = save_table_embedding if resource == "table" else save_ds_embedding
    with ThreadPoolExecutor(max_workers=1) as workers:
        future = workers.submit(
            generator, sessions, [table_id if resource == "table" else ds_id]
        )
        try:
            assert entered.wait(5)
            # Stop new jobs, while allowing the already-started one to finish.
            configure(client, table_enabled=False)
            with Session(database) as session:
                if resource in ("table", "datasource_field"):
                    crud.updateField(
                        session,
                        CoreField(
                            id=field_id,
                            ds_id=ds_id,
                            table_id=table_id,
                            checked=True,
                            custom_comment="latest content",
                        ),
                    )
                else:
                    crud.update_ds(
                        session,
                        lambda value: value,
                        SimpleNamespace(oid=1),
                        CoreDatasource(
                            id=ds_id,
                            name="latest content",
                            description="latest content",
                        ),
                    )
            with Session(database) as session:
                assert crud.get_ds(session, ds_id).embedding is None
            schema = run(task(database, ds_id))
            assert (
                "sales_alpha" in schema
                and "vector_beta" in schema
                and "other_gamma" in schema
            )
        finally:
            release.set()
        future.result(timeout=5)
    with Session(database) as session:
        result = (
            next(t for t in get_tables_by_ds_id(session, ds_id) if t.id == table_id)
            if resource == "table"
            else crud.get_ds(session, ds_id)
        )
        assert result.embedding == "[0.0, 1.0]"
        if resource == "table":
            assert crud.get_ds(session, ds_id).embedding is None
    assert "latest content" in inputs[-1]


@pytest.mark.parametrize("bad_vector", [[], [0, 0], [float("nan"), 1], ["1", 0], None])
def test_failed_generation_leaves_candidates_available(
    lifecycle_environment, monkeypatch, bad_vector
):
    from types import SimpleNamespace

    from test_table_parameters_integration import configure, run, task

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.table import (
        get_tables_by_ds_id,
        run_fill_empty_table_and_ds_embedding,
    )
    from apps.datasource.models.datasource import CoreDatasource
    from common.utils.embedding_lifecycle import EmbeddingGenerationError

    database, client, ds_id = lifecycle_environment
    configure(client, table_count=1)
    with Session(database) as session:
        table = next(t for t in get_tables_by_ds_id(session, ds_id) if t.checked)
        table.embedding = None
        session.get(CoreDatasource, ds_id).embedding = None
        session.commit()
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: SimpleNamespace(embed_query=lambda _: bad_vector),
    )
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    with pytest.raises(EmbeddingGenerationError):
        run_fill_empty_table_and_ds_embedding(sessions)
    schema = run(task(database, ds_id))
    assert all(name in schema for name in ("sales_alpha", "vector_beta", "other_gamma"))
    with Session(database) as session:
        assert session.get(CoreDatasource, ds_id).embedding is None
        assert any(
            t.embedding is None
            for t in get_tables_by_ds_id(session, ds_id)
            if t.checked
        )


@pytest.mark.parametrize("crash_first", [False, True])
def test_process_workers_deduplicate_and_recover_after_crash(
    lifecycle_environment, tmp_path, crash_first
):
    import json
    import os
    import subprocess
    import sys
    import time
    from pathlib import Path

    from sqlalchemy import text

    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.models.datasource import CoreDatasource

    database, _client, ds_id = lifecycle_environment
    with Session(database) as session:
        table = get_tables_by_ds_id(session, ds_id)[0]
        table.embedding = None
        session.get(CoreDatasource, ds_id).embedding = None
        session.commit()
    with database.connect() as connection:
        schema = connection.execute(text("select current_schema()")).scalar_one()
    application = "fill_" + schema
    worker = tmp_path / "worker.py"
    worker.write_text("""
import json, sys, time
from pathlib import Path
from types import SimpleNamespace
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session, create_engine
from apps.ai_model.embedding import EmbeddingModelCache
from common.core.config import settings
from common.utils import embedding_threads
url, schema, app, directory = sys.argv[1:]
directory = Path(directory)
engine = create_engine(url, connect_args={'options': '-csearch_path=' + schema + ',public', 'application_name': app})
embedding_threads.session_maker = scoped_session(sessionmaker(bind=engine, class_=Session))
settings.TABLE_EMBEDDING_ENABLED = True
def embed(value):
    with (directory / 'generated.jsonl').open('a') as log:
        log.write(json.dumps(value) + '\\n')
    deadline = time.monotonic() + 25
    while not (directory / 'release').exists():
        if time.monotonic() > deadline:
            raise TimeoutError('provider barrier')
        time.sleep(0.01)
    return [0.6, 0.8]
EmbeddingModelCache.get_model = staticmethod(lambda: SimpleNamespace(embed_query=embed))
embedding_threads.fill_empty_table_and_ds_embeddings().result(timeout=30)
embedding_threads.executor.shutdown(wait=True)
engine.dispose()
print('completed')
""")
    command = [
        sys.executable,
        str(worker),
        database.url.render_as_string(hide_password=False),
        schema,
        application,
        str(tmp_path),
    ]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[1].resolve())}
    processes = []

    def await_state(predicate):
        deadline = time.monotonic() + 20
        while not predicate():
            assert time.monotonic() < deadline, "worker progress timed out"
            for process in processes:
                assert process.poll() is None, process.communicate()[1]
            time.sleep(0.02)

    def waiting():
        with database.connect() as connection:
            return (
                connection.execute(
                    text(
                        "SELECT count(*) FROM pg_stat_activity WHERE application_name=:name AND wait_event='advisory'"
                    ),
                    {"name": application},
                ).scalar_one()
                == 1
            )

    try:
        first = subprocess.Popen(
            command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        processes.append(first)
        await_state(lambda: (tmp_path / "generated.jsonl").exists())
        second = subprocess.Popen(
            command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        processes.append(second)
        await_state(waiting)
        if crash_first:
            first.kill()
            first.communicate(timeout=10)
            processes.remove(first)
            await_state(
                lambda: (
                    len((tmp_path / "generated.jsonl").read_text().splitlines()) == 2
                )
            )
        (tmp_path / "release").touch()
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            assert process.returncode == 0, stderr
            assert "completed" in stdout
    finally:
        (tmp_path / "release").touch()
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
    generated = [
        json.loads(line)
        for line in (tmp_path / "generated.jsonl").read_text().splitlines()
    ]
    assert len(generated) == (3 if crash_first else 2)
    with Session(database) as session:
        assert session.get(CoreDatasource, ds_id).embedding == "[0.6, 0.8]"
        assert get_tables_by_ds_id(session, ds_id)[0].embedding == "[0.6, 0.8]"


def test_create_and_empty_field_sync_recover_after_enable(
    lifecycle_environment, monkeypatch
):
    import asyncio
    import time
    from types import SimpleNamespace

    from apps.datasource.crud import datasource as crud
    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.models.datasource import (
        ColumnSchema,
        CoreField,
        CoreTable,
        CreateDatasource,
    )

    database, client, _ds_id = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    monkeypatch.setattr(
        crud,
        "getFieldsByDs",
        lambda *_args: [ColumnSchema("id", "INTEGER", "created field")],
    )
    monkeypatch.setattr(
        crud, "get_tables", lambda *_args: [SimpleNamespace(tableName="created")]
    )
    monkeypatch.setattr(
        crud, "getTablesByDs", lambda *_args: [SimpleNamespace(tableName="created")]
    )
    with Session(database) as session:
        datasource = asyncio.run(
            crud.create_ds(
                session,
                lambda value: value,
                SimpleNamespace(id=1, oid=1),
                CreateDatasource(
                    name="created datasource",
                    type="pg",
                    tables=[
                        CoreTable(table_name="created", table_comment="created table")
                    ],
                ),
            )
        )
        ds_id = datasource.id
        table_id = get_tables_by_ds_id(session, ds_id)[0].id
    with Session(database) as session:
        assert crud.get_ds(session, ds_id).embedding is None
        assert get_tables_by_ds_id(session, ds_id)[0].embedding is None
        monkeypatch.setattr(crud, "getFieldsByDs", lambda *_args: [])
        crud.sync_single_fields(session, lambda value: value, ds_id, table_id)
        assert (
            session.query(CoreField).filter(CoreField.table_id == table_id).all() == []
        )
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": True}]).status_code
        == 200
    )
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        with Session(database) as session:
            if (
                crud.get_ds(session, ds_id).embedding
                and get_tables_by_ds_id(session, ds_id)[0].embedding
            ):
                break
        time.sleep(0.02)
    else:
        pytest.fail("created datasource remained unfilled")
