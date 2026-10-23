"""System-wide effective embedding strategy, captured once at each task boundary."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, fields
from typing import TYPE_CHECKING

from sqlmodel import Session, select

from common.core.config import settings

if TYPE_CHECKING:
    from sqlbot_xpack.config.model import SysArgModel


@dataclass(frozen=True)
class EmbeddingConfig:
    enabled: bool
    terminology_similarity: float
    terminology_top_count: int
    data_training_similarity: float
    data_training_top_count: int
    table_enabled: bool
    table_count: int
    table_alpha: float
    keyword_enabled: bool
    datasource_count: int


# Stable persisted keys use the embedding group; startup settings remain deployment defaults.
PARAMETER_SETTINGS = {
    "enabled": "EMBEDDING_ENABLED",
    "terminology_similarity": "EMBEDDING_TERMINOLOGY_SIMILARITY",
    "terminology_top_count": "EMBEDDING_TERMINOLOGY_TOP_COUNT",
    "data_training_similarity": "EMBEDDING_DATA_TRAINING_SIMILARITY",
    "data_training_top_count": "EMBEDDING_DATA_TRAINING_TOP_COUNT",
    "table_enabled": "TABLE_EMBEDDING_ENABLED",
    "table_count": "TABLE_EMBEDDING_COUNT",
    "table_alpha": "TABLE_EMBEDDING_ALPHA",
    "keyword_enabled": "TABLE_EMBEDDING_KEYWORD_ENABLED",
    "datasource_count": "DS_EMBEDDING_COUNT",
}
EDITABLE_FIELDS = (
    "enabled",
    "table_enabled",
    "terminology_similarity",
    "terminology_top_count",
    "data_training_similarity",
    "data_training_top_count",
    "table_count",
    "table_alpha",
    "keyword_enabled",
    "datasource_count",
)
BOOLEAN_FIELDS = {"enabled", "table_enabled", "keyword_enabled"}
INTEGER_FIELDS = {
    "terminology_top_count",
    "data_training_top_count",
    "table_count",
    "datasource_count",
}


def parse_parameter(field: str, value: object) -> bool | int | float:
    """Strict saved-value parsing. In particular, bool is never an integer count."""
    if field in BOOLEAN_FIELDS:
        if type(value) is bool:
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        raise ValueError(field)
    if type(value) is bool or value is None:
        raise ValueError(field)
    if field in INTEGER_FIELDS:
        if not isinstance(value, (str, int)) or not re.fullmatch(r"[0-9]+", str(value)):
            raise ValueError(field)
        number = int(value)
        if number <= 0:
            raise ValueError(field)
        return number
    if not isinstance(value, (str, int, float)):
        raise ValueError(field)
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(field)
    return number


def load_embedding_config(session: Session) -> EmbeddingConfig:
    """Read all overrides in one statement; never mutate or cache startup settings.

    A new Session per task sees commits from any API worker or MCP process. Invalid
    persisted overrides are rejected rather than silently replaced with defaults.
    Migrated installations may not have a unique pkey constraint. For historical
    duplicate keys, the row with the greatest id wins deterministically.
    """
    # Released xpack imports datasource consumers during package bootstrap.
    # Keep this model import lazy so cold worker imports cannot form a cycle.
    from sqlbot_xpack.config.model import SysArgModel

    rows = (
        session.execute(
            select(SysArgModel)
            .where(
                SysArgModel.pkey.in_(
                    [f"embedding.{name}" for name in PARAMETER_SETTINGS]
                )
            )
            .order_by(SysArgModel.id)
        )
        .scalars()
        .all()
    )
    overrides = {row.pkey.removeprefix("embedding."): row.pval for row in rows}
    values = {
        field.name: parse_parameter(field.name, overrides[field.name])
        if field.name in overrides
        else getattr(settings, PARAMETER_SETTINGS[field.name])
        for field in fields(EmbeddingConfig)
    }
    return EmbeddingConfig(**values)


def effective_parameter_args(session: Session) -> list[SysArgModel]:
    from sqlbot_xpack.config.model import SysArgModel

    config = load_embedding_config(session)
    return [
        SysArgModel(
            pkey=f"embedding.{name}",
            pval=str(getattr(config, name)).lower(),
            ptype="bool"
            if name in BOOLEAN_FIELDS
            else "int"
            if name in INTEGER_FIELDS
            else "float",
        )
        for name in EDITABLE_FIELDS
    ]
