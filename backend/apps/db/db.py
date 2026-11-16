import base64
import json
import os
import platform
import urllib.parse
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional, List

import oracledb
import psycopg2
import pymssql

from apps.db.db_sql import get_table_sql, get_field_sql, get_version_sql
from common.error import ParseSQLResultError

if platform.system() != "Darwin":
    import dmPython
import pymysql
import redshift_connector
from sqlalchemy import create_engine, text, Engine
from sqlalchemy.orm import sessionmaker

from apps.datasource.models.datasource import DatasourceConf, CoreDatasource, TableSchema, ColumnSchema
from apps.datasource.utils.utils import aes_decrypt
from apps.db.constant import DB, ConnectType
from apps.db.dialect import dialect_registry
from apps.db.sql_guard import BASIC as GUARD_BASIC, SqlRejected, build_context as build_guard_context, \
    get_pipeline as get_guard_pipeline
from apps.db.sql_guard import basic as sql_guard_basic
from apps.db.engine import get_engine_config
from apps.system.crud.assistant import get_out_ds_conf
from apps.system.schemas.system_schema import AssistantOutDsSchema
from common.core.deps import Trans
from common.utils.utils import SQLBotLogUtil, equals_ignore_case
from fastapi import HTTPException
from apps.db.es_engine import get_es_connect, get_es_index, get_es_fields, get_es_data_by_http
from common.core.config import settings
import sqlglot
from sqlglot import expressions as exp
from pyhive import hive
from sqlalchemy.pool import NullPool
from dbutils.pooled_db import PooledDB

try:
    if os.path.exists(settings.ORACLE_CLIENT_PATH):
        oracledb.init_oracle_client(
            lib_dir=settings.ORACLE_CLIENT_PATH
        )
        SQLBotLogUtil.info("init oracle client success, use thick mode")
    else:
        SQLBotLogUtil.info("init oracle client failed, because not found oracle client, use thin mode")
except Exception as e:
    SQLBotLogUtil.error("init oracle client failed, check your client is installed, use thin mode")


def get_uri(ds: CoreDatasource) -> str:
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if not equals_ignore_case(ds.type,
                                                                                                 "excel") else get_engine_config()
    return get_uri_from_config(ds.type, conf)


def get_uri_from_config(type: str, conf: DatasourceConf) -> str:
    db_url: str
    if equals_ignore_case(type, "mysql"):
        checkParams(conf.extraJdbc, DB.mysql.illegalParams)
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"mysql+pymysql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"mysql+pymysql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "sqlServer"):
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"mssql+pymssql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"mssql+pymssql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "pg", "excel"):
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"postgresql+psycopg2://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"postgresql+psycopg2://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "oracle"):
        if equals_ignore_case(conf.mode, "service_name", "serviceName"):
            if conf.extraJdbc is not None and conf.extraJdbc != '':
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}?service_name={conf.database}&{conf.extraJdbc}"
            else:
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}?service_name={conf.database}"
        else:
            if conf.extraJdbc is not None and conf.extraJdbc != '':
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
            else:
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif equals_ignore_case(type, "ck"):
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"clickhouse+http://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"clickhouse+http://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    else:
        raise 'The datasource type not support.'
    return db_url


def get_extra_config(conf: DatasourceConf):
    config_dict = {}
    if conf.extraJdbc:
        config_arr = conf.extraJdbc.split("&")
        for config in config_arr:
            kv = config.split("=")
            if len(kv) == 2 and kv[0] and kv[1]:
                config_dict[kv[0]] = kv[1]
            else:
                raise Exception(f'param: {config} is error')
    return config_dict


def get_origin_connect(type: str, conf: DatasourceConf):
    extra_config_dict = get_extra_config(conf)
    if equals_ignore_case(type, "sqlServer"):
        # none or true, set tds_version = 7.0
        if conf.lowVersion is None or conf.lowVersion:
            extra_config_dict['tds_version'] = '7.0'

        return pymssql.connect(
            server=conf.host,
            port=str(conf.port),
            user=conf.username,
            password=conf.password,
            database=conf.database,
            timeout=conf.timeout,
            **extra_config_dict
        )


def is_spark_thrift(conf: DatasourceConf) -> bool:
    """Whether the hive datasource points to a Spark Thrift Server."""
    engine = getattr(conf, 'engine', None) or 'hive'
    return equals_ignore_case(engine, 'spark')


def parse_hive_table_rows(res, is_spark: bool):
    """Parse SHOW TABLES result rows.

    - HiveServer2 returns a single `tab_name` column.
    - Spark Thrift Server (2.4+ through 4.x) returns
      `(database, tableName, isTemporary)`; the plain table name always sits in
      the second column. Over the legacy Hive-JDBC path a header row named
      `tableName` may be returned in-band, which we skip defensively.

    Returns a list of (table_name, comment) tuples.
    """
    tables = []
    seen = set()
    for item in res:
        if not item:
            continue
        row = [c.decode('utf-8') if isinstance(c, bytes) else c for c in item]
        row = [str(c) if c is not None else '' for c in row]

        if is_spark:
            # Spark Thrift Server returns (database, tableName, isTemporary).
            if len(row) >= 2:
                # Skip a possible in-band header row over the legacy Hive-JDBC path.
                if row[1].lower() == 'tablename':
                    continue
                name = row[1].strip()
            else:
                name = row[0].strip()
        else:
            # HiveServer2 returns a single tab_name column.
            name = row[0].strip()

        if not name or name in seen:
            continue
        seen.add(name)
        tables.append((name, ''))
    return tables


