# Author: Junjun
# Date: 2025/7/16

from enum import Enum

from common.utils.utils import equals_ignore_case


class ConnectType(Enum):
    sqlalchemy = ('sqlalchemy')
    py_driver = ('py_driver')

    def __init__(self, type_name):
        self.type_name = type_name


class DB(Enum):
    excel = ('excel', 'Excel/CSV', '"', '"', ConnectType.sqlalchemy, 'PostgreSQL')
    redshift = ('redshift', 'AWS Redshift', '"', '"', ConnectType.py_driver, 'AWS_Redshift')
    ck = ('ck', 'ClickHouse', '"', '"', ConnectType.sqlalchemy, 'ClickHouse')
    dm = ('dm', '达梦', '"', '"', ConnectType.py_driver, 'DM')
    doris = ('doris', 'Apache Doris', '`', '`', ConnectType.py_driver, 'Doris')
    es = ('es', 'Elasticsearch', '"', '"', ConnectType.py_driver, 'Elasticsearch')
    kingbase = ('kingbase', 'Kingbase', '"', '"', ConnectType.py_driver, 'Kingbase')
    sqlServer = ('sqlServer', 'Microsoft SQL Server', '[', ']', ConnectType.sqlalchemy, 'Microsoft_SQL_Server')
    mysql = ('mysql', 'MySQL', '`', '`', ConnectType.sqlalchemy, 'MySQL')
    oracle = ('oracle', 'Oracle', '"', '"', ConnectType.sqlalchemy, 'Oracle')
    pg = ('pg', 'PostgreSQL', '"', '"', ConnectType.sqlalchemy, 'PostgreSQL')
    starrocks = ('starrocks', 'StarRocks', '`', '`', ConnectType.py_driver, 'StarRocks')

    def __init__(self, type, db_name, prefix, suffix, connect_type: ConnectType, template_name: str):
        self.type = type
        self.db_name = db_name
        self.prefix = prefix
        self.suffix = suffix
        self.connect_type = connect_type
        self.template_name = template_name

    @classmethod
    def get_db(cls, type, default_if_none=False):
        for db in cls:
            """ if db.type == type: """
            if equals_ignore_case(db.type, type):
                return db
        if default_if_none:
            return DB.pg
        else:
            raise ValueError(f"Invalid db type: {type}")
