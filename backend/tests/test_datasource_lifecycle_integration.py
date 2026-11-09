"""Opt-in datasource lifecycle acceptance at parameter/resource/task entries."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from metadata_test_support import (
    metadata_model,
    read_datasource_vectors,
    read_table_vectors,
)
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session
from test_embedding_parameters import save, values
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)
from test_table_parameters_integration import table_environment  # noqa: F401

from apps.datasource.embedding.metadata_chunks import invalidate_chunks
from common.utils import embedding_threads
from common.utils.metadata_scheduler import MetadataScheduler


@pytest.fixture
def lifecycle_environment(table_environment, monkeypatch):  # noqa: F811
    database, client, ds_id = table_environment
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    monkeypatch.setattr("common.utils.embedding_threads.session_maker", sessions)
    monkeypatch.setattr("apps.system.schemas.permission.engine", database)
    with ThreadPoolExecutor(max_workers=4) as executor:
        monkeypatch.setattr("common.utils.embedding_threads.executor", executor)
        scheduler = MetadataScheduler(embedding_threads._run_metadata_batch)
        monkeypatch.setattr(embedding_threads, "metadata_scheduler", scheduler)
        try:
            yield database, client, ds_id
        finally:
            scheduler.shutdown()
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
    from sqlalchemy.orm import scoped_session, sessionmaker
    from sqlmodel import Session

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.datasource import get_ds
    from apps.datasource.crud.table import run_fill_empty_table_and_ds_embedding
    from apps.datasource.models.datasource import CoreDatasource, CoreTable
    from apps.datasource.models.metadata_embedding import MetadataEmbedding

    database, client, ds_id = lifecycle_environment
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": False}]).status_code
        == 200
    )
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    with Session(database) as session:
        session.query(CoreDatasource).update({"embedding": None})
        session.query(CoreTable).update({"embedding": None})
        session.query(MetadataEmbedding).delete()
        session.commit()
    inputs = []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: metadata_model(embed=lambda value: inputs.append(value) or [1, 0]),
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


@pytest.mark.parametrize(
    "damage", ["missing", "format", "model", "input", "incomplete", "invalid"]
)
def test_backfill_repairs_invalid_chunks_but_keeps_valid_vectors(
    lifecycle_environment, monkeypatch, damage
):
    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.table import (
        get_tables_by_ds_id,
        run_fill_empty_table_and_ds_embedding,
    )
    from apps.datasource.models.metadata_embedding import MetadataEmbedding

    database, _client, ds_id = lifecycle_environment
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    with Session(database) as session:
        tables = get_tables_by_ds_id(session, ds_id)
        ids = [table.id for table in tables]
        preserved = read_table_vectors(session, ids[-1])
        # Legacy vectors remain nonempty; only the new storage determines completion.
        for key in ids[:-1]:
            row = session.get(MetadataEmbedding, ("table", key))
            if damage == "missing":
                session.delete(row)
            elif damage == "format":
                row.format_version = 0
            elif damage == "model":
                row.model_id = "outdated-model"
            elif damage == "input":
                row.input_hash = "outdated-input"
            elif damage == "incomplete":
                row.chunk_count += 1
            else:
                row.vectors = "broken"
        invalidate_chunks(session, "datasource", [ds_id])
        session.commit()
    inputs = []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: metadata_model(
            embed=lambda value: inputs.append(value) or [1, 0], limit=10000
        ),
    )
    try:
        run_fill_empty_table_and_ds_embedding(sessions)
        with Session(database) as session:
            assert [read_table_vectors(session, key) for key in ids[:-1]] == [
                [[1, 0]]
            ] * 3
            assert read_table_vectors(session, ids[-1]) == preserved
            assert read_datasource_vectors(session, ds_id) == [[1, 0]]
        assert len(inputs) == 4
        inputs.clear()
        run_fill_empty_table_and_ds_embedding(sessions)
        assert inputs == []
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

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.datasource import updateField
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
        lambda: metadata_model([0.6, 0.8]),
    )
    started = time.monotonic()
    assert (
        save(client, [{"pkey": "embedding.table_enabled", "pval": True}]).status_code
        == 200
    )
    assert time.monotonic() - started < 1
    while time.monotonic() - started < 3:
        with Session(database) as session:
            try:
                vectors = [
                    read_table_vectors(session, t.id)
                    for t in get_tables_by_ds_id(session, ds_id)
                ]
                if all(
                    v == [0.6, 0.8] for v in read_datasource_vectors(session, ds_id)
                ):
                    break
            except ValueError:
                pass
        time.sleep(0.02)
    else:
        pytest.fail("enabling did not fill missing metadata vectors")
    assert vectors.count([[0.6, 0.8]]) == 1


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
        EmbeddingModelCache,
        "get_model",
        lambda: metadata_model(embed=embed, limit=10000),
    )
    with Session(database) as session:
        table = next(t for t in get_tables_by_ds_id(session, ds_id) if t.checked)
        table_id = table.id
        field = session.query(CoreField).filter(CoreField.table_id == table_id).first()
        field_id = field.id
        if resource == "table":
            table.embedding = None
            invalidate_chunks(session, "table", [table_id])
        else:
            session.get(CoreDatasource, ds_id).embedding = None
            invalidate_chunks(session, "datasource", [ds_id])
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
        if resource == "table":
            assert read_table_vectors(session, table_id) == [[0, 1]]
        else:
            assert all(
                vector == [0, 1] for vector in read_datasource_vectors(session, ds_id)
            )
        if resource == "table":
            assert crud.get_ds(session, ds_id).embedding is None
    assert "latest content" in inputs[-1]


@pytest.mark.parametrize("bad_vector", [[], [0, 0], [float("nan"), 1], ["1", 0], None])
def test_failed_generation_leaves_candidates_available(
    lifecycle_environment, monkeypatch, bad_vector
):

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
        invalidate_chunks(session, "table", [table.id])
        invalidate_chunks(session, "datasource", [ds_id])
        session.commit()
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: metadata_model(embed=lambda _: bad_vector),
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
        invalidate_chunks(session, "table", [table.id])
        invalidate_chunks(session, "datasource", [ds_id])
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
from metadata_test_support import metadata_model
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
EmbeddingModelCache.get_model = staticmethod(lambda: metadata_model(embed=embed, limit=10000))
embedding_threads.fill_empty_table_and_ds_embeddings().result(timeout=30)
embedding_threads.metadata_scheduler.shutdown(wait=True)
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
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(
            [
                str(Path(__file__).parents[1].resolve()),
                str(Path(__file__).parent.resolve()),
            ]
        ),
    }
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
        assert read_datasource_vectors(session, ds_id) == [[0.6, 0.8]]
        assert read_table_vectors(
            session, get_tables_by_ds_id(session, ds_id)[0].id
        ) == [[0.6, 0.8]]


def test_create_and_empty_field_sync_recover_after_enable(
    lifecycle_environment, monkeypatch
):
    import asyncio
    import time
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud import datasource as crud
    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.models.datasource import (
        ColumnSchema,
        CoreField,
        CoreTable,
        CreateDatasource,
    )

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: metadata_model([1, 0])
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
            try:
                if read_datasource_vectors(session, ds_id) and read_table_vectors(
                    session, table_id
                ):
                    break
            except ValueError:
                pass
        time.sleep(0.02)
    else:
        pytest.fail("created datasource remained unfilled")


def test_backfill_pages_100_tables_and_preserves_valid_resources(
    lifecycle_environment, monkeypatch
):
    from sqlalchemy import event

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.table import run_fill_empty_table_and_ds_embedding
    from apps.datasource.models.datasource import CoreTable

    database, _client, ds_id = lifecycle_environment
    with Session(database) as session:
        for index in range(100):
            session.add(
                CoreTable(ds_id=ds_id, table_name=f"bulk_{index}", embedding="[1,0]")
            )
        session.commit()
        ids = [row.id for row in session.query(CoreTable).all()]
    inputs, scans = [], []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: metadata_model(embed=lambda value: inputs.append(value) or [1, 0]),
    )

    def observe(_conn, _cursor, statement, _parameters, _context, _many):
        if (
            statement.startswith("SELECT core_table.id \nFROM")
            and "FOR UPDATE" not in statement
        ):
            scans.append(statement)

    event.listen(database, "before_cursor_execute", observe)
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    try:
        run_fill_empty_table_and_ds_embedding(sessions)
        assert scans and all("LIMIT" in statement for statement in scans)
        assert len(scans) >= 4
        with Session(database) as session:
            assert all(read_table_vectors(session, key) for key in ids)
            assert read_datasource_vectors(session, ds_id)
        inputs.clear()
        run_fill_empty_table_and_ds_embedding(sessions)
        assert inputs == []
    finally:
        event.remove(database, "before_cursor_execute", observe)
        sessions.remove()


def test_bulk_save_100_tables_and_continuous_edits_use_one_model_worker(
    lifecycle_environment, monkeypatch, capsys
):
    import json
    import time
    from dataclasses import replace
    from threading import Event, Lock
    from types import SimpleNamespace

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud import datasource as crud
    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.models.datasource import ColumnSchema, CoreField, CoreTable
    from common.core.embedding_config import load_embedding_config

    database, _client, ds_id = lifecycle_environment
    entered, release = Event(), Event()
    mutex = Lock()
    active = peak = calls = 0
    encode_seconds = 0

    def encode(value):
        nonlocal active, peak, calls, encode_seconds
        started = time.monotonic()
        with mutex:
            active += 1
            peak = max(peak, active)
            calls += 1
            first = calls == 1
        try:
            if first:
                entered.set()
                assert release.wait(30)
            return [1, 0] if "latest_19" in value else [0, 1]
        finally:
            with mutex:
                active -= 1
                encode_seconds += time.monotonic() - started

    model = metadata_model(embed=encode)
    model.embed_query = lambda _value: [1, 0]
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: model)
    monkeypatch.setattr(crud, "get_tables", lambda *_args: [])
    monkeypatch.setattr(crud, "check_status", lambda *_args: True)
    monkeypatch.setattr(
        crud,
        "getFieldsByDs",
        lambda _session, _ds, name: [
            ColumnSchema(f"field_{index}", "INT", "metric")
            for index in range(120 if int(name.split("_")[-1]) < 20 else 8)
        ],
    )
    started = time.monotonic()
    try:
        with Session(database) as session:
            crud.chooseTables(
                session,
                lambda value: value,
                ds_id,
                [
                    CoreTable(table_name=f"bulk_{index}", table_comment="metrics")
                    for index in range(100)
                ],
            )
        saved_seconds = time.monotonic() - started
        assert entered.wait(5)
        assert not release.is_set()  # Save returned while generation is blocked.
        with Session(database) as session:
            tables = get_tables_by_ds_id(session, ds_id)
            assert len(tables) == 100
            config = replace(load_embedding_config(session), table_count=10)
            fallback, names = crud.get_table_schema(
                session,
                SimpleNamespace(id=1, oid=1),
                crud.get_ds(session, ds_id),
                "metric question",
                config=config,
            )
            assert len(names) == 100
            assert all("vectors" not in table.model_dump() for table in tables)
            field = (
                session.query(CoreField)
                .filter(CoreField.table_id == tables[0].id)
                .first()
            )
            field_id, table_id = field.id, field.table_id
        edit_started = time.monotonic()
        for index in range(20):
            with Session(database) as session:
                crud.updateField(
                    session,
                    CoreField(
                        id=field_id,
                        ds_id=ds_id,
                        table_id=table_id,
                        checked=True,
                        custom_comment=f"latest_{index}",
                    ),
                )
        edit_seconds = time.monotonic() - edit_started
        pending = embedding_threads.fill_empty_table_and_ds_embeddings()
    finally:
        release.set()
    pending.result(timeout=30)
    with Session(database) as session:
        table_chunks = sum(
            len(read_table_vectors(session, table.id)) for table in tables
        )
        datasource_chunks = len(read_datasource_vectors(session, ds_id))
        assert [1, 0] in read_table_vectors(session, table_id)
        selected, names = crud.get_table_schema(
            session,
            SimpleNamespace(id=1, oid=1),
            crud.get_ds(session, ds_id),
            "metric question",
            config=config,
        )
        assert len(names) == 10
    assert peak == 1
    # Captured on demand with -s; no business metadata or credentials are printed.
    with capsys.disabled():
        print(
            "BULK_METRICS:"
            + json.dumps(
                {
                    "tables": 100,
                    "fields": 3040,
                    "save_seconds": saved_seconds,
                    "20_edits_seconds": edit_seconds,
                    "total_seconds": time.monotonic() - started,
                    "encode_calls": calls,
                    "encode_seconds_including_barrier": encode_seconds,
                    "max_concurrent_model_calls": peak,
                    "table_chunks": table_chunks,
                    "datasource_chunks": datasource_chunks,
                    "fallback_tables": 100,
                    "fallback_context_chars": len(fallback),
                    "complete_context_chars": len(selected),
                    "complete_tables": len(names),
                }
            )
        )


def test_backfill_failure_keeps_other_progress_and_later_scan_recovers(
    lifecycle_environment, monkeypatch
):
    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.table import (
        get_tables_by_ds_id,
        run_fill_empty_table_and_ds_embedding,
    )
    from common.utils.embedding_lifecycle import EmbeddingGenerationError

    database, _client, ds_id = lifecycle_environment
    with Session(database) as session:
        tables = get_tables_by_ds_id(session, ds_id)
        ids = [table.id for table in tables]
        broken_name = tables[0].table_name
        invalidate_chunks(session, "table", ids)
        session.commit()
    attempts = []

    def embed(value):
        attempts.append(value)
        if value.startswith(f"# Table: {broken_name}"):
            raise RuntimeError("one resource failed")
        return [1, 0]

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: metadata_model(embed=embed)
    )
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    with pytest.raises(EmbeddingGenerationError) as failure:
        run_fill_empty_table_and_ds_embedding(sessions)
    assert failure.value.ids == (ids[0],)
    assert sum(value.startswith(f"# Table: {broken_name}") for value in attempts) == 3
    with Session(database) as session:
        with pytest.raises(ValueError):
            read_table_vectors(session, ids[0])
        assert all(read_table_vectors(session, key) for key in ids[1:])
    recovered = []
    monkeypatch.setattr(
        EmbeddingModelCache,
        "get_model",
        lambda: metadata_model(embed=lambda value: recovered.append(value) or [1, 0]),
    )
    run_fill_empty_table_and_ds_embedding(sessions)
    assert len(recovered) == 1
    with Session(database) as session:
        assert all(read_table_vectors(session, key) for key in ids)


def test_deleting_tables_during_encoding_does_not_restore_their_chunks(
    lifecycle_environment, monkeypatch
):
    from threading import Event

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud import datasource as crud
    from apps.datasource.crud.table import get_tables_by_ds_id
    from apps.datasource.embedding.metadata_chunks import read_metadata

    database, _client, ds_id = lifecycle_environment
    entered, release = Event(), Event()
    with Session(database) as session:
        table_id = get_tables_by_ds_id(session, ds_id)[0].id
        invalidate_chunks(session, "table", [table_id])
        session.commit()

    def embed(_value):
        entered.set()
        assert release.wait(5)
        return [1, 0]

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: metadata_model(embed=embed)
    )
    monkeypatch.setattr(crud, "check_status", lambda *_args: True)
    monkeypatch.setattr(crud, "get_tables", lambda *_args: [])
    first = embedding_threads.run_save_table_embeddings([table_id])
    try:
        assert entered.wait(5)
        with Session(database) as session:
            crud.chooseTables(session, lambda value: value, ds_id, [])
        later = embedding_threads.fill_empty_table_and_ds_embeddings()
    finally:
        release.set()
    first.result(timeout=5)
    later.result(timeout=5)
    with Session(database) as session:
        assert get_tables_by_ds_id(session, ds_id) == []
        with pytest.raises(ValueError):
            read_metadata(session, "table", table_id, "deleted table")
        assert read_datasource_vectors(session, ds_id)


def test_started_scan_keeps_one_config_snapshot_for_tables_and_datasources(
    lifecycle_environment, monkeypatch
):
    from threading import Event

    from apps.ai_model.embedding import EmbeddingModelCache
    from apps.datasource.crud.table import get_tables_by_ds_id

    database, client, ds_id = lifecycle_environment
    with Session(database) as session:
        ids = [table.id for table in get_tables_by_ds_id(session, ds_id)]
        invalidate_chunks(session, "table", ids)
        invalidate_chunks(session, "datasource", [ds_id])
        session.commit()
    entered, release = Event(), Event()

    def encode(_value):
        entered.set()
        assert release.wait(5)
        return [1, 0]

    monkeypatch.setattr(
        EmbeddingModelCache, "get_model", lambda: metadata_model(embed=encode)
    )
    future = embedding_threads.fill_empty_table_and_ds_embeddings()
    try:
        assert entered.wait(5)
        assert (
            save(
                client, [{"pkey": "embedding.table_enabled", "pval": False}]
            ).status_code
            == 200
        )
    finally:
        release.set()
    future.result(timeout=5)
    with Session(database) as session:
        assert all(read_table_vectors(session, key) for key in ids)
        assert read_datasource_vectors(session, ds_id)
