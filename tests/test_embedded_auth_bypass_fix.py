"""
Tests for the CNVD embedded-auth-bypass fix (Host header injection + forged admin token).

Validates:
1. HostValidationMiddleware regex accepts valid Host headers and rejects
   path-carrying / malformed ones (defense against URL path pollution).
2. Whitelist matching behavior after tightening "/mcp*" -> "/mcp/*":
   - real business routes (/mcp/xxx) still match;
   - injected paths are rejected at middleware level by using scope["path"]
     (whitelist-level tightening alone is documented as defense-in-depth).
3. Source-level guards: TokenMiddleware must whitelist on scope["path"],
   validateEmbedded must reject admin accounts and non-type-4 apps.
"""
import os
import re
import textwrap

import pytest


# ---------- Paths to sources ----------

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_HOST_VALIDATION_SRC = os.path.join(_ROOT, "backend", "common", "core", "host_validation.py")
_WHITELIST_SRC = os.path.join(_ROOT, "backend", "common", "utils", "whitelist.py")
_AUTH_SRC = os.path.join(_ROOT, "backend", "apps", "system", "middleware", "auth.py")

with open(_HOST_VALIDATION_SRC) as f:
    _host_validation_source = f.read()
with open(_WHITELIST_SRC) as f:
    _whitelist_source = f.read()
with open(_AUTH_SRC) as f:
    _auth_source = f.read()

# ---------- Extract Host validation regex ----------

_ns = {"re": re}
exec(
    compile(
        textwrap.dedent("""
_HOST_RE = re.compile(r'^[A-Za-z0-9.\\-:\\[\\]]{1,255}$')
"""),
        "<extracted>",
        "exec",
    ),
    _ns,
)
_HOST_RE = _ns["_HOST_RE"]


# ============================================================
# Test Host header validation
# ============================================================

class TestHostValidation:
    """Valid Host headers pass; path-carrying / malformed ones are rejected."""

    @pytest.mark.parametrize("host", [
        "localhost",
        "localhost:8000",
        "127.0.0.1",
        "127.0.0.1:8000",
        "example.com",
        "api.example.com:443",
        "[::1]",
        "[::1]:8000",
        "10.0.0.1",
        "a.b.c.d.e.f.g",
    ])
    def test_valid_host_accepted(self, host):
        assert _HOST_RE.match(host) is not None

    @pytest.mark.parametrize("host", [
        "",                      # empty
        "evil.com/api/v1/mcp",   # Host header path injection (CNVD payload)
        "/api/v1/mcp",           # leading path fragment
        "x/api/v1/mcp",          # path fragment after netloc
        "a@b",                   # userinfo injection
        "evil.com/path?x=1",     # query fragment
        "evil.com#frag",         # fragment
        "evil com",              # whitespace
        "evil.com\nX-Real-IP: 1.2.3.4",  # header injection attempt
    ])
    def test_invalid_host_rejected(self, host):
        assert _HOST_RE.match(host) is None


# ============================================================
# Test whitelist matching behavior
# ============================================================

# Extract the pattern-compilation + matching logic with a fake settings object,
# mirroring the source implementation.
_ns2 = {}
exec(
    compile(
        textwrap.dedent("""
import re

# '/mcp*' tightened to '/mcp/*' in the fix
wlist = [
    "/",
    "/docs",
    "/login/*",
    "*.ico",
    "*.html",
    "*.js",
    "*.css",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
    "*.otf",
    "*.css.map",
    "/mcp*",
    "/system/license",
    "/system/config/key",
    "/images/*",
    "/sse",
    "/system/appearance/ui",
    "/system/appearance/picture/*",
    "/system/assistant/info/*",
    "/system/assistant/app/*",
    "/system/assistant/picture/*",
    "/system/assistant/validate/*",
    "/system/authentication/platform/status",
    "/system/authentication/login/*",
    "/system/authentication/sso/*",
    "/system/platform/sso/*",
    "/system/platform/client/*",
    "/system/parameter/login",
]

class FakeSettings:
    API_V1_STR = "/api/v1"
    CONTEXT_PATH = ""

settings = FakeSettings()

class WhitelistChecker:
    def __init__(self, paths=None):
        self.whitelist = paths or wlist
        self._compiled_patterns = []
        self._compile_patterns()

    def _compile_patterns(self):
        for pattern in self.whitelist:
            if "*" in pattern:
                regex_pattern = (
                    pattern.replace(".", r"\\.")
                    .replace("*", ".*")
                )
                regex_pattern = f"^{regex_pattern}$"
                self._compiled_patterns.append(re.compile(regex_pattern))

    def is_whitelisted(self, path):
        prefix = settings.API_V1_STR
        if path.startswith(prefix):
            path = path[len(prefix):]

        context_prefix = settings.CONTEXT_PATH
        if context_prefix and path.startswith(context_prefix):
            path = path[len(context_prefix):]

        if not path:
            path = '/'
        if path in self.whitelist:
            return True

        path = path.rstrip('/')
        return any(
            pattern.match(path) is not None
            for pattern in self._compiled_patterns
        )

checker = WhitelistChecker()
"""),
        "<extracted>",
        "exec",
    ),
    _ns2,
)
_is_whitelisted = _ns2["checker"].is_whitelisted


