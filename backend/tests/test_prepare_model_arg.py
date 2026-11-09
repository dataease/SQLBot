"""Regression coverage for blank model-parameter values (issue: prepare_model_arg IndexError).

`prepare_model_arg` reads the first character of `origin_arg.strip()` to decide
whether the value looks like JSON, so an empty or whitespace-only string raised
`IndexError`. `get_default_config` calls the function from a dict comprehension
whose result feeds the runtime `additional_params`, and the surrounding
`try/except` swallowed the error, so a single blank parameter dropped every
additional parameter of that model configuration. `check_llm` skips blank values
via its own truthiness filter, which is why the failure only shows on the runtime
path.

The contract pinned here: a blank string is returned unchanged and never raises,
non-string values keep their identity, and one blank value cannot remove its
siblings from the loaded mapping.
"""

import pytest

from common.utils.utils import prepare_model_arg

BLANK_VALUES = ["", "   ", "\t", "\n", " \t\n "]


@pytest.mark.parametrize("value", BLANK_VALUES)
def test_blank_values_are_returned_unchanged(value):
    assert prepare_model_arg(value) == value


@pytest.mark.parametrize(
    "value, expected",
    [
        ('{"a": 1}', {"a": 1}),
        ('  {"a": 1}', {"a": 1}),
        ("[1, 2]", [1, 2]),
        ('{"a": {"b": [1, 2]}}', {"a": {"b": [1, 2]}}),
    ],
)
def test_json_looking_strings_are_still_parsed(value, expected):
    assert prepare_model_arg(value) == expected


@pytest.mark.parametrize("value", ["{not json", "[1,", '{"a": }', "plain", "3"])
def test_non_json_strings_are_returned_unchanged(value):
    assert prepare_model_arg(value) == value


@pytest.mark.parametrize("value", [0, 1, 1.5, False, True, None, {"a": 1}, [1, 2]])
def test_non_string_values_keep_their_identity(value):
    result = prepare_model_arg(value)
    assert result == value
    assert type(result) is type(value)


def _load_like_runtime(config_raw):
    """Mirror `get_default_config`: keep entries that carry both key and val."""
    return {
        item["key"]: prepare_model_arg(item.get("val"))
        for item in config_raw
        if "key" in item and "val" in item
    }


def test_one_blank_value_does_not_drop_the_other_parameters():
    config_raw = [
        {"key": "temperature", "val": 0},
        {"key": "note", "val": ""},
        {"key": "max_tokens", "val": 1024},
    ]
    assert _load_like_runtime(config_raw) == {
        "temperature": 0,
        "note": "",
        "max_tokens": 1024,
    }


@pytest.mark.parametrize("blank", BLANK_VALUES)
def test_blank_values_never_break_the_loaded_mapping(blank):
    config_raw = [
        {"key": "stream_usage", "val": False},
        {"key": "note", "val": blank},
        {"key": "top_p", "val": '{"p": 1}'},
    ]
    assert _load_like_runtime(config_raw) == {
        "stream_usage": False,
        "note": blank,
        "top_p": {"p": 1},
    }
