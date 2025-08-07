import base64
import json
import urllib.parse
from decimal import Decimal
from typing import Any

from sqlalchemy import create_engine, text, Result, Engine
from sqlalchemy.orm import sessionmaker

from apps.datasource.models.datasource import DatasourceConf, CoreDatasource, TableSchema, ColumnSchema
from apps.datasource.utils.utils import aes_decrypt
from apps.db.engine import get_engine_config
from apps.system.crud.assistant import get_ds_engine
from apps.system.schemas.system_schema import AssistantOutDsSchema


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
    else:
        raise 'The datasource type not support.'
    return db_url


def get_engine(ds: CoreDatasource, timeout: int = 0) -> Engine:
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    if conf.timeout is None:
        conf.timeout = timeout
    if timeout > 0:
        conf.timeout = timeout
    if ds.type == "pg" and (conf.dbSchema is not None and conf.dbSchema != ""):
        engine = create_engine(get_uri(ds),
                               connect_args={"options": f"-c search_path={urllib.parse.quote(conf.dbSchema)}",
                                             "connect_timeout": conf.timeout},
                               pool_timeout=conf.timeout)
    elif ds.type == 'sqlServer':
        engine = create_engine(get_uri(ds), pool_timeout=conf.timeout)
    elif ds.type == 'oracle':
        engine = create_engine(get_uri(ds),
                               pool_timeout=conf.timeout)
    else:
        engine = create_engine(get_uri(ds), connect_args={"connect_timeout": conf.timeout}, pool_timeout=conf.timeout)
    return engine


def get_session(ds: CoreDatasource | AssistantOutDsSchema):
    engine = get_engine(ds) if isinstance(ds, CoreDatasource) else get_ds_engine(ds)
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    return session


def get_tables(ds: CoreDatasource):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    session = get_session(ds)
    result: Result[Any]
    sql: str = ''
    try:
        if ds.type == "mysql":
            sql = f"""
                    SELECT 
                        TABLE_NAME, 
                        TABLE_COMMENT
                    FROM 
                        information_schema.TABLES
                    WHERE 
                        TABLE_SCHEMA = '{conf.database}'
                    """
        elif ds.type == "sqlServer":
            sql = f"""
                    SELECT 
                        TABLE_NAME AS [TABLE_NAME],
                        ISNULL(ep.value, '') AS [TABLE_COMMENT]
                    FROM 
                        INFORMATION_SCHEMA.TABLES t
                    LEFT JOIN 
                        sys.extended_properties ep 
                        ON ep.major_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
                        AND ep.minor_id = 0 
                        AND ep.name = 'MS_Description' 
                    WHERE 
                        t.TABLE_TYPE IN ('BASE TABLE', 'VIEW')
                        AND t.TABLE_SCHEMA = '{conf.dbSchema}'
                    """
        elif ds.type == "pg" or ds.type == "excel":
            sql = """
                  SELECT c.relname                                       AS TABLE_NAME,
                         COALESCE(d.description, obj_description(c.oid)) AS TABLE_COMMENT
                  FROM pg_class c
                           LEFT JOIN
                       pg_namespace n ON n.oid = c.relnamespace
                           LEFT JOIN
                       pg_description d ON d.objoid = c.oid AND d.objsubid = 0
                  WHERE n.nspname = current_schema()
                    AND c.relkind IN ('r', 'v', 'p', 'm')
                    AND c.relname NOT LIKE 'pg_%'
                    AND c.relname NOT LIKE 'sql_%'
                  ORDER BY c.relname \
                  """
        elif ds.type == "oracle":
            sql = f"""
                    SELECT 
                        t.TABLE_NAME AS "TABLE_NAME",
                        NVL(c.COMMENTS, '') AS "TABLE_COMMENT"
                    FROM (
                        SELECT TABLE_NAME, 'TABLE' AS OBJECT_TYPE
                        FROM DBA_TABLES
                        WHERE OWNER = '{conf.dbSchema}'  
                        UNION ALL
                        SELECT VIEW_NAME AS TABLE_NAME, 'VIEW' AS OBJECT_TYPE
                        FROM DBA_VIEWS
                        WHERE OWNER = '{conf.dbSchema}'  
                    ) t
                    LEFT JOIN DBA_TAB_COMMENTS c 
                        ON t.TABLE_NAME = c.TABLE_NAME 
                        AND c.TABLE_TYPE = t.OBJECT_TYPE
                        AND c.OWNER = '{conf.dbSchema}'   
                    ORDER BY t.TABLE_NAME
                    """

        result = session.execute(text(sql))
        res = result.fetchall()
        res_list = [TableSchema(*item) for item in res]
        return res_list
    finally:
        if result is not None:
            result.close()
        if session is not None:
            session.close()


