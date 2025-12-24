from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, DateTime, Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class CoreDatasource(SQLModel, table=True):
    __tablename__ = "core_datasource"
    id: int = Field(sa_column=Column(BigInteger, Identity(always=True), nullable=False, primary_key=True))
    name: str = Field(max_length=128, nullable=False)
    description: str = Field(max_length=512, nullable=True)
    type: str = Field(max_length=64)
    type_name: str = Field(max_length=64, nullable=True)
    configuration: str = Field(sa_column=Column(Text))
    create_time: datetime = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    create_by: int = Field(sa_column=Column(BigInteger()))
    status: str = Field(max_length=64, nullable=True)
    num: str = Field(max_length=256, nullable=True)
    oid: int = Field(sa_column=Column(BigInteger()))
    table_relation: List = Field(sa_column=Column(JSONB, nullable=True))
    embedding: str = Field(sa_column=Column(Text, nullable=True))
    recommended_config: int = Field(sa_column=Column(BigInteger()))


class CoreTable(SQLModel, table=True):
    __tablename__ = "core_table"
    id: int = Field(sa_column=Column(BigInteger, Identity(always=True), nullable=False, primary_key=True))
    ds_id: int = Field(sa_column=Column(BigInteger()))
    checked: bool = Field(default=True)
    table_name: str = Field(sa_column=Column(Text))
    table_comment: str = Field(sa_column=Column(Text))
    custom_comment: str = Field(sa_column=Column(Text))
    embedding: str = Field(sa_column=Column(Text, nullable=True))


class DsRecommendedProblem(SQLModel, table=True):
    __tablename__ = "ds_recommended_problem"
    id: int = Field(sa_column=Column(BigInteger, Identity(always=True), nullable=False, primary_key=True))
    datasource_id: int = Field(sa_column=Column(BigInteger()))
    question: str = Field(sa_column=Column(Text))
    remark: str = Field(sa_column=Column(Text))
    sort: int = Field(sa_column=Column(BigInteger()))
    create_time: datetime = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    create_by: int = Field(sa_column=Column(BigInteger()))


class CoreField(SQLModel, table=True):
    __tablename__ = "core_field"
    id: int = Field(sa_column=Column(BigInteger, Identity(always=True), nullable=False, primary_key=True))
    ds_id: int = Field(sa_column=Column(BigInteger()))
    table_id: int = Field(sa_column=Column(BigInteger()))
    checked: bool = Field(default=True)
    field_name: str = Field(sa_column=Column(Text))
    field_type: str = Field(max_length=128, nullable=True)
    field_comment: str = Field(sa_column=Column(Text))
    custom_comment: str = Field(sa_column=Column(Text))
    field_index: int = Field(sa_column=Column(BigInteger()))


# datasource create obj
class CreateDatasource(BaseModel):
    id: int = None
    name: str = ''
    description: str = ''
    type: str = ''
    configuration: str = ''
    create_time: Optional[datetime] = None
    create_by: int = 0
    status: str = ''
    num: str = ''
    oid: int = 1
    tables: List[CoreTable] = []
    recommended_config: int = 1


class RecommendedProblemResponse:
    def __init__(self, datasource_id, recommended_config, questions):
        self.datasource_id = datasource_id
        self.recommended_config = recommended_config
        self.questions = questions

    datasource_id: int = None
    recommended_config: int = None
    questions: str = None


class RecommendedProblemBase(BaseModel):
    datasource_id: int = None
    recommended_config: int = None
    problemInfo: List[DsRecommendedProblem] = []


class RecommendedProblemBaseChat:
    def __init__(self, content):
        self.content = content

    content: List[str] = []


# edit local saved table and fields
class TableObj(BaseModel):
    table: CoreTable = None
    fields: List[CoreField] = []


# datasource config info
class DatasourceConf(BaseModel):
    host: str = ''
    port: int = 0
    username: str = ''
    password: str = ''
    database: str = ''
    driver: str = ''
    extraJdbc: str = ''
    dbSchema: str = ''
    filename: str = ''
    sheets: List = ''
    mode: str = ''
    timeout: int = 30

    def to_dict(self):
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
            "database": self.database,
            "driver": self.driver,
            "extraJdbc": self.extraJdbc,
            "dbSchema": self.dbSchema,
            "filename": self.filename,
            "sheets": self.sheets,
            "mode": self.mode,
            "timeout": self.timeout
        }


class TableSchema:
    def __init__(self, attr1, attr2):
        self.tableName = attr1
        self.tableComment = attr2 if attr2 is None or isinstance(attr2, str) else attr2.decode("utf-8")

    tableName: str
    tableComment: str


class TableSchemaResponse(BaseModel):
    tableName: str = ''
    tableComment: str | None = ''


class ColumnSchema:
    def __init__(self, attr1, attr2, attr3):
        self.fieldName = attr1
        self.fieldType = attr2
        self.fieldComment = attr3 if attr3 is None or isinstance(attr3, str) else attr3.decode("utf-8")

    fieldName: str
    fieldType: str
    fieldComment: str


class ColumnSchemaResponse(BaseModel):
    fieldName: str | None = ''
    fieldType: str | None = ''
    fieldComment: str | None = ''


class TableAndFields:
    def __init__(self, schema, table, fields):
        self.schema = schema
        self.table = table
        self.fields = fields

    schema: str
    table: CoreTable
    fields: List[CoreField]


class FieldObj(BaseModel):
    fieldName: str | None


class PreviewResponse(BaseModel):
    fields: List | None = []
    data: List | None = []
    sql: str | None = ''
