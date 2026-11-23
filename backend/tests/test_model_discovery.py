"""Offline model discovery protocol and real permission decorator regression."""

import ast
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from fastapi import HTTPException

from apps.system.crud import model_discovery as discovery
from apps.system.schemas.ai_model_schema import ModelDiscoveryRequest


def run_response(
    status=200, payload=None, key="", base="http://model.test/prefix/v1/", headers=None
):
    requests = []
    real_client = httpx.AsyncClient

    async def serve(request):
        requests.append(request)
        return httpx.Response(status, json=payload, headers=headers)

    with patch.object(
        discovery.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(serve)),
    ):
        result = asyncio.run(discovery.discover_models(base, key))
    return result, requests


def test_list_ids_no_key_and_path():
    result, requests = run_response(
        payload={"data": [{"id": "a"}, {"id": "a"}, {"id": "b"}]}
    )
    assert result == ["a", "b"]
    assert str(requests[0].url) == "http://model.test/prefix/v1/models"
    assert "authorization" not in requests[0].headers
    result, requests = run_response(payload={"data": []}, key="synthetic-secret")
    assert result == []
    assert requests[0].headers["authorization"] == "Bearer synthetic-secret"


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "credentials"),
        (403, "credentials"),
        (404, "unsupported"),
        (405, "unsupported"),
        (501, "unsupported"),
        (500, "failed"),
        (302, "failed"),
    ],
)
def test_failures_and_no_redirect(status, code):
    with pytest.raises(discovery.ModelDiscoveryError, match=code):
        run_response(
            status, {"data": []}, headers={"Location": "http://other.test/models"}
        )


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"data": {}},
        {"data": [{"id": ""}]},
        {"data": [{"id": 123}]},
        {"data": [{"id": "a" * 256}]},
        {"data": [{"id": "synthetic-secret"}]},
        {"data": [{"id": "x\n"}]},
        {"data": [{"id": "a"}] * 2001},
    ],
)
def test_invalid_payload(payload):
    with pytest.raises(discovery.ModelDiscoveryError, match="invalid"):
        run_response(payload=payload, key="synthetic-secret")


@pytest.mark.parametrize(
    "base",
    [
        "file:///etc/passwd",
        "ftp://model.test",
        "http://a@b/v1",
        "http://a/v1?key=x",
        "http://a/v1#x",
        "http://a:bad",
        "http://a\\b",
        "http://a/ x",
    ],
)
def test_reject_invalid_url_before_request(base):
    with pytest.raises(discovery.ModelDiscoveryError, match="address"):
        discovery.models_url(base)


def test_timeout_and_size():
    real_client = httpx.AsyncClient

    async def serve(_request):
        raise httpx.ReadTimeout("synthetic-secret")

    with patch.object(
        discovery.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(**kwargs, transport=httpx.MockTransport(serve)),
    ):
        with pytest.raises(discovery.ModelDiscoveryError, match="timeout"):
            asyncio.run(
                discovery.discover_models("http://model.test", "synthetic-secret")
            )
    with patch.object(discovery, "MAX_BYTES", 10):
        with pytest.raises(discovery.ModelDiscoveryError, match="invalid"):
            run_response(payload={"data": [{"id": "a"}]})


def test_real_route_permission_and_safe_error():
    import sqlbot_xpack  # noqa: F401 -- initialize released wheel

    from apps.system.schemas.permission import (
        RequestContext,
        SqlbotPermission,
        require_permissions,
    )

    namespace = {
        "router": SimpleNamespace(post=lambda *a, **kw: lambda f: f),
        "require_permissions": require_permissions,
        "SqlbotPermission": SqlbotPermission,
        "ModelDiscoveryRequest": ModelDiscoveryRequest,
        "Trans": object,
        "discover_models": discovery.discover_models,
        "ModelDiscoveryError": discovery.ModelDiscoveryError,
    }
    path = Path(__file__).parents[1] / "apps/system/api/aimodel.py"
    node = next(
        n
        for n in ast.parse(path.read_text()).body
        if getattr(n, "name", "") == "list_provider_models"
    )
    exec(
        compile(ast.Module(body=[node], type_ignores=[]), str(path), "exec"), namespace
    )
    handler = namespace["list_provider_models"]
    info = ModelDiscoveryRequest(
        api_domain="file:///invalid", api_key="synthetic-secret"
    )
    assert "synthetic-secret" not in repr(info)
    for user in [
        None,
        SimpleNamespace(oid=1, isAdmin=False, weight=0),
        SimpleNamespace(oid=1, isAdmin=False, weight=1),
    ]:
        request = SimpleNamespace(
            state=SimpleNamespace(current_user=user, assistant=None), headers={}
        )
        with patch.object(RequestContext, "get_request", return_value=request):
            with pytest.raises(Exception) as rejected:
                asyncio.run(handler(info, lambda key: key))
            if user is None:
                assert isinstance(rejected.value, HTTPException)
                assert rejected.value.status_code == 401
            else:
                assert str(rejected.value) == "Only administrators are allowed to call!"
    request = SimpleNamespace(
        state=SimpleNamespace(
            current_user=SimpleNamespace(oid=1, isAdmin=True), assistant=None
        ),
        headers={},
    )
    with patch.object(RequestContext, "get_request", return_value=request):
        result = asyncio.run(handler(info, lambda key: key))
    assert result == {
        "models": [],
        "error_code": "address",
        "error": "i18n_model_discovery.address",
    }
    assert "synthetic-secret" not in json.dumps(result)

    async def timeout_discovery(*_args):
        raise discovery.ModelDiscoveryError("timeout")

    namespace["discover_models"] = timeout_discovery
    with patch.object(RequestContext, "get_request", return_value=request):
        result = asyncio.run(handler(info, lambda key: key))
    assert result == {
        "models": [],
        "error_code": "timeout",
        "error": "i18n_model_discovery.timeout",
    }



def test_loopback_http_service():
    """Exercise the actual HTTP transport against a synthetic private service."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    received = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            received.append((self.path, self.headers.get("Authorization")))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                b'{"data":[{"id":"loopback-chat"},{"id":"loopback-chat"}]}'
            )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}/custom/v1"
        assert asyncio.run(discovery.discover_models(base, "")) == ["loopback-chat"]
        assert asyncio.run(discovery.discover_models(base, "synthetic-secret")) == [
            "loopback-chat"
        ]
        assert received == [
            ("/custom/v1/models", None),
            ("/custom/v1/models", "Bearer synthetic-secret"),
        ]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
