# Author: Junjun
# Date: 2025/8/20
from apps.datasource.models.datasource import CoreDatasource, DatasourceConf
from common.utils.utils import equals_ignore_case


def get_version_sql(ds: CoreDatasource, conf: DatasourceConf):
    if equals_ignore_case(ds.type, "mysql", "doris", "starrocks"):
        return """
                SELECT VERSION()
                """
    elif equals_ignore_case(ds.type, "sqlServer"):
        return """
                select SERVERPROPERTY('ProductVersion')
                """
    elif equals_ignore_case(ds.type, "pg", "kingbase", "excel"):
        return """
              SELECT current_setting('server_version')
              """
    elif equals_ignore_case(ds.type, "oracle"):
        return """
                SELECT version FROM v$instance
                """
    elif equals_ignore_case(ds.type, "ck"):
        return """
                select  version()
                """
    elif equals_ignore_case(ds.type, "dm"):
        return """
                SELECT * FROM v$version
                """
    elif equals_ignore_case(ds.type, "redshift"):
        return ''


def get_table_sql(ds: CoreDatasource, conf: DatasourceConf, db_version: str = ''):
    if equals_ignore_case(ds.type, "mysql"):
        return """
                SELECT 
                    TABLE_NAME, 
                    TABLE_COMMENT
                FROM 
                    information_schema.TABLES
                WHERE 
                    TABLE_SCHEMA = :param
                """, conf.database
    elif equals_ignore_case(ds.type, "sqlServer"):
        return """
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
                    AND t.TABLE_SCHEMA = :param
                """, conf.dbSchema
    elif equals_ignore_case(ds.type, "pg", "excel"):
        return """
              SELECT c.relname                                       AS TABLE_NAME,
                     COALESCE(COALESCE(d.description, obj_description(c.oid)), '') AS TABLE_COMMENT
              FROM pg_class c
                       LEFT JOIN
                   pg_namespace n ON n.oid = c.relnamespace
                       LEFT JOIN
                   pg_description d ON d.objoid = c.oid AND d.objsubid = 0
              WHERE n.nspname = :param
                AND c.relkind IN ('r', 'v', 'p', 'm')
                AND c.relname NOT LIKE 'pg_%'
                AND c.relname NOT LIKE 'sql_%'
              ORDER BY c.relname \
              """, conf.dbSchema
    elif equals_ignore_case(ds.type, "oracle"):
        return """
                SELECT DISTINCT
                    t.TABLE_NAME AS "TABLE_NAME",
                    NVL(c.COMMENTS, '') AS "TABLE_COMMENT"
                FROM (
                    SELECT TABLE_NAME, 'TABLE' AS OBJECT_TYPE
                    FROM ALL_TABLES
                    WHERE OWNER = :param  
                    UNION ALL
                    SELECT VIEW_NAME AS TABLE_NAME, 'VIEW' AS OBJECT_TYPE
                    FROM ALL_VIEWS
                    WHERE OWNER = :param  
                    UNION ALL
                    SELECT MVIEW_NAME AS TABLE_NAME, 'MATERIALIZED VIEW' AS OBJECT_TYPE
                    FROM ALL_MVIEWS
                    WHERE OWNER = :param  
                ) t
                LEFT JOIN ALL_TAB_COMMENTS c 
                    ON t.TABLE_NAME = c.TABLE_NAME 
                    AND c.TABLE_TYPE = t.OBJECT_TYPE
                    AND c.OWNER = :param   
                ORDER BY t.TABLE_NAME
                """, conf.dbSchema
    elif equals_ignore_case(ds.type, "ck"):
        version = int(db_version.split('.')[0])
        if version < 22:
            return """
                    SELECT name, '' as comment
                    FROM system.tables
                    WHERE database = :param
                      AND engine NOT IN ('Dictionary')
                    ORDER BY name
                    """, conf.database
        else:
            return """
                    SELECT name, comment
                    FROM system.tables
                    WHERE database = :param
                      AND engine NOT IN ('Dictionary')
                    ORDER BY name
                    """, conf.database
    elif equals_ignore_case(ds.type, "dm"):
        return """
                select table_name, comments 
                from all_tab_comments 
                where owner=:param
                AND (table_type = 'TABLE' or table_type = 'VIEW')
                """, conf.dbSchema
    elif equals_ignore_case(ds.type, "redshift"):
        return """
                SELECT  
                  relname AS TableName, 
                  obj_description(relfilenode::regclass, 'pg_class') AS TableDescription
                FROM 
                  pg_class 
                WHERE 
                  relkind in  ('r','p', 'f') 
                  AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = %s)
                """, conf.dbSchema
    elif equals_ignore_case(ds.type, "doris", "starrocks"):
        return """
                SELECT 
                    TABLE_NAME, 
                    TABLE_COMMENT
                FROM 
                    information_schema.TABLES
                WHERE 
                    TABLE_SCHEMA = %s
                """, conf.database
    elif equals_ignore_case(ds.type, "kingbase"):
        return """
              SELECT c.relname                                       AS TABLE_NAME,
                     COALESCE(COALESCE(d.description, obj_description(c.oid)), '') AS TABLE_COMMENT
              FROM pg_class c
                       LEFT JOIN
                   pg_namespace n ON n.oid = c.relnamespace
                       LEFT JOIN
                   pg_description d ON d.objoid = c.oid AND d.objsubid = 0
              WHERE n.nspname = '{0}'
                AND c.relkind IN ('r', 'v', 'p', 'm')
                AND c.relname NOT LIKE 'pg_%'
                AND c.relname NOT LIKE 'sql_%'
              ORDER BY c.relname \
              """, conf.dbSchema
    elif equals_ignore_case(ds.type, "es"):
        return "", None


