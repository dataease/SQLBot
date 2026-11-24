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
    request = Request(
        {"type": "http", "headers": [(b"accept-language", header.encode())]}
    )
    assert i18n.get_language(request) == expected


def test_explicit_language_still_takes_precedence(i18n):
    request = Request(
        {"type": "http", "headers": [(b"accept-language", b"en-US,en;q=0.9")]}
    )
    assert i18n.get_language(request, "zh-TW") == "zh-tw"
    assert i18n.get_language(Request({"type": "http", "headers": []})) == "en"


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("zh-Hant-TW, zh-TW;q=0.9", "zh-tw"),
        ("zh-TW-u-nu-hanidec", "zh-tw"),
        ("zh-HK, en;q=0.8", "zh-tw"),
        ("zh-Hans-TW", "zh-cn"),
        ("en-US, ko-KR;q=0.95, en;q=0.1", "ko-kr"),
        ("zh;q=0.9, zh-CN;q=0.1, ko-KR;q=0.8", "zh-tw"),
        ("zh, zh-CN;q=0, zh-TW;q=0.8", "zh-tw"),
        ("en-US, en;q=0, th-TH;q=0.8", "th-th"),
        ("zh;q=0, zh-TW;q=0.5, *;q=0", "zh-tw"),
        ("zh-CN;q=0, *;q=0.5", "en"),
        ("en;q=1e0, th-TH;q=0.8", "th-th"),
        ("en;q=0.9999, th-TH;q=0.8", "th-th"),
        ("th;q=0.700, ko;q=0.700", "th-th"),
        ("en;q=0, fr", "zh-cn"),
        ("*", "zh-cn"),
    ],
)
def test_language_ranges_and_weights(i18n, header, expected):
    request = Request(
        {"type": "http", "headers": [(b"accept-language", header.encode())]}
    )
    assert i18n.get_language(request) == expected


def test_multiple_field_lines_share_one_preference_order(i18n):
    request = Request(
        {
            "type": "http",
            "headers": [
                (b"accept-language", b"en;q=0.5"),
                (b"accept-language", b"th-TH;q=0.9"),
            ],
        }
    )
    assert i18n.get_language(request) == "th-th"
    assert i18n.get_language(request, "en") == "en"
    assert i18n.get_language(request, "unsupported") == "zh-cn"
    assert i18n.get_language() == "zh-cn"
