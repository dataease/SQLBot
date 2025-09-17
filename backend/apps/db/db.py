import base64
import json
import platform
import urllib.parse
from decimal import Decimal
from typing import Optional

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
from apps.system.crud.assistant import get_ds_engine
from apps.system.schemas.system_schema import AssistantOutDsSchema
from common.core.deps import Trans
from common.utils.utils import SQLBotLogUtil
from fastapi import HTTPException
from apps.db.es_engine import get_es_connect, get_es_index, get_es_fields, get_es_data_by_http


def get_uri(ds: CoreDatasource) -> str:
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    return get_uri_from_config(ds.type, conf)


def get_uri_from_config(type: str, conf: DatasourceConf) -> str:
    db_url: str
    if type == "mysql":
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"mysql+pymysql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"mysql+pymysql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif type == "sqlServer":
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"mssql+pymssql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"mssql+pymssql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif type == "pg" or type == "excel":
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"postgresql+psycopg2://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"postgresql+psycopg2://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif type == "oracle":
        if conf.mode == "service_name":
            if conf.extraJdbc is not None and conf.extraJdbc != '':
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}?service_name={conf.database}&{conf.extraJdbc}"
            else:
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}?service_name={conf.database}"
        else:
            if conf.extraJdbc is not None and conf.extraJdbc != '':
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
            else:
                db_url = f"oracle+oracledb://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    elif type == "ck":
        if conf.extraJdbc is not None and conf.extraJdbc != '':
            db_url = f"clickhouse+http://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}?{conf.extraJdbc}"
        else:
            db_url = f"clickhouse+http://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{conf.database}"
    else:
        raise 'The datasource type not support.'
    return db_url


def get_engine(ds: CoreDatasource, timeout: int = 0) -> Engine:
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    if conf.timeout is None:
        conf.timeout = timeout
    if timeout > 0:
        conf.timeout = timeout
    if ds.type == "pg":
        if conf.dbSchema is not None and conf.dbSchema != "":
            engine = create_engine(get_uri(ds),
                                   connect_args={"options": f"-c search_path={urllib.parse.quote(conf.dbSchema)}",
                                                 "connect_timeout": conf.timeout},
                                   pool_timeout=conf.timeout)
        else:
            engine = create_engine(get_uri(ds),
                                   connect_args={"connect_timeout": conf.timeout},
                                   pool_timeout=conf.timeout)
    elif ds.type == 'sqlServer':
        engine = create_engine(get_uri(ds), pool_timeout=conf.timeout)
    elif ds.type == 'oracle':
        engine = create_engine(get_uri(ds),
                               pool_timeout=conf.timeout)
    else:  # mysql, ck
        engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout}, pool_timeout=conf.timeout)
    return engine


def get_session(ds: CoreDatasource | AssistantOutDsSchema):
    engine = get_engine(ds) if isinstance(ds, CoreDatasource) else get_ds_engine(ds)
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    return session


def check_connection(trans: Optional[Trans], ds: CoreDatasource | AssistantOutDsSchema, is_raise: bool = False):
    if isinstance(ds, CoreDatasource):
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
            if ds.type == 'dm':
                with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                      port=conf.port) as conn, conn.cursor() as cursor:
                    try:
                        cursor.execute('select 1', timeout=10).fetchall()
                        SQLBotLogUtil.info("success")
                        return True
                    except Exception as e:
                        SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                        if is_raise:
                            raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                        return False
            elif ds.type == 'doris':
                with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                     port=conf.port, db=conf.database, connect_timeout=10,
                                     read_timeout=10) as conn, conn.cursor() as cursor:
                    try:
                        cursor.execute('select 1')
                        SQLBotLogUtil.info("success")
                        return True
                    except Exception as e:
                        SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                        if is_raise:
                            raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                        return False
            elif ds.type == 'redshift':
                with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database,
                                                user=conf.username,
                                                password=conf.password,
                                                timeout=10) as conn, conn.cursor() as cursor:
                    try:
                        cursor.execute('select 1')
                        SQLBotLogUtil.info("success")
                        return True
                    except Exception as e:
                        SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
                        if is_raise:
                            raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
                        return False
            elif ds.type == 'es':
                es_conn = get_es_connect(conf)
                if es_conn.ping():
                    SQLBotLogUtil.info("success")
                    return True
                else:
                    SQLBotLogUtil.info("failed")
                    return False
    else:
        conn = get_ds_engine(ds)
        try:
            with conn.connect() as connection:
                SQLBotLogUtil.info("success")
                return True
        except Exception as e:
            SQLBotLogUtil.error(f"Datasource {ds.id} connection failed: {e}")
            if is_raise:
                raise HTTPException(status_code=500, detail=trans('i18n_ds_invalid') + f': {e.args}')
            return False

    return False