def get_field_sql(ds: CoreDatasource, conf: DatasourceConf, table_name: str = None):
    if equals_ignore_case(ds.type, "mysql"):
        sql1 = """
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    COLUMN_COMMENT
                FROM 
                    INFORMATION_SCHEMA.COLUMNS
                WHERE 
                    TABLE_SCHEMA = :param1
                """
        sql2 = " AND TABLE_NAME = :param2" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.database, table_name
    elif equals_ignore_case(ds.type, "sqlServer"):
        sql1 = """
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
                    C.TABLE_SCHEMA = :param1
                """
        sql2 = " AND C.TABLE_NAME = :param2" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.dbSchema, table_name
    elif equals_ignore_case(ds.type, "pg", "excel"):
        sql1 = """
               SELECT a.attname                                       AS COLUMN_NAME,
                      pg_catalog.format_type(a.atttypid, a.atttypmod) AS DATA_TYPE,
                      col_description(c.oid, a.attnum)                AS COLUMN_COMMENT
               FROM pg_catalog.pg_attribute a
                        JOIN
                    pg_catalog.pg_class c ON a.attrelid = c.oid
                        JOIN
                    pg_catalog.pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = :param1
                 AND a.attnum > 0
                 AND NOT a.attisdropped \
               """
        sql2 = " AND c.relname = :param2" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.dbSchema, table_name
    elif equals_ignore_case(ds.type, "redshift"):
        sql1 = """
               SELECT a.attname                                       AS COLUMN_NAME,
                      pg_catalog.format_type(a.atttypid, a.atttypmod) AS DATA_TYPE,
                      col_description(c.oid, a.attnum)                AS COLUMN_COMMENT
               FROM pg_catalog.pg_attribute a
                        JOIN
                    pg_catalog.pg_class c ON a.attrelid = c.oid
                        JOIN
                    pg_catalog.pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname = %s
                 AND a.attnum > 0
                 AND NOT a.attisdropped \
               """
        sql2 = " AND c.relname = %s" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.dbSchema, table_name
    elif equals_ignore_case(ds.type, "oracle"):
        sql1 = """
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
                    ALL_TAB_COLUMNS col
                LEFT JOIN 
                    ALL_COL_COMMENTS com 
                    ON col.OWNER = com.OWNER 
                    AND col.TABLE_NAME = com.TABLE_NAME 
                    AND col.COLUMN_NAME = com.COLUMN_NAME
                WHERE 
                    col.OWNER = :param1
                """
        sql2 = " AND col.TABLE_NAME = :param2" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.dbSchema, table_name
    elif equals_ignore_case(ds.type, "ck"):
        sql1 = """
                SELECT 
                    name AS COLUMN_NAME,
                    type AS DATA_TYPE,
                    comment AS COLUMN_COMMENT
                FROM system.columns
                WHERE database = :param1
                """
        sql2 = " AND table = :param2" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.database, table_name
    elif equals_ignore_case(ds.type, "dm"):
        sql1 = """
                SELECT 
                    c.COLUMN_NAME    AS "COLUMN_NAME",
                    c.DATA_TYPE      AS "DATA_TYPE",
                    COALESCE(com.COMMENTS, '') AS "COMMENTS"
                FROM 
                    ALL_TAB_COLS c
                LEFT JOIN 
                    ALL_COL_COMMENTS com 
                    ON c.OWNER = com.OWNER 
                   AND c.TABLE_NAME = com.TABLE_NAME 
                   AND c.COLUMN_NAME = com.COLUMN_NAME
                WHERE 
                    c.OWNER = :param1
                """
        sql2 = " AND c.TABLE_NAME = :param2" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.dbSchema, table_name
    elif equals_ignore_case(ds.type, "doris", "starrocks"):
        sql1 = """
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    COLUMN_COMMENT
                FROM 
                    INFORMATION_SCHEMA.COLUMNS
                WHERE 
                    TABLE_SCHEMA = %s
                """
        sql2 = " AND TABLE_NAME = %s" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.database, table_name
    elif equals_ignore_case(ds.type, "kingbase"):
        sql1 = """
                       SELECT a.attname                                       AS COLUMN_NAME,
                              pg_catalog.format_type(a.atttypid, a.atttypmod) AS DATA_TYPE,
                              col_description(c.oid, a.attnum)                AS COLUMN_COMMENT
                       FROM pg_catalog.pg_attribute a
                                JOIN
                            pg_catalog.pg_class c ON a.attrelid = c.oid
                                JOIN
                            pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                       WHERE n.nspname = '{0}'
                         AND a.attnum > 0
                         AND NOT a.attisdropped \
                       """
        sql2 = " AND c.relname = '{1}'" if table_name is not None and table_name != "" else ""
        return sql1 + sql2, conf.dbSchema, table_name
    elif equals_ignore_case(ds.type, "es"):
        return "", None, None
