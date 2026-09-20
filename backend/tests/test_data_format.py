"""Regression tests for numeric values shared by query results and Excel exports."""

import ast
from decimal import Decimal
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def convert_numbers():
    # Follow the existing isolated tests without importing the chat/LLM stack.
    source = Path(__file__).resolve().parents[1] / "common/utils/data_format.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    node = next(
        node for node in tree.body if getattr(node, "name", None) == "DataFormat"
    )
    namespace = {"Decimal": Decimal}
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"),
        namespace,
    )
    return namespace["DataFormat"].convert_large_numbers_in_object_array


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1.23e20, "123000000000000000000"),
        (-1.23e20, "-123000000000000000000"),
        (1.23e-10, "0.000000000123"),
        (-1.23e-10, "-0.000000000123"),
        (1e20, "100000000000000000000"),
        (1e-7, "0.0000001"),
        (1e10, "10000000000"),
        (12345678901.25, "12345678901.25"),
        (0.0, "0"),
        (-0.0, "0"),
    ],
)
def test_float_conversion_preserves_value_without_scientific_notation(
    convert_numbers, value, expected
):
    assert convert_numbers([{"value": value}]) == [{"value": expected}]


def test_values_outside_conversion_thresholds_keep_their_types(convert_numbers):
    row = {
        "regular_float": 123.4,
        "small_float_boundary": 1e-6,
        "below_float_threshold": 9999999999.5,
        "below_int_threshold": 999999999999999,
        "large_integer": 1000000000000000,
        "negative_integer": -1000000000000000,
        "zero": 0,
        "flag": True,
        "text": "1.23e20",
        "missing": None,
    }

    converted = convert_numbers([row])[0]

    assert converted == {
        **row,
        "large_integer": "1000000000000000",
        "negative_integer": "-1000000000000000",
    }
    for key in ("regular_float", "small_float_boundary", "below_float_threshold"):
        assert isinstance(converted[key], float)


def test_scientific_notation_is_converted_in_nested_rows(convert_numbers):
    rows = [{"metrics": {"amount": 1.23e20}, "series": [{"value": 1.23e-10}]}]

    assert convert_numbers(rows) == [
        {
            "metrics": {"amount": "123000000000000000000"},
            "series": [{"value": "0.000000000123"}],
        }
    ]
    assert rows[0]["metrics"]["amount"] == 1.23e20


def test_excel_integer_threshold_remains_supported(convert_numbers):
    assert convert_numbers(
        [{"below": 99999999999, "boundary": 100000000000, "amount": 1.23e20}],
        int_threshold=1e11,
    ) == [
        {
            "below": 99999999999,
            "boundary": "100000000000",
            "amount": "123000000000000000000",
        }
    ]
