# Author: Junjun
# Date: 2025/7/16

from enum import Enum


class ConnectType(Enum):
    sqlalchemy = ('sqlalchemy')
    py_driver = ('py_driver')

    def __init__(self, type_name):
        self.type_name = type_name


class DB(Enum):
    mysql = ('mysql', 'MySQL', '`', '`', ConnectType.sqlalchemy)
    sqlServer = ('sqlServer', 'Microsoft SQL Server', '[', ']', ConnectType.sqlalchemy)
    pg = ('pg', 'PostgreSQL', '"', '"', ConnectType.sqlalchemy)
    excel = ('excel', 'Excel/CSV', '"', '"', ConnectType.sqlalchemy)
    oracle = ('oracle', 'Oracle', '"', '"', ConnectType.sqlalchemy)
    ck = ('ck', 'ClickHouse', '"', '"', ConnectType.sqlalchemy)
    dm = ('dm', '达梦', '"', '"', ConnectType.py_driver)
    doris = ('doris', 'Apache Doris', '`', '`', ConnectType.py_driver)
    redshift = ('redshift', 'AWS Redshift', '"', '"', ConnectType.py_driver)
    es = ('es', 'Elasticsearch', '"', '"', ConnectType.py_driver)
    kingbase = ('kingbase', 'Kingbase', '"', '"', ConnectType.py_driver)
    starrocks = ('starrocks', 'StarRocks', '"', '"', ConnectType.py_driver)

    def __init__(self, type, db_name, prefix, suffix, connect_type: ConnectType):
        self.type = type
        self.db_name = db_name
        self.prefix = prefix
        self.suffix = suffix
        self.connect_type = connect_type

    @classmethod
    def get_db(cls, type):
        for db in cls:
            if db.type == type:
                return db
        raise ValueError(f"Invalid db type: {type}")
