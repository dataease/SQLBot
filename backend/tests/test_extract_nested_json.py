import os
import sys

import orjson
import pytest

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from common.utils.utils import extract_nested_json  # noqa: E402


def test_standard_json_extraction():
    raw = '{"sql": "SELECT * FROM users WHERE status = 1", "success": true}'
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == "SELECT * FROM users WHERE status = 1"
    assert data["success"] is True


def test_standard_json_array_extraction():
    raw = '[{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]'
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert len(data) == 2
    assert data[0]["id"] == 1


def test_sql_with_single_left_brace():
    """Test Issue #1401: SQL containing an unmatched left curly brace '{'."""
    raw = """{"sql": "SELECT * FROM config WHERE path LIKE '{'", "success": true}"""
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == "SELECT * FROM config WHERE path LIKE '{'"
    assert data["success"] is True


def test_sql_with_single_right_brace():
    """Test Issue #1401: SQL containing an unmatched right curly brace '}'."""
    raw = """{"sql": "SELECT * FROM logs WHERE note LIKE '%}'", "success": true}"""
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == "SELECT * FROM logs WHERE note LIKE '%}'"
    assert data["success"] is True


def test_sql_with_balanced_braces_in_like_pattern():
    """Test Issue #1401: SQL with LIKE pattern containing '{pattern}'."""
    raw = """{"sql": "SELECT * FROM users WHERE tag LIKE '%{vip}%'", "success": true}"""
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == "SELECT * FROM users WHERE tag LIKE '%{vip}%'"
    assert data["success"] is True


def test_sql_with_escaped_quotes_and_braces():
    """Test SQL with escaped double quotes and braces inside string literal."""
    raw = r"""{"sql": "SELECT \"col\" FROM t WHERE json_val = '{\"key\": \"val\"}'", "success": true}"""
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == 'SELECT "col" FROM t WHERE json_val = \'{"key": "val"}\''
    assert data["success"] is True


def test_sql_with_escaped_backslashes():
    """Test SQL containing escaped backslashes and path delimiters."""
    raw = r"""{"sql": "SELECT * FROM files WHERE path = 'C:\\Users\\default\\{tmp}'", "success": true}"""
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == r"SELECT * FROM files WHERE path = 'C:\Users\default\{tmp}'"
    assert data["success"] is True


def test_markdown_code_block_wrapping():
    """Test JSON wrapped inside markdown code block."""
    raw = """Here is the query result:
```json
{
  "sql": "SELECT * FROM users WHERE template LIKE '%{test}%'",
  "success": true
}
```
Hope this helps!"""
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == "SELECT * FROM users WHERE template LIKE '%{test}%'"
    assert data["success"] is True


def test_leading_explanation_with_braces_and_quotes():
    """Test text preceding the JSON that contains braces or quotes."""
    raw = """注意：参数模板例如 {workspace_id}，大模型返回的结果如下：
{"sql": "SELECT * FROM table WHERE col = '{foo}'", "success": true}"""
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == "SELECT * FROM table WHERE col = '{foo}'"
    assert data["success"] is True


def test_invalid_candidate_before_valid_json():
    """Test that invalid braced block before valid JSON does not break extraction."""
    raw = '{invalid json here} Followed by valid: {"sql": "SELECT 1", "success": true}'
    extracted = extract_nested_json(raw)
    assert extracted is not None
    data = orjson.loads(extracted)
    assert data["sql"] == "SELECT 1"


@pytest.mark.parametrize(
    "invalid_input", [None, "", "   ", 123, [], {}, "No json at all here"]
)
def test_invalid_or_empty_inputs(invalid_input):
    assert extract_nested_json(invalid_input) is None


@pytest.mark.parametrize(
    "invalid_candidate",
    [
        '{"tables": [],}',
        '{"outer": {"success": true, "sql": "SELECT 0"}, bad}',
        '[{"year": 2026, "value": 10},]',
        '{"sql": "SELECT \'{}\'", bad}',
        '{"tables": [}, "other": {"success": true}}',
        '{"value": NaN, "tables": []}',
        '{"sql": "SELECT\n1", "tables": []}',
    ],
)
def test_invalid_outer_candidate_does_not_expose_nested_values(invalid_candidate):
    assert extract_nested_json(invalid_candidate) is None
    answer = '{"success": true, "sql": "SELECT 1", "tables": ["t"]}'
    assert extract_nested_json(invalid_candidate + " then " + answer) == answer


@pytest.mark.parametrize(
    "truncated",
    [
        '{"sql": "SELECT 1", "tables": ["t"]',
        '[{"year": 2026, "value": 10},',
        '[{"x": 1}',
        '{"outer": {"success": true, "sql": "SELECT 1"}',
        '{"text": "unterminated [] {}',
    ],
)
def test_truncated_outer_candidate_is_rejected(truncated):
    assert extract_nested_json(truncated) is None


@pytest.mark.parametrize(
    "answer",
    [
        '{"outer": [{"inner": [1, 2]}, []], "empty": {}}',
        "{\"sql\": \"SELECT '[', ']', '{', '}'\", \"tables\": []}",
        r'{"text": "escaped quote: \" { [", "tail": "ends in slash \\"}',
        "{}",
        "[]",
    ],
)
def test_complete_outer_candidate_is_preserved(answer):
    assert (
        extract_nested_json('Explanation: "answer" ```json\n' + answer + "\n```")
        == answer
    )
    assert extract_nested_json(answer + ' {"next": true}') == answer
