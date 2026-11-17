"""Guard final query vectors against silent truncation by the deployed model."""

import copy
import json
import time
from typing import Any

from common.utils.utils import SQLBotLogUtil


class QueryEmbeddingUnavailable(ValueError):
    def __init__(
        self, reason: str, token_count: int | None = None, limit: int | None = None
    ):
        super().__init__(reason)
        self.reason = reason
        self.token_count = token_count
        self.limit = limit


def embed_query(model: Any, text: str, *, stage: str) -> list[float]:
    """Encode once only if the exact tokenizer input fits, including special tokens.

    Mirrors the deployed HuggingFaceEmbeddings/SentenceTransformer preprocessing.
    Counting uses a clone: fast tokenizers mutate truncation settings during calls.
    Failure to inspect the tokenizer is a safe retrieval fallback, not permission to
    let the model silently truncate. Callers retain their original legal candidates.
    """
    started = time.monotonic()
    count = limit = None
    reason = "encoded"
    model_calls = 0
    try:
        try:
            transformer = model._client._first_module()
            limit = transformer.max_seq_length
            if not isinstance(limit, int) or limit <= 0:
                raise ValueError("Invalid tokenizer limit")
            tokenizer = copy.deepcopy(transformer.tokenizer)
            options = getattr(model, "query_encode_kwargs", None) or getattr(
                model, "encode_kwargs", {}
            )
            # Query-specific encoding options take precedence in the wrapper.
            prompt = options.get("prompt")
            if prompt is None:
                prompt_name = options.get("prompt_name")
                if prompt_name is not None:
                    prompt = model._client.prompts[prompt_name]
                else:
                    prompt = getattr(model._client, "prompts", {}).get(
                        getattr(model._client, "default_prompt_name", None), ""
                    )
            value = ((prompt or "") + text.replace("\n", " ")).strip()
            if transformer.do_lower_case:
                value = value.lower()
            count = len(
                tokenizer(
                    value, truncation=False, add_special_tokens=True, verbose=False
                )["input_ids"]
            )
        except Exception as exc:
            raise QueryEmbeddingUnavailable("tokenizer_unavailable") from exc
        if count > limit:
            raise QueryEmbeddingUnavailable("query_too_long", count, limit)
        model_calls = 1
        try:
            return model.embed_query(text)
        except Exception as exc:
            raise QueryEmbeddingUnavailable("model_error", count, limit) from exc
    except QueryEmbeddingUnavailable as exc:
        reason = exc.reason
        raise
    finally:
        SQLBotLogUtil.info(
            "[retrieval] "
            + json.dumps(
                {
                    "stage": stage,
                    "query": text,
                    "reason": reason,
                    "token_count": count,
                    "token_limit": limit,
                    "model_calls": model_calls,
                    "elapsed_ms": (time.monotonic() - started) * 1000,
                },
                ensure_ascii=False,
            )
        )
