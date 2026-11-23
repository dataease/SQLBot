"""Explicit cross-repository binding fixture; never opens the product database.

Reuse the xpack synthetic SQLite fixture and its real routes/token middleware.
Only the license, external provider and browser's current-user boundary are replaced.
"""

import importlib.util
import json
import logging
import os
import signal
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlencode

import pytest

logging.getLogger("httpx").setLevel(logging.WARNING)

root = Path(os.environ["SQLBOT_XPACK_TEST_ROOT"]).resolve()
spec = importlib.util.spec_from_file_location(
    "binding_browser_fixture", root / "tests/test_account_bindings.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ui_url = os.environ["SQLBOT_BINDING_UI_URL"]
port = int(os.environ["SQLBOT_BINDING_BACKEND_PORT"])


class Fixture:
    def __init__(self):
        self.generator = None
        self.reset()

    def close(self):
        if self.generator:
            self.generator.close()
            self.patch.undo()
            self.directory.cleanup()
            self.generator = None

    def reset(self):
        self.close()
        self.directory = TemporaryDirectory(prefix="binding-browser-")
        self.patch = pytest.MonkeyPatch()
        self.generator = module.env.__wrapped__(Path(self.directory.name), self.patch)
        self.env = next(self.generator)

        async def authorization(_origin, _config, callback_url, state):
            return {
                "url": ui_url + "/provider?" + urlencode({"state": state}),
                "client": {},
                "callback_url": callback_url,
            }

        module.b.authorization.side_effect = authorization
        async def ldap_identity(_config, username, password):
            if username != 'directory-user' or password != 'SyntheticDirectory42!':
                raise ValueError('invalid directory credentials')
            return {'account': 'directory-id', 'name': 'Directory User'}
        self.patch.setattr(module.b, 'verify_ldap_identity', ldap_identity)


fixture = Fixture()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass  # No request state, tokens or bodies in fixture logs.

    def do_GET(self):
        self.dispatch()

    def do_POST(self):
        self.dispatch()

    def do_DELETE(self):
        self.dispatch()

    def dispatch(self):
        data = None
        status = 200
        if self.path == "/__test/health":
            data = {"ready": True}
        elif self.path == "/__test/reset" and self.command == "POST":
            fixture.reset()
            data = {"ready": True}
        elif self.path == "/__test/evidence":
            with module.Session(fixture.env.db) as session:
                records = session.exec(module.select(module.UserBindingRequest)).all()
                links = session.exec(module.select(module.UserPlatformModel)).all()
            data = {"password_attempts": len(records), "links": len(links)}
        else:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else None
            path = self.path.replace("/api/system/", "/api/v1/system/", 1)
            headers = fixture.env.headers()
            if body and path.endswith("/requests"):
                # The synthetic fixture's trusted origin is testserver.
                body["callback_url"] = "http://testserver/"
            response = fixture.env.client.request(
                self.command, path, headers=headers, json=body
            )
            status = response.status_code
            data = response.json()
            if status >= 400:
                key = data.get("detail", "")
                data = {
                    "i18n_binding.rate_limit": "操作过于频繁，请稍后重试。",
                    "i18n_binding.password": "密码不正确。",
                }.get(key, key)
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)


def terminate(_signum, _frame):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, terminate)
try:
    with HTTPServer(("127.0.0.1", port), Handler) as server:
        server.serve_forever()
finally:
    fixture.close()
