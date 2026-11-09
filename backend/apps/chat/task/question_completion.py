"""Per-task retrieval intent, separate from the original SQL-generation question."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class QuestionCompletion:
    original: str
    text: str
    reason: str
    token_usage: dict[str, Any]
    elapsed_ms: float
    model_calls: int = 1
