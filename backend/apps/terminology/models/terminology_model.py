from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, DateTime, Identity, Boolean, JSON
from sqlmodel import SQLModel, Field


class Terminology(SQLModel, table=True):
    __tablename__ = "terminology"
    id: Optional[int] = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    oid: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True, default=1))
    pid: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True))
    create_time: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    word: Optional[str] = Field(max_length=255)
    description: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    embedded: Optional[bool] = Field(sa_column=Column(Boolean, default=False))  # word字段是否已向量化到 Milvus
    specific_ds: Optional[bool] = Field(sa_column=Column(Boolean, default=False))
    datasource_ids: Optional[list[int]] = Field(sa_column=Column(JSON), default=[])
    enabled: Optional[bool] = Field(sa_column=Column(Boolean, default=True))


class TerminologyInfo(BaseModel):
    id: Optional[int] = None
    create_time: Optional[datetime] = None
    word: Optional[str] = None
    description: Optional[str] = None
    other_words: Optional[List[str]] = []
    specific_ds: Optional[bool] = False
    datasource_ids: Optional[list[int]] = []
    datasource_names: Optional[list[str]] = []
    enabled: Optional[bool] = True