def get_version(ds: CoreDatasource | AssistantOutDsSchema):
    version = ''
    conf = None
    if isinstance(ds, CoreDatasource):
        conf = DatasourceConf(
            **json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    if isinstance(ds, AssistantOutDsSchema):
        conf = DatasourceConf()
        conf.host = ds.host
        conf.port = ds.port
        conf.username = ds.user
        conf.password = ds.password
        conf.database = ds.dataBase
        conf.dbSchema = ds.db_schema
        conf.timeout = 10
    db = DB.get_db(ds.type)
    sql = get_version_sql(ds, conf)
    try:
        if db.connect_type == ConnectType.sqlalchemy:
            with get_session(ds) as session:
                with session.execute(text(sql)) as result:
                    res = result.fetchall()
                    version = res[0][0]
        else:
            if ds.type == 'dm':
                with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                      port=conf.port) as conn, conn.cursor() as cursor:
                    cursor.execute(sql, timeout=10)
                    res = cursor.fetchall()
                    version = res[0][0]
            elif ds.type == 'doris':
                with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                     port=conf.port, db=conf.database, connect_timeout=10,
                                     read_timeout=10) as conn, conn.cursor() as cursor:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    version = res[0][0]
            elif ds.type == 'redshift' or ds.type == 'es':
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
            if ds.type == "sqlServer":
                sql = f"""select name from sys.schemas"""
            elif ds.type == "pg" or ds.type == "excel":
                sql = """SELECT nspname
                         FROM pg_namespace"""
            elif ds.type == "oracle":
                sql = f"""select * from all_users"""
            with session.execute(text(sql)) as result:
                res = result.fetchall()
                res_list = [item[0] for item in res]
                return res_list
    else:
        if ds.type == 'dm':
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port) as conn, conn.cursor() as cursor:
                cursor.execute(f"""select OBJECT_NAME from dba_objects where object_type='SCH'""", timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list
    def get_table_info(self, table_name: str) -> str:
        """
        Get table info for a given table name.
        """
        cursor = self.conn.cursor()
        # Whitelist the table name by checking if it exists in the schema.
        # This prevents SQL injection as PRAGMA statements do not support placeholders for table names.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone() is None:
            # Table not found. Return an empty string.
            return ""

        # The table name is now validated against the schema. It is safe to use it.
        # We must escape single quotes to prevent SQL injection if the table name contains them.
        safe_table_name = table_name.replace("'", "''")
        return self._run(f"PRAGMA table_info('{safe_table_name}')")
                res = cursor.fetchall()
                res_list = [item[0] for item in res]
                return res_list


def get_tables(ds: CoreDatasource):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    db = DB.get_db(ds.type)
    sql = get_table_sql(ds, conf, get_version(ds))
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql)) as result:
                res = result.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
    else:
        if ds.type == 'dm':
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port) as conn, conn.cursor() as cursor:
                cursor.execute(sql, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif ds.type == 'doris':
            with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                 port=conf.port, db=conf.database, connect_timeout=conf.timeout,
                                 read_timeout=conf.timeout) as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif ds.type == 'redshift':
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                            password=conf.password,
                                            timeout=conf.timeout) as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [TableSchema(*item) for item in res]
                return res_list
        elif ds.type == 'es':
            res = get_es_index(conf)
            res_list = [TableSchema(*item) for item in res]
            return res_list


def get_fields(ds: CoreDatasource, table_name: str = None):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    db = DB.get_db(ds.type)
    sql = get_field_sql(ds, conf, table_name)
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql)) as result:
                res = result.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
    else:
        if ds.type == 'dm':
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port) as conn, conn.cursor() as cursor:
                cursor.execute(sql, timeout=conf.timeout)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif ds.type == 'doris':
            with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                 port=conf.port, db=conf.database, connect_timeout=conf.timeout,
                                 read_timeout=conf.timeout) as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif ds.type == 'redshift':
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                            password=conf.password,
                                            timeout=conf.timeout) as conn, conn.cursor() as cursor:
                cursor.execute(sql)
                res = cursor.fetchall()
                res_list = [ColumnSchema(*item) for item in res]
                return res_list
        elif ds.type == 'es':
            res = get_es_fields(conf, table_name)
            res_list = [ColumnSchema(*item) for item in res]
            return res_list


