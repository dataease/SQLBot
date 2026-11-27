"""Regression tests for SQLAlchemy connection pool lifecycle management."""

import hashlib
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


def _load_connection_pool_manager(class_name="ConnectionPoolManager"):
    """Load only ConnectionPoolManager to avoid importing database drivers."""
    with open(_SRC_PATH, encoding="utf-8") as file:
        source = file.read()

    tree = ast.parse(source)
    class_node = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == class_name
    )

    class CoreDatasource:
        pass

    class AssistantOutDsSchema:
        pass

    namespace = {
        "threading": threading,
        "hashlib": hashlib,
        "aes_decrypt": lambda value: value,
        "equals_ignore_case": lambda a, b: a.lower() == b.lower(),
        "OrderedDict": OrderedDict,
        "CoreDatasource": CoreDatasource,
        "AssistantOutDsSchema": AssistantOutDsSchema,
        "sessionmaker": sessionmaker,
        "get_engine": None,
    }
    module = ast.Module(body=[class_node], type_ignores=[])
    ast.fix_missing_locations(module)
    exec(compile(module, _SRC_PATH, "exec"), namespace)
    return namespace[class_name], namespace


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

    manager.get_pool(SimpleNamespace(id="ds-1", type="pg", configuration="old"))
    manager.remove_pool("ds-1")

    created_engines[0].dispose.assert_called_once_with()
    assert "ds-1" not in manager._pools


def test_lru_eviction_disposes_oldest_engine():
    created_engines = []
    _namespace["get_engine"] = _engine_factory(created_engines)
    manager = ConnectionPoolManager(max_pools=1)

    manager.get_pool(SimpleNamespace(id="ds-1", type="pg", configuration="old"))
    manager.get_pool(SimpleNamespace(id="ds-2", type="pg", configuration="old"))

    created_engines[0].dispose.assert_called_once_with()
    created_engines[1].dispose.assert_not_called()


def test_close_all_disposes_every_engine():
    created_engines = []
    _namespace["get_engine"] = _engine_factory(created_engines)
    manager = ConnectionPoolManager(max_pools=2)

    manager.get_pool(SimpleNamespace(id="ds-1", type="pg", configuration="old"))
    manager.get_pool(SimpleNamespace(id="ds-2", type="pg", configuration="old"))
    manager.close_all()

    for engine in created_engines:
        engine.dispose.assert_called_once_with()
    assert not manager._pools


def test_configuration_change_replaces_pool_without_web_invalidation():
    created_engines = []
    _namespace["get_engine"] = _engine_factory(created_engines)
    manager = ConnectionPoolManager()
    ds = SimpleNamespace(id="ds-1", type="pg", configuration="old")
    original = manager.get_pool(ds)
    assert manager.get_pool(ds) is original
    ds.configuration = "new"
    replacement = manager.get_pool(ds)
    assert replacement is not original
    assert manager.get_pool(ds) is replacement
    created_engines[0].dispose.assert_called_once_with()
    assert len(created_engines) == 2


def test_driver_configuration_change_and_cleanup():
    manager_class, namespace = _load_connection_pool_manager("DriverConnectionPoolManager")
    created = []

    def create_pool(ds, config, use_pool=False):
        assert use_pool
        pool = Mock()
        created.append(pool)
        return pool

    namespace["get_driver_connection"] = create_pool
    manager = manager_class(max_pools=1)
    ds = SimpleNamespace(id="ds-1", type="mysql", configuration="old")
    original = manager.get_pool(ds, {})
    assert manager.get_pool(ds, {}) is original
    ds.configuration = "new"
    replacement = manager.get_pool(ds, {})
    original.close.assert_called_once_with()
    assert replacement is not original
    assert manager.get_pool(ds, {}) is replacement
    manager.remove_pool(ds.id)
    replacement.close.assert_called_once_with()
    assert not manager._fingerprints