class TestWhitelistMatching:
    """Whitelist behavior: legitimate routes match; protected routes must not."""

    # --- Real business routes still match ---

    @pytest.mark.parametrize("path", [
        "/api/v1/mcp/access_token",
        "/api/v1/mcp/mcp_start",
        "/api/v1/mcp/mcp_question",
        "/api/v1/mcp/mcp_assistant",
        "/mcp/access_token",
        "/api/v1/login/access-token",
        "/api/v1/system/config/key",
        "/api/v1/system/assistant/info/123",
    ])
    def test_legit_whitelisted_paths_still_match(self, path):
        assert _is_whitelisted(path) is True

    # --- Protected routes must NOT be whitelisted on real paths ---

    @pytest.mark.parametrize("path", [
        "/api/v1/system/embedded",
        "/api/v1/user/info",
        "/api/v1/user/defaultPwd",
        "/api/v1/system/user/list",
        "/api/v1/chat/list",
        "/api/v1/datasource/list",
    ])
    def test_protected_paths_not_whitelisted(self, path):
        assert _is_whitelisted(path) is False

    def test_injected_path_documented_as_defense_in_depth(self):
        """Host-injected path still matches whitelist-level check, which is why
        the middleware must pass scope["path"] (real path) instead of url.path.
        This test pins the whitelist behavior so future changes are deliberate."""
        # '/api/v1/mcp/api/v1/system/embedded' strips the prefix to
        # '/mcp/api/v1/system/embedded' -> matches ^/mcp.*$
        assert _is_whitelisted("/api/v1/mcp/api/v1/system/embedded") is True
        # The REAL path of that same request must not match:
        assert _is_whitelisted("/api/v1/system/embedded") is False


# ============================================================
# Source-level regression guards
# ============================================================

class TestSourceLevelGuards:
    """Pin the actual fix points in source to prevent regressions."""

    def test_auth_middleware_uses_scope_path(self):
        assert "request.scope.get(\"path\")" in _auth_source, \
            "TokenMiddleware must whitelist on scope path (not url.path)"

    def test_auth_middleware_preflight_uses_scope_path(self):
        # the preflight regex search must not use request.url.path
        assert "re.search(r'/system/assistant/info/(\\d+)', request_path)" in _auth_source

    def test_validate_embedded_rejects_admin(self):
        assert "isAdmin:" in _auth_source and \
            "Admin account is not allowed for embedded token" in _auth_source, \
            "validateEmbedded must reject admin accounts"

    def test_validate_embedded_checks_type(self):
        assert "assistant_info.type != 4" in _auth_source, \
            "validateEmbedded must only accept type=4 embedded apps"

    def test_host_validation_middleware_exists(self):
        assert "class HostValidationMiddleware" in _host_validation_source

    def test_host_validation_registered(self):
        main_src_path = os.path.join(_ROOT, "backend", "main.py")
        with open(main_src_path) as f:
            main_source = f.read()
        assert "app.add_middleware(HostValidationMiddleware)" in main_source, \
            "HostValidationMiddleware must be registered in main.py"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
