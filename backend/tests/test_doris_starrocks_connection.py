"""Regression coverage for Doris/StarRocks connection parameter forwarding."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.datasource.models.datasource import DatasourceConf

SOURCE = Path(__file__).parents[1] / "apps" / "db" / "db.py"


@pytest.fixture
def driver_connection():
    """Load production functions without importing unrelated database drivers."""
    nodes = ast.parse(SOURCE.read_text(encoding="utf-8")).body
    selected = [
        node
        for node in nodes
        if isinstance(node, ast.FunctionDef)
        and node.name in {"get_extra_config", "get_driver_connection"}
    ]
    connect = Mock()
    pool = Mock()
    driver = SimpleNamespace(connect=connect)
    namespace = {
        "CoreDatasource": SimpleNamespace,
        "AssistantOutDsSchema": SimpleNamespace,
        "DatasourceConf": DatasourceConf,
        "json": json,
        "aes_decrypt": lambda value: value,
        "equals_ignore_case": lambda value, *options: (
            value.lower() in [option.lower() for option in options]
        ),
        "pymysql": driver,
        "PooledDB": pool,
    }
    exec(
        compile(ast.Module(body=selected, type_ignores=[]), str(SOURCE), "exec"),
        namespace,
    )
    return namespace["get_driver_connection"], connect, pool, driver


def _datasource(datasource_type, ssl, extra_jdbc):
    return SimpleNamespace(
        type=datasource_type,
        configuration=json.dumps(
            {
                "username": "test-user",
                "password": "test-password",
                "host": "test-host",
                "port": 9030,
                "database": "test-db",
                "timeout": 30,
                "ssl": ssl,
                "poolSize": 8,
                "extraJdbc": extra_jdbc,
            }
        ),
    )


def _connection_options(ssl):
    options = {
        "user": "test-user",
        "passwd": "test-password",
        "host": "test-host",
        "port": 9030,
        "db": "test-db",
        "connect_timeout": 30,
        "read_timeout": 30,
    }
    if ssl:
        options["ssl"] = {"ssl_mode": "REQUIRE"}
    return options


@pytest.mark.parametrize("datasource_type", ["doris", "starrocks"])
@pytest.mark.parametrize("ssl", [False, True])
@pytest.mark.parametrize(
    ("extra_jdbc", "db_config", "expected_extra"),
    [
        ("", {}, {}),
        ("charset=utf8mb4", {}, {"charset": "utf8mb4"}),
        (
            "charset=latin1",
            {"charset": "utf8mb4", "autocommit": True},
            {"charset": "utf8mb4", "autocommit": True},
        ),
    ],
    ids=["defaults", "extra-parameter", "config-override"],
)
def test_direct_connection_forwards_merged_parameters(
    driver_connection, datasource_type, ssl, extra_jdbc, db_config, expected_extra
):
    get_connection, connect, pool, _ = driver_connection
    datasource = _datasource(datasource_type, ssl, extra_jdbc)

    connection = get_connection(datasource, db_config)

    assert connection is connect.return_value
    connect.assert_called_once_with(**(_connection_options(ssl) | expected_extra))
    pool.assert_not_called()


@pytest.mark.parametrize("datasource_type", ["doris", "starrocks"])
@pytest.mark.parametrize("ssl", [False, True])
def test_pooled_connection_preserves_parameters(
    driver_connection, datasource_type, ssl
):
    get_connection, connect, pool, driver = driver_connection
    datasource = _datasource(datasource_type, ssl, "charset=latin1")

    connection = get_connection(
        datasource, {"charset": "utf8mb4", "autocommit": True}, use_pool=True
    )

    assert connection is pool.return_value
    pool.assert_called_once_with(
        creator=driver,
        **_connection_options(ssl),
        charset="utf8mb4",
        autocommit=True,
        maxconnections=8,
        mincached=5,
        maxcached=10,
        blocking=True,
        maxusage=100,
        ping=1,
    )
    connect.assert_not_called()
