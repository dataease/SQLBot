# ruff: noqa: F811
"""Opt-in PostgreSQL datasource lifecycle and persisted preselection acceptance."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest
from metadata_test_support import read_datasource_vectors
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlmodel import Session
from test_embedding_parameters_integration import (  # noqa: F401
    knowledge_environment,
    pytestmark,
)
from test_metadata_table_chunks import BoundaryModel
from test_table_parameters_integration import table_environment  # noqa: F401

from apps.ai_model.embedding import EmbeddingModelCache
from apps.datasource.crud import datasource as crud
from apps.datasource.crud.table import save_ds_embedding
from apps.datasource.embedding.ds_embedding import get_ds_embedding
from apps.datasource.models.datasource import (
    ColumnSchema,
    CoreDatasource,
    CoreField,
    CoreTable,
)
from common.core.embedding_config import load_embedding_config
from common.utils import embedding_threads
from common.utils.metadata_scheduler import MetadataScheduler


@pytest.fixture
def datasource_environment(table_environment, monkeypatch):
    database, client, ds_id = table_environment
    sessions = scoped_session(sessionmaker(bind=database, class_=Session))
    monkeypatch.setattr(embedding_threads, "session_maker", sessions)
    model = BoundaryModel()
    monkeypatch.setattr(EmbeddingModelCache, "get_model", lambda: model)
    futures = []
    with ThreadPoolExecutor(max_workers=2) as executor:

        def submit(function, *args):
            future = executor.submit(function, *args)
            futures.append(future)
            return future

        scheduler = MetadataScheduler(
            embedding_threads._run_metadata_batch,
            executor=SimpleNamespace(submit=submit, shutdown=executor.shutdown),
        )
        monkeypatch.setattr(embedding_threads, "metadata_scheduler", scheduler)
        try:
            yield database, client, ds_id, sessions, futures, model
        finally:
            scheduler.shutdown()
    sessions.remove()


def drain(futures):
    for future in futures:
        future.result(timeout=30)
    futures.clear()


def test_saved_late_table_field_controls_persisted_datasource_preselection(
    datasource_environment,
):
    database, _client, ds_id, sessions, futures, model = datasource_environment
    with Session(database) as session:
        other_ids = []
        for index in range(12):
            source = CoreDatasource(name=f"other{index}", type="pg", embedding="[1,0]")
            session.add(source)
            session.flush()
            other_ids.append(source.id)
        for index in range(5):
            table = CoreTable(ds_id=ds_id, table_name=f"later_table_{index}")
            session.add(table)
            session.flush()
            for field_index in range(30):
                field = CoreField(
                    ds_id=ds_id,
                    table_id=table.id,
                    field_name=f"metric{field_index}",
                    field_type="INT",
                    field_index=field_index,
                )
                session.add(field)
        session.flush()
        table_id, field_id = table.id, field.id
        session.commit()
        crud.updateField(
            session,
            CoreField(
                id=field_id,
                ds_id=ds_id,
                table_id=table_id,
                checked=True,
                custom_comment="TAIL",
            ),
        )
    drain(futures)
    save_ds_embedding(sessions, other_ids)
    candidates = [{"id": key, "name": "allowed"} for key in other_ids[:-1] + [ds_id]]
    with Session(database) as session:
        assert len(read_datasource_vectors(session, ds_id)) > 30
        result = get_ds_embedding(
            session,
            candidates,
            None,
            "synonym",
            config=replace(load_embedding_config(session), datasource_count=10),
        )
        assert len(result) == 10 and result[0] is candidates[-1]
        assert other_ids[-1] not in {candidate["id"] for candidate in result}
        assert all(set(candidate) == {"id", "name"} for candidate in result)
    assert "TAIL" in "".join(model.inputs)


@pytest.mark.parametrize(
    "operation",
    [
        "rename",
        "table_comment",
        "table_checked",
        "field_comment",
        "field_checked",
        "choose",
    ],
)
@pytest.mark.parametrize("enabled", [True, False])
def test_metadata_save_invalidates_and_regenerates_parent_representation(
    datasource_environment, monkeypatch, operation, enabled
):
    from common.core.config import settings

    database, _client, ds_id, _sessions, futures, model = datasource_environment
    monkeypatch.setattr(settings, "TABLE_EMBEDDING_ENABLED", enabled)
    with Session(database) as session:
        before = read_datasource_vectors(session, ds_id)
        assert before == [[1, 0]]
        table = (
            session.query(CoreTable)
            .filter(CoreTable.ds_id == ds_id, CoreTable.checked.is_(True))
            .first()
        )
        field = session.query(CoreField).filter(CoreField.table_id == table.id).first()
        if operation == "rename":
            crud.update_ds(
                session,
                lambda value: value,
                SimpleNamespace(oid=1),
                CoreDatasource(id=ds_id, name="renamed", description="TAIL"),
            )
        elif operation.startswith("table"):
            crud.updateTable(
                session,
                CoreTable(
                    id=table.id,
                    ds_id=ds_id,
                    checked=operation != "table_checked",
                    custom_comment="TAIL",
                ),
            )
        elif operation.startswith("field"):
            crud.updateField(
                session,
                CoreField(
                    id=field.id,
                    ds_id=ds_id,
                    table_id=table.id,
                    checked=operation != "field_checked",
                    custom_comment="TAIL",
                ),
            )
        else:
            monkeypatch.setattr(
                crud,
                "getFieldsByDs",
                lambda *_args: [ColumnSchema("TAIL", "INT", "selected")],
            )
            monkeypatch.setattr(crud, "get_tables", lambda *_args: [])
            monkeypatch.setattr(crud, "check_status", lambda *_args: True)
            crud.chooseTables(
                session,
                lambda value: value,
                ds_id,
                [CoreTable(table_name="new_selected")],
            )
    drain(futures)
    with Session(database) as session:
        if not enabled:
            assert model.inputs == []
            with pytest.raises(ValueError):
                read_datasource_vectors(session, ds_id)
            return
        after = read_datasource_vectors(session, ds_id)
        # The saved input is fully current; a legacy vector was not reused.
        assert len(after) > 1
        if operation not in ("table_checked", "field_checked"):
            assert [1.0, 0.0] in after
        else:
            assert [1.0, 0.0] not in after


def test_datasource_edit_during_encoding_never_publishes_old_input(
    datasource_environment, monkeypatch
):
    from threading import Event

    database, _client, ds_id, _sessions, futures, model = datasource_environment
    old_started, release_old = Event(), Event()
    new_started, release_new = Event(), Event()
    encode = model.embed_documents

    def controlled_encode(texts):
        if any("OLDER" in text for text in texts):
            old_started.set()
            assert release_old.wait(10), "old provider was not released"
        if any("TAIL" in text for text in texts):
            new_started.set()
            assert release_new.wait(10), "new provider was not released"
        return encode(texts)

    monkeypatch.setattr(model, "embed_documents", controlled_encode)
    try:
        with Session(database) as session:
            crud.update_ds(
                session,
                lambda value: value,
                SimpleNamespace(oid=1),
                CoreDatasource(id=ds_id, name="source", description="OLDER"),
            )
        assert old_started.wait(10)
        with Session(database) as session:
            crud.update_ds(
                session,
                lambda value: value,
                SimpleNamespace(oid=1),
                CoreDatasource(id=ds_id, name="source", description="TAIL"),
            )
        release_old.set()
        assert new_started.wait(10)
        with Session(database) as session:
            with pytest.raises(ValueError):
                read_datasource_vectors(session, ds_id)
        release_new.set()
        drain(futures)
        with Session(database) as session:
            assert [1.0, 0.0] in read_datasource_vectors(session, ds_id)
    finally:
        release_old.set()
        release_new.set()
