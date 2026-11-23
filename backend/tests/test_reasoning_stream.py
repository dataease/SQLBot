"""Exercise the production stream parser with synthetic model chunks."""

import ast
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest


@pytest.fixture(scope="module")
def process_stream():
    source = Path(__file__).resolve().parents[1] / "apps/chat/task/llm.py"
    functions = [
        node for node in ast.parse(source.read_text(encoding="utf-8")).body
        if isinstance(node, ast.FunctionDef) and node.name in {"process_stream", "get_token_usage"}
    ]
    namespace = {
        "Any": Any,
        "Dict": dict,
        "Iterator": Iterator,
        "BaseMessageChunk": SimpleNamespace,
        "SQLBotLogUtil": Mock(),
        "settings": SimpleNamespace(
            PARSE_REASONING_BLOCK_ENABLED=True,
            DEFAULT_REASONING_CONTENT_START="<think>",
            DEFAULT_REASONING_CONTENT_END="</think>",
        ),
    }
    exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["process_stream"]


@pytest.mark.parametrize(
    "parts",
    [
        ["<think>Plan ", "the query", "</think>Answer"],
        ["<th", "ink>Plan ", "the query</th", "ink>Answer"],
        ["<think>Plan the query</", "th", "i", "nk", ">Answer"],
        ["<think>Plan the query</think>Answer"],
    ],
)
def test_thinking_is_emitted_once_and_closing_tag_can_span_chunks(process_stream, parts):
    chunks = (SimpleNamespace(content=part, additional_kwargs={}, usage_metadata=None) for part in parts)
    events = list(process_stream(chunks))

    assert "".join(event["reasoning_content"] for event in events) == "Plan the query"
    assert "".join(event["content"] for event in events) == "Answer"


def test_partial_closing_tag_is_retained_if_it_is_reasoning_text(process_stream):
    chunks = (
        SimpleNamespace(content=part, additional_kwargs={}, usage_metadata=None)
        for part in ["<think>Use </th", " as a prefix.</think>Answer"]
    )
    events = list(process_stream(chunks))

    assert "".join(event["reasoning_content"] for event in events) == "Use </th as a prefix."
    assert "".join(event["content"] for event in events) == "Answer"


def test_reasoning_metadata_and_usage_are_preserved(process_stream):
    chunks = iter([
        SimpleNamespace(content="", additional_kwargs={"reasoning_content": "Plan"}, usage_metadata=None),
        SimpleNamespace(
            content="Answer", additional_kwargs={},
            usage_metadata={"input_tokens": 4, "output_tokens": 3, "total_tokens": 7},
        ),
    ])
    usage = {}

    assert list(process_stream(chunks, usage)) == [
        {"content": "", "reasoning_content": "Plan"},
        {"content": "Answer", "reasoning_content": ""},
    ]
    assert usage == {"input_tokens": 4, "output_tokens": 3, "total_tokens": 7}
