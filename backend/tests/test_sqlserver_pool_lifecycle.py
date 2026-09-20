"""Regression coverage for issue 1330's SQL Server pool reconnect path."""

import ast
import json
import sqlite3
import threading
from collections import OrderedDict
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import make_transient_to_detached, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlmodel import Session

from apps.datasource.models.datasource import CoreDatasource, DatasourceConf


SOURCE = Path(__file__).parents[1] / "apps" / "db" / "db.py"


def _load_pool_code(connect):
    """Load the production functions without importing unrelated DB drivers."""
    nodes = ast.parse(SOURCE.read_text()).body
    selected = [node for node in nodes if
                (isinstance(node, ast.FunctionDef) and node.name == "get_engine") or
                (isinstance(node, ast.ClassDef) and node.name == "ConnectionPoolManager")]

    def build_engine(url, creator, **options):
        assert url == "mssql+pymssql://"
        assert options["pool_recycle"] == 3600
        # Force a new DBAPI connection at the next checkout rather than waiting an hour.
        return create_engine("sqlite://", creator=creator, poolclass=QueuePool,
                             pool_recycle=0)

    namespace = {
        "CoreDatasource": CoreDatasource,
        "AssistantOutDsSchema": type("AssistantOutDsSchema", (), {}),
        "DatasourceConf": DatasourceConf,
        "Engine": object,
        "json": json,
        "aes_decrypt": lambda value: value,
        "equals_ignore_case": lambda left, right: left.lower() == right.lower(),
        "create_engine": build_engine,
        "get_origin_connect": connect,
        "NullPool": NullPool,
        "threading": threading,
        "OrderedDict": OrderedDict,
        "sessionmaker": sessionmaker,
    }
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["ConnectionPoolManager"]()


@pytest.mark.parametrize("finish", ["commit", "rollback"])
def test_preview_created_pool_reconnects_after_request_session_closes(finish):
    connections = []

    def connect(ds_type, conf):
        connections.append((ds_type, conf.host, conf.database))
        return sqlite3.connect(":memory:")

    manager = _load_pool_code(connect)
    metadata_engine = create_engine("sqlite://")
    configuration = json.dumps({"host": "test-host", "database": "test-db"})
    datasource = CoreDatasource(id=1330, type="sqlServer", configuration=configuration)
    make_transient_to_detached(datasource)
    try:
        with Session(metadata_engine) as request_session:
            request_session.add(datasource)
            with manager.get_pool(datasource)() as sql_session:
                assert sql_session.execute(text("SELECT 1")).scalar_one() == 1
            getattr(request_session, finish)()

        # A later chat/MCP request reuses the pool created by the preview request.
        later_datasource = CoreDatasource(id=1330, type="sqlServer", configuration=configuration)
        with manager.get_pool(later_datasource)() as sql_session:
            assert sql_session.execute(text("SELECT 1")).scalar_one() == 1
        assert len(connections) >= 2
        assert all(connection == ("sqlServer", "test-host", "test-db")
                   for connection in connections)
    finally:
        manager.close_all()
        metadata_engine.dispose()