def get_fields(ds: CoreDatasource, table_name: str = None):
    conf = DatasourceConf(**json.loads(aes_decrypt(ds.configuration))) if ds.type != "excel" else get_engine_config()
    session = get_session(ds)
    result: Result[Any]
    sql: str = ''
    try:
        if ds.type == "mysql":
            sql1 = f"""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        COLUMN_COMMENT
                    FROM 
                        INFORMATION_SCHEMA.COLUMNS
                    WHERE 
                        TABLE_SCHEMA = '{conf.database}'
                    """
            sql2 = f" AND TABLE_NAME = '{table_name}'" if table_name is not None and table_name != "" else ""
            sql = sql1 + sql2
        elif ds.type == "sqlServer":
            sql1 = f"""
                    SELECT 
                        COLUMN_NAME AS [COLUMN_NAME],
                        DATA_TYPE AS [DATA_TYPE],
                        ISNULL(EP.value, '') AS [COLUMN_COMMENT]
                    FROM 
                        INFORMATION_SCHEMA.COLUMNS C
                    LEFT JOIN 
                        sys.extended_properties EP 
                        ON EP.major_id = OBJECT_ID(C.TABLE_SCHEMA + '.' + C.TABLE_NAME)
                        AND EP.minor_id = C.ORDINAL_POSITION
                        AND EP.name = 'MS_Description'
                    WHERE 
                        C.TABLE_SCHEMA = '{conf.dbSchema}'
                    """
            sql2 = f" AND C.TABLE_NAME = '{table_name}'" if table_name is not None and table_name != "" else ""
            sql = sql1 + sql2
        elif ds.type == "pg" or ds.type == "excel":
            sql1 = """
                   SELECT a.attname                                       AS COLUMN_NAME,
                          pg_catalog.format_type(a.atttypid, a.atttypmod) AS DATA_TYPE,
                          col_description(c.oid, a.attnum)                AS COLUMN_COMMENT
                   FROM pg_catalog.pg_attribute a
                            JOIN
                        pg_catalog.pg_class c ON a.attrelid = c.oid
                            JOIN
                        pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                   WHERE n.nspname = current_schema()
                     AND a.attnum > 0
                     AND NOT a.attisdropped \
                   """
            sql2 = f" AND c.relname = '{table_name}'" if table_name is not None and table_name != "" else ""
            sql = sql1 + sql2
        elif ds.type == "oracle":
            sql1 = f"""
                    SELECT 
                        col.COLUMN_NAME AS "COLUMN_NAME",
                        (CASE 
                            WHEN col.DATA_TYPE IN ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR') 
                                THEN col.DATA_TYPE || '(' || col.DATA_LENGTH || ')' 
                            WHEN col.DATA_TYPE = 'NUMBER' AND col.DATA_PRECISION IS NOT NULL 
                                THEN col.DATA_TYPE || '(' || col.DATA_PRECISION || 
                                     CASE WHEN col.DATA_SCALE > 0 THEN ',' || col.DATA_SCALE END || ')' 
                            ELSE col.DATA_TYPE 
                        END) AS "DATA_TYPE",
                        NVL(com.COMMENTS, '') AS "COLUMN_COMMENT"
                    FROM 
                        DBA_TAB_COLUMNS col
                    LEFT JOIN 
                        DBA_COL_COMMENTS com 
                        ON col.OWNER = com.OWNER 
                        AND col.TABLE_NAME = com.TABLE_NAME 
                        AND col.COLUMN_NAME = com.COLUMN_NAME
                    WHERE 
                        col.OWNER = '{conf.dbSchema}'
                    """
            sql2 = f" AND col.TABLE_NAME = '{table_name}'" if table_name is not None and table_name != "" else ""
            sql = sql1 + sql2

        result = session.execute(text(sql))
        res = result.fetchall()
        res_list = [ColumnSchema(*item) for item in res]
        return res_list
    finally:
        if result is not None:
            result.close()
        if session is not None:
            session.close()


def exec_sql(ds: CoreDatasource | AssistantOutDsSchema, sql: str):
    with get_session(ds) as session:
        with session.execute(text(sql)) as result:
            try:
                columns = [item.lower() for item in result.keys()._keys]
                res = result.fetchall()
                result_list = [
                    {str(columns[i]): float(value) if isinstance(value, Decimal) else value for i, value in
                     enumerate(tuple_item)}
                    for tuple_item in res
                ]
                return {"fields": columns, "data": result_list,
                        "sql": bytes.decode(base64.b64encode(bytes(sql, 'utf-8')))}
            except Exception as ex:
                raise ex
