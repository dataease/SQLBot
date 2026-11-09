"""Internal metadata representations; deliberately separate from management DTOs."""

from sqlalchemy import BigInteger, Column, Text
from sqlmodel import Field, SQLModel


class MetadataEmbedding(SQLModel, table=True):
    __tablename__ = "metadata_embedding"

    resource_type: str = Field(primary_key=True, max_length=32)
    resource_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    format_version: int
    model_id: str = Field(sa_column=Column(Text, nullable=False))
    input_hash: str = Field(max_length=64)
    chunk_count: int
    dimension: int
    vectors_hash: str = Field(max_length=64)
    vectors: str = Field(sa_column=Column(Text, nullable=False))
