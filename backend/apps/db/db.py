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
            return pymssql.connect(
                server=conf.host,
                port=str(conf.port),
                user=conf.username,
                password=conf.password,
                database=conf.database,
                timeout=conf.timeout,
                tds_version='7.0',  # options: '4.2', '7.0', '8.0' ...,
                **extra_config_dict
            )
        else:
            return pymssql.connect(
                server=conf.host,
                port=str(conf.port),
                user=conf.username,
                password=conf.password,
                database=conf.database,
                timeout=conf.timeout,
                **extra_config_dict
            )


# use sqlalchemy
def get_engine(ds: CoreDatasource, timeout: int = 0) -> Engine:
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if not equals_ignore_case(ds.type,
                                                                                                 "excel") else get_engine_config()
    if conf.timeout is None:
        conf.timeout = timeout
    if timeout > 0:
        conf.timeout = timeout

    db_config = {
        'pool_size': conf.poolSize if conf.poolSize else 5,
        'max_overflow': 20,
        'pool_recycle': 3600
    }

    if equals_ignore_case(ds.type, "pg"):
        if conf.dbSchema is not None and conf.dbSchema != "":
            engine = create_engine(get_uri(ds),
                                   connect_args={"options": f"-c search_path={urllib.parse.quote(conf.dbSchema)}",
                                                 "connect_timeout": conf.timeout}, **db_config)
        else:
            engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout}, **db_config)
    elif equals_ignore_case(ds.type, 'sqlServer'):
        engine = create_engine('mssql+pymssql://', creator=lambda: get_origin_connect(ds.type, conf),
                               **db_config)
    elif equals_ignore_case(ds.type, 'oracle'):
        engine = create_engine(get_uri(ds), **db_config)
    elif equals_ignore_case(ds.type, 'mysql'):  # mysql
        ssl_mode = {"require": True} if conf.ssl else None
        engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout, "ssl": ssl_mode},
                               **db_config)
    else:  # ck
        engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout}, **db_config)
    return engine


def get_connection(ds: CoreDatasource | AssistantOutDsSchema, db_config):
    pass


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
            with hive.connect(host=conf.host, port=conf.port, username=conf.username,
                              database=conf.database, **extra_config_dict) as conn, conn.cursor() as cursor:
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
    # if isinstance(ds, AssistantOutDsSchema):
    #     conf = DatasourceConf()
    #     conf.host = ds.host
    #     conf.port = ds.port
    #     conf.username = ds.user
    #     conf.password = ds.password
    #     conf.database = ds.dataBase
    #     conf.dbSchema = ds.db_schema
    #     conf.timeout = 10
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
                with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                      port=conf.port) as conn, conn.cursor() as cursor:
                    cursor.execute(sql, timeout=10, **extra_config_dict)
                    res = cursor.fetchall()
                    version = res[0][0]
            elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
                ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
                with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                     port=conf.port, db=conf.database, connect_timeout=10,
                                     read_timeout=10, **extra_config_dict, **ssl_args) as conn, conn.cursor() as cursor:
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
        with get_session(ds) as session:
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
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute("""select OBJECT_NAME
                                  from all_objects
                                  where object_type = 'SCH'""", timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'redshift'):
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                            password=conf.password,
                                            timeout=conf.timeout, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute("""SELECT nspname
                                  FROM pg_namespace""")
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'kingbase'):
            with psycopg2.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                  password=conf.password,
                                  options=f"-c statement_timeout={conf.timeout * 1000}",
                                  **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute("""SELECT nspname
                                  FROM pg_namespace""")
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list


def get_tables(ds: CoreDatasource):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if not equals_ignore_case(ds.type,
                                                                                                 "excel") else get_engine_config()
    db = DB.get_db(ds.type)
    sql, sql_param = get_table_sql(ds, conf, get_version(ds))
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql), {"param": sql_param}) as result:
                res = result.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
    else:
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql, {"param": sql_param}, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
            ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
            with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                 port=conf.port, db=conf.database, connect_timeout=conf.timeout,
                                 read_timeout=conf.timeout, **extra_config_dict,
                                 **ssl_args) as conn, conn.cursor() as cursor:
                cursor.execute(sql, (sql_param,))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'redshift'):
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                            password=conf.password,
                                            timeout=conf.timeout, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql, (sql_param,))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'kingbase'):
            with psycopg2.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                  password=conf.password,
                                  options=f"-c statement_timeout={conf.timeout * 1000}",
                                  **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql.format(sql_param))
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'es'):
            res = get_es_index(conf)
            res_list = [TableSchema(*item) for item in res]
            return res_list
        elif equals_ignore_case(ds.type, 'hive'):
            with hive.connect(host=conf.host, port=conf.port, username=conf.username,
                              database=conf.database, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
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
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql, {"param1": p1, "param2": p2}, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
            ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
            with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                 port=conf.port, db=conf.database, connect_timeout=conf.timeout,
                                 read_timeout=conf.timeout, **extra_config_dict,
                                 **ssl_args) as conn, conn.cursor() as cursor:
                cursor.execute(sql, (p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'redshift'):
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                            password=conf.password,
                                            timeout=conf.timeout, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql, (p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'kingbase'):
            with psycopg2.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                  password=conf.password,
                                  options=f"-c statement_timeout={conf.timeout * 1000}",
                                  **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql.format(p1, p2))
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif equals_ignore_case(ds.type, 'es'):
            res = get_es_fields(conf, table_name)
            res_list = [ColumnSchema(*item) for item in res]
            return res_list
        elif equals_ignore_case(ds.type, 'hive'):
            with hive.connect(host=conf.host, port=conf.port, username=conf.username,
                              database=conf.database, **extra_config_dict) as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
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