def exec_sql(ds: CoreDatasource | AssistantOutDsSchema, sql: str, origin_column=False):
    while sql.endswith(';'):
        sql = sql[:-1]

    db = DB.get_db(ds.type)
    if db.connect_type == ConnectType.sqlalchemy:
        with get_session(ds) as session:
            with session.execute(text(sql)) as result:
                try:
                    columns = result.keys()._keys if origin_column else [item.lower() for item in result.keys()._keys]
                    res = result.fetchall()
                    result_list = [
                        {str(columns[i]): float(value) if isinstance(value, Decimal) else value for i, value in
                         enumerate(tuple_item)}
                        for tuple_item in res
                    ]
                    return {"fields": columns, "data": result_list,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
    else:
        conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration)))
        if ds.type == 'dm':
            with dmPython.connect(user=conf.username, password=conf.password, server=conf.host,
                                  port=conf.port) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute(sql, timeout=conf.timeout)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    result_list = [
                        {str(columns[i]): float(value) if isinstance(value, Decimal) else value for i, value in
                         enumerate(tuple_item)}
                        for tuple_item in res
                    ]
                    return {"fields": columns, "data": result_list,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif ds.type == 'doris':
            with pymysql.connect(user=conf.username, passwd=conf.password, host=conf.host,
                                 port=conf.port, db=conf.database, connect_timeout=conf.timeout,
                                 read_timeout=conf.timeout) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    result_list = [
                        {str(columns[i]): float(value) if isinstance(value, Decimal) else value for i, value in
                         enumerate(tuple_item)}
                        for tuple_item in res
                    ]
                    return {"fields": columns, "data": result_list,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif ds.type == 'redshift':
            with redshift_connector.connect(host=conf.host, port=conf.port, database=conf.database, user=conf.username,
                                            password=conf.password,
                                            timeout=conf.timeout) as conn, conn.cursor() as cursor:
                try:
                    cursor.execute(sql)
                    res = cursor.fetchall()
                    columns = [field[0] for field in cursor.description] if origin_column else [field[0].lower() for
                                                                                                field in
                                                                                                cursor.description]
                    result_list = [
                        {str(columns[i]): float(value) if isinstance(value, Decimal) else value for i, value in
                         enumerate(tuple_item)}
                        for tuple_item in res
                    ]
                    return {"fields": columns, "data": result_list,
                            "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
                except Exception as ex:
                    raise ParseSQLResultError(str(ex))
        elif ds.type == 'es':
            try:
                res, columns = get_es_data_by_http(conf, sql)
                columns = [field.get('name') for field in columns] if origin_column else [field.get('name').lower() for
                                                                                          field in
                                                                                          columns]
                result_list = [
                    {str(columns[i]): float(value) if isinstance(value, Decimal) else value for i, value in
                     enumerate(tuple(tuple_item))}
                    for tuple_item in res
                ]
                return {"fields": columns, "data": result_list,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
            except Exception as ex:
                raise Exception(str(ex))

    def get_tables(self) -> list:
        """
        Get list of all tables in the database
        """
        if self.db_type == "mysql":
            sql = "SHOW TABLES"
        else:
            sql = "SELECT name FROM sqlite_master WHERE type='table'"
        
        try:
            result = self.run(sql)
            if result:
                return [row[0] for row in result]
            return []
        except Exception as e:
            logger.error(f"get_tables error: {e}")
            return []

    def _validate_table_name(self, table_name: str) -> bool:
        """
        Validate table name against existing tables and basic security checks
        """
        # Basic security check - only allow alphanumeric, underscore, and hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', table_name):
            return False
        
        # Check if table exists
        existing_tables = self.get_tables()
        return table_name in existing_tables

    def get_table_info(self, table_name: str) -> str:
        """
        Get table information
        """
        # Validate table name for security
        if not self._validate_table_name(table_name):
            logger.error(f"Invalid or non-existent table name: {table_name}")
            return ""

        if self.db_type == "mysql":
            # For MySQL, use backticks to quote the identifier safely
            # Since we've validated the table name, this is safe
            sql = f"SHOW CREATE TABLE `{table_name}`"
            params = None
        else:
            # For SQLite, use parameterized query
            sql = "SELECT sql FROM sqlite_master WHERE type='table' AND name=?"
            params = (table_name,)

        try:
            result = self.run(sql, params=params)
            if result and len(result) > 0:
                return result[0][0] if result[0][0] else ""
            return ""
        except Exception as e:
            logger.error(f"get_table_info error: {e}")
            return ""

    def get_fields(self, table_name: str) -> list:
        """
        Get table fields
        """
        # Validate table name for security
        if not self._validate_table_name(table_name):
            logger.error(f"Invalid or non-existent table name: {table_name}")
            return []

        if self.db_type == "mysql":
            # For MySQL, use backticks to quote the identifier safely
            sql = f"DESC `{table_name}`"
            params = None
        else:
            # For SQLite, PRAGMA doesn't support parameterization
            # But we've validated the table name, so this is safe
            sql = f"PRAGMA table_info('{table_name}')"
            params = None

        try:
            result = self.run(sql, params=params)
            if not result:
                return []
                
            if self.db_type == "mysql":
                return [
                    {"field": item[0], "type": item[1]}
                    for item in result
                ]
            else:
                return [
                    {"field": item[1], "type": item[2]}
                    for item in result
                ]
        except Exception as e:
            logger.error(f"get_fields error: {e}")
            return []
