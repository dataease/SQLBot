"""Regression tests for supported locales in browser Accept-Language headers."""

from pathlib import Path

import pytest
from starlette.requests import Request

from common.utils.locale import I18n


@pytest.fixture(scope="module")
def i18n():
    return I18n(Path(__file__).resolve().parents[1] / "locales")


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("en-US,en;q=0.9", "en"),
        ("fr-FR, ko-KR;q=0.8, en;q=0.5", "ko-kr"),
        ("zh-TW;q=0.5, th-TH;q=0.9", "th-th"),
        ("en;q=0, zh-TW;q=0.5", "zh-tw"),
        ("en;q=invalid, th-TH;q=0.5", "th-th"),
        ("fr-FR, *;q=0.1", "zh-cn"),
    ],
)
def test_request_header_selects_supported_language(i18n, header, expected):
    request = Request({"type": "http", "headers": [(b"accept-language", header.encode())]})
    assert i18n.get_language(request) == expected


def test_explicit_language_still_takes_precedence(i18n):
    request = Request({"type": "http", "headers": [(b"accept-language", b"en-US,en;q=0.9")]})
    assert i18n.get_language(request, "zh-TW") == "zh-tw"
    assert i18n.get_language(Request({"type": "http", "headers": []})) == "en"
