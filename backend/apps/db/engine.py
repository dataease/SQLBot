import urllib.parse
from typing import List

from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker

from apps.datasource.models.datasource import DatasourceConf
from common.core.config import settings


def get_engine_config():
    return DatasourceConf(username=settings.MYSQL_USER, password=settings.MYSQL_PASSWORD,
                          host=settings.MYSQL_SERVER, port=settings.MYSQL_PORT, database=settings.MYSQL_DB,
                          timeout=30)


def get_engine_uri(conf: DatasourceConf):
    return f"mysql+pymysql://{urllib.parse.quote(conf.username)}:{urllib.parse.quote(conf.password)}@{conf.host}:{conf.port}/{urllib.parse.quote(conf.database)}?charset=utf8mb4"


def get_engine_conn():
    conf = get_engine_config()
    db_url = get_engine_uri(conf)
    engine = create_engine(db_url,
                           connect_args={"connect_timeout": conf.timeout},
                           pool_timeout=conf.timeout)
    return engine


def get_data_engine():
    engine = get_engine_conn()
    session_maker = sessionmaker(bind=engine)
    session = session_maker()
    return session


def create_table(session, table_name: str, fields: List[any]):
    # field type relation
    list = []
    for f in fields:
        if "object" in f["type"]:
            f["relType"] = "text"
        elif "int" in f["type"]:
            f["relType"] = "bigint"
        elif "float" in f["type"]:
            f["relType"] = "double"
        elif "datetime" in f["type"]:
            f["relType"] = "datetime"
        else:
            f["relType"] = "text"
        list.append(f'`{f["name"]}` {f["relType"]}')

    sql = f"""
            CREATE TABLE `{table_name}` (
                {", ".join(list)}
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
    session.execute(text(sql))
    session.commit()


def insert_data(session, table_name: str, fields: List[any], data: List[any]):
    engine = get_engine_conn()
    metadata = MetaData()
    table = Table(table_name, metadata, autoload_with=engine)
    with engine.connect() as conn:
        stmt = table.insert().values(data)
        conn.execute(stmt)
        conn.commit()
