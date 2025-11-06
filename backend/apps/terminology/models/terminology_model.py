from datetime import datetime
from typing import List, Optional

from pgvector.sqlalchemy import VECTOR
from pydantic import BaseModel
from sqlalchemy import Column, Text, BigInteger, DateTime, Identity, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import SQLModel, Field


class Terminology(SQLModel, table=True):
    __tablename__ = "terminology"
    id: Optional[int] = Field(sa_column=Column(BigInteger, Identity(always=True), primary_key=True))
    oid: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True, default=1))
    pid: Optional[int] = Field(sa_column=Column(BigInteger, nullable=True))
    create_time: Optional[datetime] = Field(sa_column=Column(DateTime(timezone=False), nullable=True))
    word: Optional[str] = Field(max_length=255)
    description: Optional[str] = Field(sa_column=Column(Text, nullable=True))
    embedding: Optional[List[float]] = Field(sa_column=Column(VECTOR(), nullable=True))
    specific_ds: Optional[bool] = Field(sa_column=Column(Boolean, default=False))
    datasource_ids: Optional[list[int]] = Field(sa_column=Column(JSONB), default=[])
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
