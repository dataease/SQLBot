"""Exercise the actual UI schema and save handler with an isolated session.

Empty welcome strings must overwrite old custom text; omitted fields must not.
This does not exercise FastAPI authentication, file uploads or a real database.
"""

import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]


def load_node(path, name, namespace):
    node = next(
        n for n in ast.parse(path.read_text()).body if getattr(n, "name", None) == name
    )
    if isinstance(node, ast.AsyncFunctionDef):
        node.decorator_list = []
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace
    )


@pytest.mark.parametrize(
    "fields,expected",
    [
        ({"welcome": "", "welcome_desc": ""}, {"welcome": "", "welcome_desc": ""}),
        (
            {"welcome": "New custom title"},
            {"welcome": "New custom title", "welcome_desc": "Custom description"},
        ),
        (
            {"theme": "#123456"},
            {"welcome": "Custom title", "welcome_desc": "Custom description"},
        ),
    ],
)
def test_save_welcome_defaults(fields, expected):
    model = SimpleNamespace(
        id=42,
        configuration=json.dumps(
            {
                "welcome": "Custom title",
                "welcome_desc": "Custom description",
                "auto_ds": True,
            }
        ),
    )
    namespace = {
        "BaseModel": BaseModel,
        "Field": Field,
        "Optional": Optional,
        "List": list,
        "json": json,
        "SessionDep": object,
        "CurrentUser": object,
        "Trans": object,
        "UploadFile": object,
        "Form": lambda: None,
        "get_ws_assistant": Mock(return_value=model),
        "clear_ui_cache": AsyncMock(),
    }
    load_node(ROOT / "common/core/schemas.py", "BaseCreatorDTO", namespace)
    load_node(
        ROOT / "apps/system/schemas/system_schema.py", "AssistantUiSchema", namespace
    )
    load_node(ROOT / "apps/system/api/assistant.py", "ui", namespace)
    session, user, trans = Mock(), object(), object()
    result = asyncio.run(
        namespace["ui"](
            session, user, trans, json.dumps({"id": 42, **fields}), files=[]
        )
    )
    stored = json.loads(result.configuration)
    assert {key: stored[key] for key in expected} == expected
    assert stored["auto_ds"] is True
    if "theme" in fields:
        assert stored["theme"] == fields["theme"]
    namespace["get_ws_assistant"].assert_called_once_with(session, 42, user, trans)
    session.add.assert_called_once_with(model)
    session.commit.assert_called_once()
    namespace["clear_ui_cache"].assert_awaited_once_with(42)
