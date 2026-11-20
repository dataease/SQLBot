"""Guard: assistant request headers must not turn a request into a 500.

``get_current_assistant`` reads two optional headers. They describe an assistant
identity that the auth middleware resolves, so before this guard the header
values were written onto whatever ``request.state`` held: a request carrying the
header without an assistant identity raised ``AttributeError``, and a malformed
certificate raised a decoding error. Both surfaced as 500 instead of a usable
answer or a 400.
"""

import asyncio
import base64
from types import SimpleNamespace
from urllib.parse import quote

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from common.core.deps import get_current_assistant

_MISSING = object()


def _request(headers: dict[str, str], assistant=_MISSING) -> Request:
    encoded = [(key.lower().encode(), value.encode()) for key, value in headers.items()]
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": encoded,
        }
    )
    if assistant is not _MISSING:
        request.state.assistant = assistant
    return request


def test_header_without_assistant_identity_returns_none():
    request = _request({"X-SQLBOT-ASSISTANT-CERTIFICATE": "YWJj"})

    assert asyncio.run(get_current_assistant(request)) is None


def test_online_header_without_assistant_identity_returns_none():
    request = _request({"X-SQLBOT-ASSISTANT-ONLINE": "true"})

    assert asyncio.run(get_current_assistant(request)) is None


def test_certificate_header_is_decoded_and_unquoted():
    assistant = SimpleNamespace(certificate=None, online=None)
    payload = '{"token":"a b"}'
    header = quote(base64.b64encode(payload.encode()).decode())

    result = asyncio.run(
        get_current_assistant(_request({"X-SQLBOT-ASSISTANT-CERTIFICATE": header}, assistant))
    )

    assert result is assistant
    assert assistant.certificate == payload


def test_online_header_sets_the_flag():
    assistant = SimpleNamespace(certificate=None, online=None)

    result = asyncio.run(
        get_current_assistant(_request({"X-SQLBOT-ASSISTANT-ONLINE": "TRUE"}, assistant))
    )

    assert result.online is True


@pytest.mark.parametrize("header", ["A", "//4="])
def test_unreadable_certificate_is_rejected(header):
    assistant = SimpleNamespace(certificate=None, online=None)

    with pytest.raises(HTTPException) as excinfo:
        asyncio.run(
            get_current_assistant(_request({"X-SQLBOT-ASSISTANT-CERTIFICATE": header}, assistant))
        )

    assert excinfo.value.status_code == 400
    assert assistant.certificate is None