def parse_hive_field_rows(res, is_spark: bool):
    """Parse DESCRIBE table result rows for HiveServer2 and Spark Thrift Server
    (all Spark 2.4+ versions use the same col_name/data_type/comment shape with
    a `# Partition Information` / `# col_name` section).

    On the legacy Hive-JDBC path the (col_name, data_type, comment) header may
    also be returned in-band; we skip it defensively.

    Returns a list of (field_name, field_type, field_comment) tuples.
    """
    fields = []
    seen_fields = set()
    for item in res:
        field_name = item[0] if len(item) > 0 else None
        field_type = item[1] if len(item) > 1 else None
        field_comment = item[2] if len(item) > 2 else None

        if not field_name or not str(field_name).strip():
            continue
        stripped_name = str(field_name).strip()

        type_str = (field_type or '').strip() if isinstance(field_type, str) else (str(field_type).strip() if field_type else '')

        # Legacy Hive-JDBC path may return the column header row as data.
        if is_spark and stripped_name.lower() == 'col_name':
            continue

        # DESCRIBE includes section headings and repeats partition columns.
        if stripped_name.lstrip().startswith('#') and type_str in ('', 'data_type'):
            continue
        if stripped_name in seen_fields:
            continue
        seen_fields.add(stripped_name)
        fields.append((field_name, type_str, field_comment))
    return fields


# use sqlalchemy
def get_engine(ds: CoreDatasource, timeout: int = 0, use_pool: bool = False) -> Engine:
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if not equals_ignore_case(ds.type,
                                                                                                 "excel") else get_engine_config()
    if conf.timeout is None:
        conf.timeout = timeout
    if timeout > 0:
        conf.timeout = timeout

    db_config = {
        'pool_size': conf.poolSize if conf.poolSize else 5,
        'max_overflow': 20,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
        'pool_timeout': conf.timeout if conf.timeout else 30
    } if use_pool else {
        'poolclass': NullPool
    }

    if equals_ignore_case(ds.type, "pg"):
        if conf.dbSchema is not None and conf.dbSchema != "":
            engine = create_engine(get_uri(ds),
                                   connect_args={"options": f"-c search_path={urllib.parse.quote(conf.dbSchema)}",
                                                 "connect_timeout": conf.timeout}, **db_config)
        else:
            engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout}, **db_config)
    elif equals_ignore_case(ds.type, 'sqlServer'):
        # A pooled connection may be recreated after the datasource's ORM session closes.
        ds_type = ds.type
        engine = create_engine('mssql+pymssql://', creator=lambda: get_origin_connect(ds_type, conf),
                               **db_config)
    elif equals_ignore_case(ds.type, 'oracle'):
        engine = create_engine(get_uri(ds), connect_args={"tcp_connect_timeout": conf.timeout}, **db_config)
    elif equals_ignore_case(ds.type, 'mysql'):  # mysql
        ssl_mode = {"require": True} if conf.ssl else None
        engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout, "ssl": ssl_mode},
                               **db_config)
    else:  # ck
        engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout}, **db_config)
    return engine


def get_session(ds: CoreDatasource | AssistantOutDsSchema):
    # engine = get_engine(ds) if isinstance(ds, CoreDatasource) else get_ds_engine(ds)
    if isinstance(ds, AssistantOutDsSchema):
        out_conf = get_out_ds_conf(ds, 30)
        ds.configuration = out_conf

    # engine = get_engine(ds)
    # session_maker = sessionmaker(bind=engine)

    # get session from pool
    session = pool_manager.get_pool(ds=ds, **{})
    return session()


def get_driver_connection(ds: CoreDatasource | AssistantOutDsSchema, db_config: dict = {}, use_pool: bool = False):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    extra_config_dict = get_extra_config(conf)

    pool_config = {
        'maxconnections': conf.poolSize if conf.poolSize else 5,
        'mincached': 5,
        'maxcached': 10,
        'blocking': True,
        'maxusage': 100,
        'ping': 1,
    } if use_pool else {}
    conn_conf = extra_config_dict | db_config | pool_config

    conn = None
    if equals_ignore_case(ds.type, 'dm'):
        if not use_pool:
            conn = dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                    port=conf.port, **conn_conf)
        else:
            conn = PooledDB(
                creator=dmPython,
                user=conf.username,
                password=conf.password,
                server=conf.host,
                port=conf.port,
                **conn_conf
            )
    elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
        ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
        args = conn_conf | ssl_args
        if not use_pool:
            conn = pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                   port=conf.port, db=conf.database, connect_timeout=conf.timeout,
                                   read_timeout=conf.timeout,
                                   **args)
        else:
            conn = PooledDB(
                creator=pymysql,
                user=conf.username,
                passwd=conf.password,
                host=conf.host,
                port=conf.port,
                db=conf.database,
                connect_timeout=conf.timeout,
                read_timeout=conf.timeout,
                **args
            )
    elif equals_ignore_case(ds.type, 'redshift'):
        if not use_pool:
            conn = redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database,
                                              user=conf.username,
                                              password=conf.password,
                                              timeout=conf.timeout, **conn_conf)
        else:
            conn = PooledDB(
                creator=redshift_connector,
                host=conf.host,
                port=conf.port,
                database=conf.database,
                user=conf.username,
                password=conf.password,
                timeout=conf.timeout,
                **conn_conf
            )
    elif equals_ignore_case(ds.type, 'kingbase'):
        if not use_pool:
            conn = psycopg2.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                    password=conf.password,
                                    options=f"-c statement_timeout={conf.timeout * 1000}",
                                    **conn_conf)
        else:
            conn = PooledDB(
                creator=psycopg2,
                host=conf.host,
                port=conf.port,
                database=conf.database,
                user=conf.username,
                password=conf.password,
                options=f"-c statement_timeout={conf.timeout * 1000}",
                **conn_conf
            )
    elif equals_ignore_case(ds.type, 'hive'):
        if conf.password:
            conn_conf['password'] = conf.password
            conn_conf['auth'] = 'LDAP'

        if not use_pool:
            conn = hive.connect(host=conf.host, port=conf.port, username=conf.username, database=conf.database,
                                **conn_conf)
        else:
            conn = PooledDB(
                creator=hive,
                host=conf.host,
                port=conf.port,
                username=conf.username,
                database=conf.database,
                **conn_conf
            )

    return conn


