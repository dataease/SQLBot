"""Regression tests for SQLAlchemy connection pool lifecycle management."""

import ast
import os
import threading
from collections import OrderedDict
from types import SimpleNamespace
from unittest.mock import Mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


_SRC_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "apps",
    "db",
    "db.py",
)


def _load_connection_pool_manager():
    """Load only ConnectionPoolManager to avoid importing database drivers."""
    with open(_SRC_PATH, encoding="utf-8") as file:
        source = file.read()

    tree = ast.parse(source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ConnectionPoolManager"
    )

    class CoreDatasource:
        pass

    class AssistantOutDsSchema:
        pass

    namespace = {
        "threading": threading,
        "OrderedDict": OrderedDict,
        "CoreDatasource": CoreDatasource,
        "AssistantOutDsSchema": AssistantOutDsSchema,
        "sessionmaker": sessionmaker,
        "get_engine": None,
    }
    module = ast.Module(body=[class_node], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, _SRC_PATH, "exec"), namespace)
    return namespace["ConnectionPoolManager"], namespace


ConnectionPoolManager, _namespace = _load_connection_pool_manager()


def _engine_factory(created_engines):
    def get_engine(ds, use_pool=False):
        assert use_pool is True
        engine = create_engine("sqlite://")
        engine.dispose = Mock(wraps=engine.dispose)
        created_engines.append(engine)
        return engine

    return get_engine


def test_remove_pool_disposes_bound_engine():
    created_engines = []
    _namespace["get_engine"] = _engine_factory(created_engines)
    manager = ConnectionPoolManager()

    manager.get_pool(SimpleNamespace(id="ds-1"))
    manager.remove_pool("ds-1")

    created_engines[0].dispose.assert_called_once_with()
    assert "ds-1" not in manager._pools


def test_lru_eviction_disposes_oldest_engine():
    created_engines = []
    _namespace["get_engine"] = _engine_factory(created_engines)
    manager = ConnectionPoolManager(max_pools=1)

    manager.get_pool(SimpleNamespace(id="ds-1"))
    manager.get_pool(SimpleNamespace(id="ds-2"))

    created_engines[0].dispose.assert_called_once_with()
    created_engines[1].dispose.assert_not_called()


def test_close_all_disposes_every_engine():
    created_engines = []
    _namespace["get_engine"] = _engine_factory(created_engines)
    manager = ConnectionPoolManager(max_pools=2)

    manager.get_pool(SimpleNamespace(id="ds-1"))
    manager.get_pool(SimpleNamespace(id="ds-2"))
    manager.close_all()

    for engine in created_engines:
        engine.dispose.assert_called_once_with()
    assert not manager._pools