def exec_sql(ds: CoreDatasource | AssistantOutDsSchema, sql: str, origin_column=False):
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

            with session.execute(text(sql)) as result:
                try:
                    columns = result.keys()._keys if origin_column else [item.lower() for item in result.keys()._keys]

                    fields_info = []

                    for col_idx, col_name in enumerate(columns):
                        is_numeric = False
                        try:
                            type_code = result.cursor.description[col_idx][1]
                            is_numeric = is_numeric_type_code(type_code, dialect_name)
                        except (IndexError, AttributeError):
                            pass

                        fields_info.append({
                            "name": col_name,
                            "is_numeric": is_numeric
                        })

                    res = result.fetchall()
                    result_list = [
                        {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in
                        res
                    ]
                    return {"fields": columns, "data": result_list, "fields_info": fields_info,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
    else:
        conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
        extra_config_dict = get_extra_config(conf)
        if equals_ignore_case(ds.type, 'dm'):
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port, **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute(sql, timeout=conf.timeout)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    fields_info = build_fields_info_from_cursor(cursor, origin_column, 'dm')
                    result_list = [
                        {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in
                        res
                    ]
                    return {"fields": columns, "data": result_list, "fields_info": fields_info,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds.type, 'doris', 'starrocks'):
            ssl_args = {'ssl': {'ssl_mode': 'REQUIRE'}} if conf.ssl else {}
            with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                 port=conf.port, db=conf.database, connect_timeout=conf.timeout,
                                 read_timeout=conf.timeout, **extra_config_dict,
                                 **ssl_args) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    fields_info = build_fields_info_from_cursor(cursor, origin_column, 'mysql')
                    result_list = [
                        {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in
                        res
                    ]
                    return {"fields": columns, "data": result_list, "fields_info": fields_info,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds.type, 'redshift'):
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                            password=conf.password,
                                            timeout=conf.timeout, **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    fields_info = build_fields_info_from_cursor(cursor, origin_column, 'postgresql')
                    result_list = [
                        {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in
                        res
                    ]
                    return {"fields": columns, "data": result_list, "fields_info": fields_info,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds.type, 'kingbase'):
            with psycopg2.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                  password=conf.password,
                                  options=f"-c statement_timeout={conf.timeout * 1000}",
                                  **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    fields_info = build_fields_info_from_cursor(cursor, origin_column, 'postgresql')
                    result_list = [
                        {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in
                        res
                    ]
                    return {"fields": columns, "data": result_list, "fields_info": fields_info,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif equals_ignore_case(ds.type, 'es'):
            try:
                res, raw_columns = get_es_data_by_http(conf, sql)
                columns = [field.get('name') for field in raw_columns] if origin_column else [field.get('name').lower()
                                                                                              for
                                                                                              field in
                                                                                              raw_columns]
                fields_info = build_fields_info_from_es(raw_columns, origin_column)
                result_list = [
                    {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in
                    res
                ]
                return {"fields": columns, "data": result_list, "fields_info": fields_info,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
            except Exception as ex:
                raise Exception(str(ex))
        elif equals_ignore_case(ds.type, 'hive'):
            with hive.connect(host=conf.host, port=conf.port, username=conf.username,
                              database=conf.database, **extra_config_dict) as conn, conn.cursor() as cursor:
                try:
                    # Hive uses backticks for identifiers; normalize quoted identifiers as a compatibility fallback.
                    hive_sql = re.sub(r'"([A-Za-z_][A-Za-z0-9_]*)"', r'`\1`', sql)
                    cursor.execute(hive_sql)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    fields_info = build_fields_info_from_cursor(cursor, origin_column, 'hive')
                    result_list = [
                        {str(columns[i]): convert_value(value) for i, value in enumerate(tuple_item)} for tuple_item in
                        res
                    ]
                    return {"fields": columns, "data": result_list, "fields_info": fields_info,
                            "sql": bytes.decode(base64.b64encode(bytes(hive_sql, 'utf-8')))}
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
    """根据数据源类型获取 sqlglot dialect"""
    if equals_ignore_case(ds_type, 'mysql', 'doris', 'starrocks'):
        return 'mysql'
    elif equals_ignore_case(ds_type, 'sqlServer'):
        return 'tsql'
    elif equals_ignore_case(ds_type, 'hive'):
        return 'hive'
    return None


# 通用危险函数（适用于所有数据库）
COMMON_DANGEROUS_FUNCTIONS = {'version', 'current_user', 'user', 'database'}

# 特定数据库的危险函数
DS_SPECIFIC_DANGEROUS_FUNCTIONS = {
    'mysql': {'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE'},
    'doris': {'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE'},
    'starrocks': {'LOAD_FILE', 'INTO OUTFILE', 'INTO DUMPFILE'},
    'postgresql': {'pg_read_file', 'pg_write_file', 'lo_import', 'lo_export'},
    'sqlserver': {'EXEC', 'xp_cmdshell', 'sp_executesql'},
    'oracle': {'UTL_FILE', 'DBMS_PIPE', 'DBMS_LOCK'},
    'hive': {'ADD FILE', 'ADD JAR'},
}

# 危险模式正则表达式（用于检查特殊语法）
import re

DANGEROUS_PATTERNS = [
    r'\bINTO\s+OUTFILE\b',
    r'\bINTO\s+DUMPFILE\b',
    r'\bEXEC\s*\(',
    r'\bCOPY\s+.*\bTO\s+PROGRAM\b',
]


def get_dangerous_functions(ds_type: str) -> set:
    """获取危险函数（通用 + 特定数据源）"""
    functions = COMMON_DANGEROUS_FUNCTIONS.copy()
    ds_key = ds_type.lower() if ds_type else ''
    if ds_key in DS_SPECIFIC_DANGEROUS_FUNCTIONS:
        functions.update(DS_SPECIFIC_DANGEROUS_FUNCTIONS[ds_key])
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


def check_sql_read(sql: str, ds: CoreDatasource | AssistantOutDsSchema) -> tuple[bool, str]:
    """
    检查 SQL 是否为安全的只读查询
    返回: (是否安全, 错误原因)
    """
    try:
        normalized_sql = sql.strip().lstrip("(").strip()
        first_keyword = normalized_sql.split(None, 1)[0].upper() if normalized_sql else ""

        # 根据配置决定是否允许元数据查询
        if settings.SQLBOT_ALLOW_METADATA_QUERIES:
            allowed_read_commands = {"SELECT", "WITH", "SHOW", "DESCRIBE", "DESC", "EXPLAIN"}
        else:
            allowed_read_commands = {"SELECT", "WITH"}

        denied_write_commands = {
            "INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER",
            "TRUNCATE", "MERGE", "COPY", "REPLACE", "GRANT", "REVOKE",
            "USE", "SET", "CALL"
        }

        if not first_keyword:
            raise ValueError("Parse SQL Error")
        if first_keyword in denied_write_commands:
            return False, f"Write operation '{first_keyword}' is not allowed"

        # 1. 使用正则检查特殊模式
        for pattern in DANGEROUS_PATTERNS:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, f"SQL contains dangerous pattern: {pattern}"

        dialect = get_sqlglot_dialect(ds.type)
        statements = sqlglot.parse(sql, dialect=dialect)

        if not statements:
            raise ValueError("Parse SQL Error")

        # 2. 使用 sqlglot 检查函数调用
        dangerous_functions = get_dangerous_functions(ds.type)
        dangerous_functions_upper = {f.upper() for f in dangerous_functions}
        for stmt in statements:
            if stmt:
                for func in stmt.find_all(exp.Anonymous):
                    if func.name.upper() in dangerous_functions_upper:
                        return False, f"SQL contains dangerous function: {func.name}"

        # 3. 检查写操作类型
        write_types = (
            exp.Insert, exp.Update, exp.Delete,
            exp.Create, exp.Drop, exp.Alter,
            exp.Merge, exp.Copy
        )

        for stmt in statements:
            if stmt is None:
                continue
            if isinstance(stmt, write_types):
                return False, f"SQL contains write operation: {type(stmt).__name__}"

        if first_keyword not in allowed_read_commands:
            return False, f"SQL command '{first_keyword}' is not allowed. Only SELECT and WITH are permitted"

        return True, ""

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
        self._pools = OrderedDict()  # 使用有序字典实现 LRU
        self._lock = threading.Lock()  # 保证多线程安全

    def get_pool(self, ds: CoreDatasource | AssistantOutDsSchema, **db_config):
        """
        get connection pool（lazy load + LRU update）
        """
        with self._lock:
            if ds.id:
                # 1. 如果连接池已存在，将其移动到字典末尾（标记为最近使用）
                if ds.id in self._pools:
                    self._pools.move_to_end(ds.id)
                    print(f"[LRU] return: {ds.id}")
                    return self._pools[ds.id]

                # 2. 如果连接池不存在，检查是否达到上限，若达到则淘汰最久未使用的（字典头部）
                if len(self._pools) >= self.max_pools:
                    oldest_id, oldest_pool = self._pools.popitem(last=False)
                    oldest_pool.close()  # 安全关闭被驱逐的连接池
                    print(f"[LRU] remove oldest: {oldest_id}")

            # 3. 创建新连接池并放入字典末尾
            engine = get_engine(ds)
            new_pool = sessionmaker(bind=engine)
            self._pools[ds.id] = new_pool
            print(f"[LRU] create: {ds.id}")
            return new_pool

    def close_all(self):
        """stop"""
        with self._lock:
            for pool in self._pools.values():
                pool.close()
            self._pools.clear()


pool_manager = ConnectionPoolManager(max_pools=500)