def get_driver_pool(ds: CoreDatasource | AssistantOutDsSchema, db_config: dict = {}):
    pool = driver_pool_manager.get_pool(ds, db_config)
    return pool


def check_connection(trans: Optional[Trans], ds: CoreDatasource | AssistantOutDsSchema, is_raise: bool = False):
    if isinstance(ds, AssistantOutDsSchema):
        out_conf = get_out_ds_conf(ds, 10)
        ds.configuration = out_conf

    db = DB.get_db(ds.type)
    if db.connect_type == ConnectType.sqlalchemy:
        conn = get_engine(ds, 10)
        try:
            with conn.connect() as connection:
                SQLBotLogUtil.info("success")
                return True
        except Exception as e:
            SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
            if is_raise:
                raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
            return False
    else:
        conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port, **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute('select 1', timeout=10).fetchall()
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                    return False
        elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
            ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
            with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                 port=conf.port, db=conf.database, connect_timeout=10,
                                 read_timeout=10, **extra_config_dict, **ssl_args) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute('select 1')
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                    return False
        elif equals_ignore_case(ds.type, 'redshift'):
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database,
                                            user=conf.username,
                                            password=conf.password,
                                            timeout=10, **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute('select 1')
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                    return False
        elif equals_ignore_case(ds.type, 'kingbase'):
            with psycopg2.connect(host=conf.host, port=conf.port, database=conf.database,
                                  user=conf.username,
                                  password=conf.password,
                                  connect_timeout=10, **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute('select 1')
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                    return False
        elif equals_ignore_case(ds.type, 'hive'):
            if conf.password:
                extra_config_dict['password'] = conf.password
                extra_config_dict['auth'] = 'LDAP'
            with hive.connect(host=conf.host, port=conf.port, username=conf.username, database=conf.database,
                              **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute('select 1')
                    SQLBotLogUtil.info("success")
                    return True
                except Exception as e:
                    SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                    if is_raise:
                        raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                    return False

        elif equals_ignore_case(ds.type, 'es'):
            es_conn = get_es_connect(conf)
            if es_conn.ping():
                SQLBotLogUtil.info("success")
                return True
            else:
                SQLBotLogUtil.info("failed")
                return False
    # else:
    #     conn = get_ds_engine(ds)
    #     try:
    #         with conn.connect() as connection:
    #             SQLBotLogUtil.info("success")
    #             return True
    #     except Exception as e:
    #         SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
    #         if is_raise:
    #             raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
    #         return False

    return False


def get_version(ds: CoreDatasource | AssistantOutDsSchema):
    version = ''
    if isinstance(ds, CoreDatasource):
        conf = DatasourceConf(
            **json.loads(aes_decrypt(ds.configuration))) if not equals_ignore_case(ds.type,
                                                                                   "excel") else get_engine_config()
    else:
        conf = DatasourceConf(**json.loads(aes_decrypt(get_out_ds_conf(ds, 10))))

    db = DB.get_db(ds.type)
    sql = get_version_sql(ds, conf)
    if not sql:
        return ''
    try:
        if db.connect_type == ConnectType.sqlalchemy:
            with get_session(ds) as session:
                with session.execute(text(sql)) as result:
                    res = result.fetchall()
                    version = res[0][0]
        else:
            extra_config_dict = get_extra_config(conf)
            if equals_ignore_case(ds.type, 'dm'):
                with get_driver_pool(ds).connection() as conn, conn.cursor() as cursor:
                    cursor.execute(sql, timeout=10, **extra_config_dict)
                    res = cursor.fetchall()
                    version = res[0][0]
            elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
                t_conf = {'connect_timeout': 10, 'read_timeout': 10}
                with get_driver_pool(ds, t_conf).connection() as conn, conn.cursor() as cursor:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    version = res[0][0]
            elif equals_ignore_case(ds.type, 'redshift', 'es', 'hive'):
                version = ''
    except Exception as e:
        print(e)
        version = ''
    return version.decode() if isinstance(version, bytes) else version


def get_schema(ds: CoreDatasource):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    db = DB.get_db(ds.type)
    if db.connect_type == ConnectType.sqlalchemy:
        with sessionmaker(bind=get_engine(ds))() as session:
            sql: str = ''
            if equals_ignore_case(ds.type, "sqlServer"):
                sql = """select name
                         from sys.schemas"""
            elif equals_ignore_case(ds.type, "pg", "excel"):
                sql = """SELECT nspname
                         FROM pg_namespace"""
            elif equals_ignore_case(ds.type, "oracle"):
                sql = """select *
                         from all_users"""
            with session.execute(text(sql)) as result:
                res = result.fetchall()
                res_list = [item[0] for item in res]
                return res_list
    else:
        # extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute("""select OBJECT_NAME
                                  from all_objects
                                  where object_type = 'SCH'""", timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'redshift'):
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute("""SELECT nspname
                                  FROM pg_namespace""")
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'kingbase'):
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute("""SELECT nspname
                                  FROM pg_namespace""")
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list


def get_tables(ds: CoreDatasource):
    if equals_ignore_case(ds.type, "excel"):
        # Excel imports share a database; only this datasource's sheets are visible.
        sheets = json.loads(aes_decrypt(ds.configuration)).get("sheets") or []
        return [TableSchema(sheet["tableName"], sheet.get("tableComment")) for sheet in sheets]

    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if not equals_ignore_case(ds.type,
                                                                                                 "excel") else get_engine_config()
    db = DB.get_db(ds.type)
    sql, sql_param = get_table_sql(ds, conf, get_version(ds))
    if db.connect_type == ConnectType.sqlalchemy:
        with sessionmaker(bind=get_engine(ds))() as session:
            with session.execute(text(sql), {"param": sql_param}) as result:
                res = result.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
    else:
        # extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute(sql, {"param": sql_param}, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
            # ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute(sql, (sql_param,))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'redshift'):
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute(sql, (sql_param,))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'kingbase'):
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute(sql, (sql_param,))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'es'):
            res = get_es_index(conf)
            res_list = [TableSchema(*item) for item in res]
            return res_list
        elif equals_ignore_case(ds.type, 'hive'):
            with get_driver_connection(ds) as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in parse_hive_table_rows(res, is_spark_thrift(conf))]
                return res_list


def get_fields(ds: CoreDatasource, table_name: str = None):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if not equals_ignore_case(ds.type,
                                                                                                 "excel") else get_engine_config()
    db = DB.get_db(ds.type)
    sql, p1, p2 = get_field_sql(ds, conf, table_name)
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql), {"param1": p1, "param2": p2}) as result:
                res = result.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
    else:
        # extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with get_driver_pool(ds).connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, {"param1": p1, "param2": p2}, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
            # ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
            with get_driver_pool(ds).connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, (p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'redshift'):
            with get_driver_pool(ds).connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql, (p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'kingbase'):
            with get_driver_pool(ds).connection() as conn, conn.cursor() as cursor:
                # cursor.execute(sql.format(p1, p2))
                cursor.execute(sql, (p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'es'):
            res = get_es_fields(conf, table_name)
            res_list = [ColumnSchema(*item) for item in res]
            return res_list
        elif equals_ignore_case(ds.type, 'hive'):
            with get_driver_pool(ds).connection() as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in parse_hive_field_rows(res, is_spark_thrift(conf))]
                return res_list


def convert_value(value, datetime_format='space'):
    """
        将Python值转换为JSON可序列化的类型

        :param value: 要转换的值
        :param datetime_format: 日期时间格式
            'iso' - 2024-01-15T14:30:45 (ISO标准，带T)
            'space' - 2024-01-15 14:30:45 (空格分隔，更常见)
            'auto' - 自动选择
        """
    if value is None:
        return None
        # 处理 bytes 类型（包括 BIT 字段）
    if isinstance(value, bytes):
        # 1. 尝试判断是否是 BIT 类型
        if len(value) <= 8:  # BIT 类型通常不会很长
            try:
                # 转换为整数
                int_val = int.from_bytes(value, 'big')

                # 如果是 0 或 1，返回布尔值更直观
                if int_val in (0, 1):
                    return bool(int_val)
                else:
                    return int_val
            except:
                # 如果转换失败，尝试解码为字符串
                pass

        # 2. 尝试解码为 UTF-8 字符串
        try:
            return value.decode('utf-8')
        except UnicodeDecodeError:
            # 3. 如果包含非打印字符，返回十六进制
            if any(b < 32 and b not in (9, 10, 13) for b in value):  # 非打印字符
                return f"0x{value.hex()}"
            else:
                # 4. 尝试 Latin-1 解码（不会失败）
                return value.decode('latin-1')

    elif isinstance(value, bytearray):
        # 处理 bytearray
        return convert_value(bytes(value))

    if isinstance(value, timedelta):
        # 将 timedelta 转换为秒数（整数）或字符串
        return str(value)  # 或 value.total_seconds()
    elif isinstance(value, Decimal):
        return float(value)
    # 4. 处理 datetime
    elif isinstance(value, datetime):
        if datetime_format == 'iso':
            return value.isoformat()
        elif datetime_format == 'space':
            return value.strftime('%Y-%m-%d %H:%M:%S')
        else:  # 'auto' 或其他
            # 自动判断：没有时间部分只显示日期
            if value.hour == 0 and value.minute == 0 and value.second == 0 and value.microsecond == 0:
                return value.strftime('%Y-%m-%d')
            else:
                return value.strftime('%Y-%m-%d %H:%M:%S')

    # 5. 处理 date
    elif isinstance(value, date):
        return value.isoformat()  # 总是 YYYY-MM-DD

    # 6. 处理 time
    elif isinstance(value, time):
        return str(value)
    else:
        return value


def is_numeric_type_code(type_code, dialect_name: str) -> bool:
    """
    根据数据库方言和 type_code 判断是否为数值类型

    Args:
        type_code: cursor.description[col_idx][1] 的值
        dialect_name: SQLAlchemy dialect name (mysql/postgresql/mssql/oracle/sqlite 等)

    Returns:
        bool: 是否为数值类型
    """
    dialect_name = dialect_name.lower()

    # ---------- MySQL (pymysql) ----------
    if dialect_name == 'mysql':
        if isinstance(type_code, int):
            return type_code in {
                1,  # TINYINT
                2,  # SMALLINT
                3,  # INT
                4,  # FLOAT
                5,  # DOUBLE
                8,  # BIGINT
                9,  # MEDIUMINT
                16,  # BIT
                246,  # DECIMAL/NEWDECIMAL
            }
        return False

    # ---------- PostgreSQL (psycopg2) ----------
    if dialect_name == 'postgresql':
        if isinstance(type_code, int):
            return type_code in {
                20,  # int8
                21,  # int2
                23,  # int4
                700,  # float4
                701,  # float8
                1700,  # numeric
                16,  # boolean
            }
        return False

    # ---------- Oracle (cx_Oracle / oracledb) ----------
    if dialect_name == 'oracle':
        type_str = str(type_code).upper()
        return any(kw in type_str for kw in ['NUMBER', 'FLOAT', 'INTEGER', 'BINARY_FLOAT', 'BINARY_DOUBLE'])

    if dialect_name == 'clickhouse':
        if isinstance(type_code, str):
            upper_type = type_code.upper()
            # 数值类型关键字
            numeric_prefixes = (
                'INT',  # Int8/16/32/64
                'UINT',  # UInt8/16/32/64  ✅ 加上 UINT
                'FLOAT',  # Float32, Float64
                'DECIMAL',  # Decimal, Decimal32/64/128
                'BOOL',  # Bool
                'BIT',  # 极少数场景
            )
            return any(upper_type.startswith(p) for p in numeric_prefixes)

    # ---------- SQL Server (pyodbc / pymssql) ----------
    if dialect_name == 'mssql':
        if isinstance(type_code, int):
            # SQL Server (pyodbc / ODBC) 数值类型码
            return type_code in {
                2,  # smallint
                3,  # int
                4,  # tinyint
                5,  # float / real / decimal / numeric / money / smallmoney
                6,  # bit
                7,  # bigint
            }

    # ---------- SQLite ----------
    if dialect_name == 'sqlite':
        if isinstance(type_code, int):
            return type_code in {1, 2, 3, 4, 5}  # INTEGER, FLOAT, NUMERIC, etc.
        return False

    # ---------- 未知数据库，保守返回 False ----------
    return False


def is_mssql_string_type_code(type_code) -> bool:
    """
    判断 SQL Server (pymssql) 游标描述中的 type_code 是否为字符串类型。

    pymssql 的 varchar/char/nvarchar/nchar/text 等字符串类型的 type_code 为
    STRING(1)，而数值/日期等类型分别为 NUMBER(3)、DATETIME(4) 等。

    Args:
        type_code: cursor.description[col][1] 的值

    Returns:
        bool: 是否为字符串（varchar 等）类型
    """
    try:
        return type_code == 1
    except Exception:
        return False


def convert_gbk_string(value):
    """
    将 SQL Server 中以 latin-1 读取出的乱码字符串转换为 GBK 编码的正确文本。

    当 varchar 列实际存储的是 GBK 字节（被错误地按 latin-1 解码）时，
    通过 str.encode('latin-1').decode('gbk') 还原。转换中任一步失败则返回原值。
    """
    if not isinstance(value, str):
        return value
    try:
        return value.encode('latin-1').decode('gbk')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return value


def convert_mssql_value(value, col_idx, string_col_idx_set, is_mssql):
    """
    对 SQL Server 结果集中字符串列的值进行 GBK 编码转换。
    """
    if is_mssql and col_idx in string_col_idx_set:
        return convert_gbk_string(value)
    return value


def _fetch_rows(cursor_or_result, max_rows: Optional[int]):
    """fetchall()，或在给定上限时最多取 max_rows 行（用于不能改写 LIMIT 的方言）。"""
    if max_rows is None:
        return cursor_or_result.fetchall()
    return cursor_or_result.fetchmany(max_rows)


def _apply_statement_timeout(session, ds, timeout_seconds: Optional[int]):
    """按方言策略设置单条语句超时；返回恢复回调。方言不支持时返回 None 且不报错。"""
    if not timeout_seconds:
        return None
    policy = dialect_registry.find(ds.type)
    if policy is None or policy.apply_timeout is None:
        SQLBotLogUtil.warning(f"Statement timeout is not supported for datasource type {ds.type}")
        return None
    return policy.apply_timeout(session.connection(), int(timeout_seconds))


def exec_sql(ds: CoreDatasource | AssistantOutDsSchema, sql: str, origin_column=False,
             timeout_seconds: Optional[int] = None, max_rows: Optional[int] = None):
    """执行只读 SQL。

    timeout_seconds：按方言策略设置单条语句超时（仅 sqlalchemy 连接、且方言支持时生效）。
    max_rows：最多读取的行数，用于无法通过改写 SQL 限行的方言；不传则读取全部（原有行为）。
    """
    while sql.endswith(';'):
        sql = sql[:-1]
    # check execute sql only contain read operations
    is_safe, error_reason = check_sql_read(sql, ds)
    if not is_safe:
        raise ValueError(f"SQL can only contain read operations: {error_reason}")

    db = DB.get_db(ds.type)
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            # 获取当前数据库方言
            dialect_name = session.bind.dialect.name
            restore_timeout = _apply_statement_timeout(session, ds, timeout_seconds)
            try:
                return _exec_sqlalchemy(session, sql, dialect_name, origin_column, max_rows)
            finally:
                if restore_timeout is not None:
                    try:
                        restore_timeout()
                    except Exception:
                        SQLBotLogUtil.exception("Failed to restore statement timeout")
    return _exec_driver(ds, sql, origin_column, max_rows)


def _encode_sql(sql: str) -> str:
    return bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))


def _exec_sqlalchemy(session, sql: str, dialect_name: str, origin_column, max_rows: Optional[int]):
    with session.execute(text(sql)) as result:
        try:
            columns = result.keys()._keys if origin_column else [item.lower() for item in result.keys()._keys]

            # SQL Server varchar 等字符串列需做 GBK 编码转换
            is_mssql = dialect_name == 'mssql'
            string_cols = []

            fields_info = []

            for col_idx, col_name in enumerate(columns):
                is_numeric = False
                try:
                    type_code = result.cursor.description[col_idx][1]
                    is_numeric = is_numeric_type_code(type_code, dialect_name)
                    if is_mssql and is_mssql_string_type_code(type_code):
                        string_cols.append(col_idx)
                except (IndexError, AttributeError):
                    pass

                fields_info.append({
                    "name": col_name,
                    "is_numeric": is_numeric
                })

            string_col_idx_set = set(string_cols)

            res = _fetch_rows(result, max_rows)
            result_list = [
                {str(columns[i]): convert_mssql_value(convert_value(value), i, string_col_idx_set, is_mssql)
                 for i, value in enumerate(tuple_item)} for tuple_item in
                res
            ]
            return {"fields": columns, "data": result_list, "fields_info": fields_info, "sql": _encode_sql(sql)}
        except Exception as ex:
            raise ParseSQLResultError(str(ex))


def _hive_sql(sql: str) -> str:
    # Hive uses backticks for identifiers; normalize quoted identifiers as a compatibility fallback.
    return re.sub(r'"([A-Za-z_][A-Za-z0-9_]*)"', r'`\1`', sql)


# py_driver 数据源的执行差异：(字段类型码族, SQL 预处理, 是否传驱动级超时)。
# 新增 py_driver 数据源时在此登记一行，不必复制执行流程。
_DRIVER_EXEC_PROFILES = {
    'dm': ('dm', None, True),
    'doris': ('mysql', None, False),
    'starrocks': ('mysql', None, False),
    'redshift': ('postgresql', None, False),
    'kingbase': ('postgresql', None, False),
    'hive': ('hive', _hive_sql, False),
}


def _exec_driver(ds, sql: str, origin_column, max_rows: Optional[int]):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
    ds_key = (ds.type or '').lower()
    if ds_key == 'es':
        try:
            res, raw_columns = get_es_data_by_http(conf, sql)
            if max_rows is not None:
                res = res[:max_rows]
            columns = [field.get('name') for field in raw_columns] if origin_column else [field.get('name').lower()
                                                                                          for field in raw_columns]
            fields_info = build_fields_info_from_es(raw_columns, origin_column)
            result_list = [
                {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in res
            ]
            return {"fields": columns, "data": result_list, "fields_info": fields_info, "sql": _encode_sql(sql)}
        except Exception as ex:
            raise Exception(str(ex))

    profile = _DRIVER_EXEC_PROFILES.get(ds_key)
    if profile is None:
        # 与旧实现一致：未登记的 py_driver 类型不执行
        return None
    type_family, prepare_sql, driver_timeout = profile
    exec_sql_text = prepare_sql(sql) if prepare_sql else sql
    with get_driver_pool(ds).connection() as conn, conn.cursor() as cursor:
        try:
            if driver_timeout:
                cursor.execute(exec_sql_text, timeout=conf.timeout)
            else:
                cursor.execute(exec_sql_text)
            res = _fetch_rows(cursor, max_rows)
            columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                        field in
                                                                                        cursor.description]
            fields_info = build_fields_info_from_cursor(cursor, origin_column, type_family)
            result_list = [
                {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in res
            ]
            return {"fields": columns, "data": result_list, "fields_info": fields_info,
                    "sql": _encode_sql(exec_sql_text)}
        except Exception as ex:
            raise ParseSQLResultError(str(ex))


def build_fields_info_from_cursor(cursor, origin_column, db_type='postgresql'):
    """
    根据数据库游标的 description 构建字段信息列表

    Args:
        cursor: 数据库游标对象
        origin_column: 是否保留原始列名大小写
        db_type: 数据库类型，支持 'mysql', 'postgresql', 'redshift', 'kingbase', 'dm', 'hive'

    Returns:
        list: 包含字段名和是否数值类型的字典列表
    """
    fields_info = []

    for col_info in cursor.description:
        col_name = col_info[0]

        if db_type in ('mysql', 'mariadb', 'doris', 'starrocks'):
            # MySQL/pymysql 类型码
            is_numeric = col_info[1] in (
                1,  # TINYINT
                2,  # SMALLINT
                3,  # INT
                4,  # FLOAT
                5,  # DOUBLE
                8,  # BIGINT
                9,  # MEDIUMINT
                16,  # BIT
                246,  # DECIMAL/NEWDECIMAL
            )
        elif db_type in ('postgresql', 'redshift', 'kingbase'):
            # PostgreSQL/psycopg2 类型 OID
            is_numeric = col_info[1] in (
                16,  # bool
                20,  # int8
                21,  # int2
                23,  # int4
                700,  # float4
                701,  # float8
                790,  # money
                1700,  # numeric
            )
        elif db_type == 'dm':
            # 达梦数据库类型码 <class 'dmPython.DECIMAL'>
            # 获取类型类名
            type_name = col_info[1].__name__.upper() if hasattr(col_info[1], '__name__') else str(col_info[1]).upper()

            is_numeric = type_name in {
                'INT', 'INTEGER',
                'BIGINT', 'SMALLINT', 'TINYINT',
                'NUMBER', 'NUMERIC', 'DECIMAL',
                'FLOAT', 'DOUBLE', 'REAL',
                'BIT', 'BOOLEAN',
            }
        elif db_type == 'hive':
            # Hive 类型对象转字符串判断
            type_str = str(col_info[1]).lower()
            NUMERIC_PREFIXES = ('tinyint', 'smallint', 'int', 'bigint', 'float', 'double', 'decimal', 'numeric')
            is_numeric = type_str == 'boolean' or any(type_str.startswith(p) for p in NUMERIC_PREFIXES)
        else:
            is_numeric = False

        fields_info.append({
            "name": col_name if origin_column else col_name.lower(),
            "is_numeric": is_numeric
        })

    return fields_info


def build_fields_info_from_es(raw_columns, origin_column):
    """
    专门为 Elasticsearch 构建字段信息

    Args:
        raw_columns: ES 返回的列信息列表
        origin_column: 是否保留原始列名大小写

    Returns:
        list: 包含字段名和是否数值类型的字典列表
    """
    fields_info = []

    for field in raw_columns:
        field_name = field.get('name') if origin_column else field.get('name').lower()
        field_type = field.get('type', '').lower()

        is_numeric = field_type in (
            'long', 'integer', 'short', 'byte',
            'double', 'float', 'half_float', 'scaled_float',
            'unsigned_long', 'boolean'
        )

        fields_info.append({
            "name": field_name,
            "is_numeric": is_numeric
        })

    return fields_info


def get_sqlglot_dialect(ds_type: str) -> str:
    """根据数据源类型获取 sqlglot dialect（来自 apps/db/dialect 的方言策略注册表）"""
    policy = dialect_registry.find(ds_type)
    return policy.sqlglot_dialect if policy else None


# 通用危险函数（适用于所有数据库）；规则本体在 apps/db/sql_guard/basic.py
COMMON_DANGEROUS_FUNCTIONS = set(sql_guard_basic.COMMON_DANGEROUS_FUNCTIONS)

# 特定数据库的危险函数，由方言策略注册表派生（新增数据源类型请注册 DialectPolicy，
# 不要直接改这里）。key 与 DB 枚举的 type 值一致（小写）。
DS_SPECIFIC_DANGEROUS_FUNCTIONS = {
    key: set(dialect_registry.get(key).dangerous_functions)
    for key in sorted(dialect_registry.types())
    if dialect_registry.get(key).dangerous_functions
}

# 危险模式正则表达式（用于检查特殊语法）
import re

DANGEROUS_PATTERNS = list(sql_guard_basic.DANGEROUS_PATTERNS)


def get_dangerous_functions(ds_type: str) -> set:
    """获取危险函数（通用 + 特定数据源）"""
    functions = COMMON_DANGEROUS_FUNCTIONS.copy()
    policy = dialect_registry.find(ds_type)
    if policy:
        functions.update(policy.dangerous_functions)
    return functions


def check_dangerous_functions(statements: list, ds_type: str) -> bool:
    """检查是否使用了危险函数，返回 True 表示安全"""
    dangerous_functions = get_dangerous_functions(ds_type)
    dangerous_functions_upper = {f.upper() for f in dangerous_functions}

    for stmt in statements:
        if stmt:
            for func in stmt.find_all(exp.Anonymous):
                if func.name.upper() in dangerous_functions_upper:
                    return False
    return True


# 规则拒绝（可展示给调用方）时返回 (False, reason)；以下 code 表示无法完成检查，
# 沿用旧行为抛出 ValueError("Parse SQL Error: ...")。
_GUARD_ERROR_CODES = {"parse_error", "check_error", "rewrite_error", "unsupported_dialect"}


def check_sql_read(sql: str, ds: CoreDatasource | AssistantOutDsSchema) -> tuple[bool, str]:
    """
    检查 SQL 是否为安全的只读查询（apps/db/sql_guard 的 basic 规则集）
    返回: (是否安全, 错误原因)；无法解析时抛出 ValueError
    """
    try:
        ctx = build_guard_context(sql, ds.type, allow_metadata_queries=settings.SQLBOT_ALLOW_METADATA_QUERIES)
        get_guard_pipeline(GUARD_BASIC).run(ctx)
        return True, ""
    except SqlRejected as e:
        if e.code in _GUARD_ERROR_CODES:
            detail = e.reason
            raise ValueError(detail if detail.startswith("Parse SQL Error: ") else f"Parse SQL Error: {detail}")
        return False, e.reason
    except Exception as e:
        raise ValueError(f"Parse SQL Error: {e}")


def checkParams(extraParams: str, illegalParams: List[str]):
    kvs = extraParams.split('&')
    for kv in kvs:
        if kv and '=' in kv:
            k, v = kv.split('=')
            if k in illegalParams:
                raise HTTPException(status_code=500, detail=f'Illegal Parameter: {k}')


import threading
from collections import OrderedDict


class ConnectionPoolManager:
    def __init__(self, max_pools=500):
        """
        init
        :param max_pools: max pool
        """
        self.max_pools = max_pools
        self._pools = OrderedDict()  # datasource_id -> (sessionmaker, Engine)
        self._lock = threading.Lock()  # 保证多线程安全

    def get_pool(self, ds: CoreDatasource | AssistantOutDsSchema, **db_config):
        """
        get connection pool（lazy load + LRU update）
        """
        with self._lock:
            if ds.id:
                # 1. 如果连接池已存在，将其移动到字典末尾（标记为最近使用）
                if ds.id in self._pools:
                    if not equals_ignore_case(ds.type, "excel"):
                        aes_decrypt(ds.configuration)
                    self._pools.move_to_end(ds.id)
                    print(f"[LRU] return: {ds.id}")
                    return self._pools[ds.id][0]

                # 2. 如果连接池不存在，检查是否达到上限，若达到则淘汰最久未使用的（字典头部）
                if len(self._pools) >= self.max_pools:
                    oldest_id, (_, oldest_engine) = self._pools.popitem(last=False)
                    oldest_engine.dispose()  # 安全关闭被驱逐的连接池
                    print(f"[LRU] remove oldest: {oldest_id}")

            # 3. 创建新连接池并放入字典末尾
            engine = get_engine(ds, use_pool=True)
            new_pool = sessionmaker(bind=engine)
            self._pools[ds.id] = (new_pool, engine)
            print(f"[LRU] create: {ds.id}")
            return new_pool

    def remove_pool(self, datasource_id):
        with self._lock:
            if datasource_id in self._pools:
                # 1. 从字典中移除并获取该连接池对象
                _, engine = self._pools.pop(datasource_id)
                # 2. 安全关闭该连接池，释放底层所有数据库连接和内存
                engine.dispose()
                print(f"[Manager] Closed pool and remove: {datasource_id}")
            else:
                print(f"[Manager] Warning: ds id {datasource_id} not exist in sqlalchemy")

    def close_all(self):
        """stop"""
        with self._lock:
            for _, engine in self._pools.values():
                engine.dispose()
            self._pools.clear()


pool_manager = ConnectionPoolManager(max_pools=500)


class DriverConnectionPoolManager:
    def __init__(self, max_pools=500):
        """
        init
        :param max_pools: max pool
        """
        self.max_pools = max_pools
        self._pools = OrderedDict()  # 使用有序字典实现 LRU
        self._lock = threading.Lock()  # 保证多线程安全

    def get_pool(self, ds: CoreDatasource | AssistantOutDsSchema, db_config):
        """
        get connection pool（lazy load + LRU update）
        """
        with self._lock:
            if ds.id:
                # 1. 如果连接池已存在，将其移动到字典末尾（标记为最近使用）
                if ds.id in self._pools:
                    if not equals_ignore_case(ds.type, "excel"):
                        aes_decrypt(ds.configuration)
                    self._pools.move_to_end(ds.id)
                    print(f"[LRU] return: {ds.id}")
                    return self._pools[ds.id]

                # 2. 如果连接池不存在，检查是否达到上限，若达到则淘汰最久未使用的（字典头部）
                if len(self._pools) >= self.max_pools:
                    oldest_id, oldest_pool = self._pools.popitem(last=False)
                    oldest_pool.close()  # 安全关闭被驱逐的连接池
                    print(f"[LRU] remove oldest: {oldest_id}")

            # 3. 创建新连接池并放入字典末尾
            new_pool = get_driver_connection(ds, db_config, use_pool=True)
            self._pools[ds.id] = new_pool
            print(f"[LRU] create: {ds.id}")
            return new_pool

    def remove_pool(self, datasource_id):
        with self._lock:
            if datasource_id in self._pools:
                # 1. 从字典中移除并获取该连接池对象
                pool = self._pools.pop(datasource_id)
                # 2. 安全关闭该连接池，释放底层所有数据库连接和内存
                pool.close()
                print(f"[Manager] Closed pool and remove: {datasource_id}")
            else:
                print(f"[Manager] Warning: ds id {datasource_id} not exist in dbutils")

    def close_all(self):
        """stop"""
        with self._lock:
            for pool in self._pools.values():
                pool.close()
            self._pools.clear()


driver_pool_manager = DriverConnectionPoolManager(max_pools=500)
