"""Real tokenizer boundary; embedding inference stays offline and observable."""

from types import SimpleNamespace

import pytest
from tokenizers import Tokenizer, models, pre_tokenizers, processors
from transformers import PreTrainedTokenizerFast

from apps.ai_model.query_embedding import QueryEmbeddingUnavailable, embed_query


def embedding_model(*, limit=5, calls=None):
    tokenizer = Tokenizer(
        models.WordLevel(
            {"[UNK]": 0, "[CLS]": 1, "[SEP]": 2, "a": 3}, unk_token="[UNK]"
        )
    )
    tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
    tokenizer.post_processor = processors.TemplateProcessing(
        single="[CLS] $A [SEP]", special_tokens=[("[CLS]", 1), ("[SEP]", 2)]
    )
    fast = PreTrainedTokenizerFast(tokenizer_object=tokenizer, unk_token="[UNK]")
    transformer = SimpleNamespace(
        tokenizer=fast, max_seq_length=limit, do_lower_case=True
    )
    recorded = calls if calls is not None else []

    def encode(value):
        recorded.append(value)
        return [1.0, 0.0]

    return SimpleNamespace(
        _client=SimpleNamespace(_first_module=lambda: transformer), embed_query=encode
    )


@pytest.mark.parametrize("query", ["a a", " A\na a "])
def test_query_at_or_below_real_tokenizer_limit_reaches_model(query):
    calls = []
    model = embedding_model(calls=calls)
    assert embed_query(model, query, stage="sql_example") == [1.0, 0.0]
    assert calls == [query]
    assert model._client._first_module().tokenizer._tokenizer.truncation is None


def test_over_limit_query_never_reaches_truncating_model():
    calls = []
    with pytest.raises(QueryEmbeddingUnavailable) as error:
        embed_query(embedding_model(calls=calls), "a a a a", stage="sql_example")
    assert error.value.reason == "query_too_long"
    assert error.value.token_count == 6
    assert error.value.limit == 5
    assert calls == []


def test_query_prompt_special_tokens_and_preprocessing_share_the_actual_budget():
    calls = []
    model = embedding_model(calls=calls)
    model.query_encode_kwargs = {"prompt": "a a "}
    with pytest.raises(QueryEmbeddingUnavailable, match="query_too_long"):
        embed_query(model, "A\na", stage="sql_example")
    assert calls == []
