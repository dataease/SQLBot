"""Execute model validation with real DTOs and no provider/database connections."""

import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional
from unittest.mock import Mock

import pytest
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

BACKEND_DIR = Path(__file__).resolve().parents[1]


def load_symbol(path, name, namespace):
    source = BACKEND_DIR / path
    tree = ast.parse(source.read_text(encoding="utf-8"))
    node = next(node for node in tree.body if getattr(node, "name", None) == name)
    # Keep production handler logic while isolating unrelated auth/DB imports.
    if isinstance(node, ast.AsyncFunctionDef):
        node.decorator_list = []
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    return namespace[name]


@pytest.fixture
def validation():
    namespace = {
        "BaseModel": BaseModel,
        "Field": Field,
        "List": list,
        "Dict": dict,
        "Any": Any,
        "Optional": Optional,
        "PLACEHOLDER_PREFIX": "PLACEHOLDER_",
        "json": json,
        "Trans": object,
        "StreamingResponse": StreamingResponse,
        "SQLBotLogUtil": Mock(),
    }
    schema = "apps/system/schemas/ai_model_schema.py"
    for name in ("AiModelItem", "AiModelConfigItem", "AiModelCreator"):
        load_symbol(schema, name, namespace)
    load_symbol("common/utils/utils.py", "prepare_model_arg", namespace)
    load_symbol("apps/ai_model/model_factory.py", "LLMConfig", namespace)

    async def stream(_question):
        yield "ok"

    factory = Mock()
    factory.create_llm.return_value = SimpleNamespace(
        llm=SimpleNamespace(astream=stream)
    )
    namespace["LLMFactory"] = factory
    handler = load_symbol("apps/system/api/aimodel.py", "check_llm", namespace)

    def run(rows):
        info = namespace["AiModelCreator"](
            name="test",
            model_type=0,
            base_model="test",
            supplier=15,
            protocol=1,
            api_domain="https://example.test/v1",
            api_key="test-key",
            config_list=rows,
        )

        async def consume():
            response = await handler(info, lambda key, **_kwargs: key)
            assert isinstance(response, StreamingResponse)
            return [json.loads(chunk) async for chunk in response.body_iterator]

        assert asyncio.run(consume()) == [{"content": "ok"}]
        factory.create_llm.assert_called_once()
        return factory.create_llm.call_args.args[0].additional_params

    return run


@pytest.mark.parametrize("value", [0, 0.0, False])
def test_validation_preserves_zero_and_false(validation, value):
    result = validation(
        [
            {"key": "sample", "val": value, "name": "sample"},
            {"key": "max_tokens", "val": 1024, "name": "tokens"},
        ]
    )
    assert result == {"sample": value, "max_tokens": 1024}
    assert type(result["sample"]) is type(value)


@pytest.mark.parametrize("value", [1, 0.5, True, "0", "false", "text", [], {}])
def test_validation_preserves_other_supplied_values(validation, value):
    result = validation([{"key": "sample", "val": value, "name": "sample"}])
    assert result == {"sample": value}
    assert type(result["sample"]) is type(value)


@pytest.mark.parametrize("value", [None, ""])
def test_validation_still_skips_absent_values(validation, value):
    assert validation([{"key": "sample", "val": value, "name": "sample"}]) == {}


def test_validation_still_skips_empty_keys(validation):
    assert validation([{"key": "", "val": 1, "name": "sample"}]) == {}


@pytest.mark.parametrize(
    "value, expected",
    [
        ('{"enable_thinking": false}', {"enable_thinking": False}),
        ('["stop"]', ["stop"]),
        ('{"invalid"', '{"invalid"'),
    ],
)
def test_validation_keeps_json_conversion(validation, value, expected):
    assert validation([{"key": "sample", "val": value, "name": "sample"}]) == {
        "sample": expected,
    }


def test_validation_mixed_configuration(validation):
    assert validation(
        [
            {"key": "temperature", "val": 0, "name": "temperature"},
            {"key": "stream_usage", "val": False, "name": "stream_usage"},
            {"key": "max_tokens", "val": 1024, "name": "tokens"},
            {"key": "extra_body", "val": '{"enable_thinking": false}', "name": "extra"},
            {"key": "omitted", "val": None, "name": "omitted"},
        ]
    ) == {
        "temperature": 0,
        "stream_usage": False,
        "max_tokens": 1024,
        "extra_body": {"enable_thinking": False},
    }
