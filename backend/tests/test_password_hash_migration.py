"""Regression coverage for the password hashing migration (issue #1432).

Passwords used to be stored as unsalted MD5 digests, so a single database dump
allowed offline cracking and equal passwords were equal in the table. Storage
now goes through bcrypt (`common.core.security.get_password_hash`), while
verification keeps accepting a legacy digest so an existing deployment can still
log in once and gets upgraded during that login.

The tests below import the real helpers (no database, no xpack). `authenticate`
is extracted from source with the same AST helper the sibling guard
(`test_initial_password_policy.py`) uses, so the login upgrade path is covered
without importing DB/xpack startup.
"""

import ast
import hashlib
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from common.core.security import (
    default_pwd,
    default_pwd_hash,
    get_password_hash,
    is_legacy_md5_pwd,
    verify_md5pwd,
    verify_password,
)

ROOT = Path(__file__).resolve().parents[2]
USER_CRUD = "backend/apps/system/crud/user.py"
SECURITY_MODULE = ROOT / "backend" / "common" / "core" / "security.py"

PASSWORD = "Str0ng-Pass!23"
LEGACY_DIGEST = hashlib.md5(PASSWORD.encode("utf-8")).hexdigest()
# Only these helpers may hash a password with MD5, and only for the legacy
# verification path; `verify_md5pwd` / `is_legacy_md5_pwd` are lookups, not writes.
LEGACY_STORAGE_HELPERS = {"md5pwd", "default_md5_pwd"}


def load_function(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    node = next(
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    )
    node.decorator_list = []
    node.returns = None
    # `authenticate` takes keyword-only arguments, whose annotations would be
    # evaluated below with types this offline namespace does not provide.
    for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
        arg.annotation = None
    exec(
        compile(
            ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])),
            str(path),
            "exec",
        ),
        namespace,
    )
    return namespace[name]


def _login_context(stored_hash):
    """Run `authenticate` with the DB and DTO boundaries replaced."""

    class FakeSession:
        def __init__(self):
            self.added = []

        def add(self, obj):
            self.added.append(obj)

    session = FakeSession()
    stored_user = None
    if stored_hash is not None:
        stored_user = SimpleNamespace(id=7, account="alice", password=stored_hash)
    namespace = {
        "get_user_by_account": Mock(return_value=stored_user),
        "get_db_user": Mock(return_value=stored_user),
        "verify_password": verify_password,
        "get_password_hash": get_password_hash,
        "is_legacy_md5_pwd": is_legacy_md5_pwd,
        "BaseUserDTO": SimpleNamespace,
        "UserModel": SimpleNamespace,
    }
    load_function(USER_CRUD, "authenticate", namespace)
    load_function(USER_CRUD, "upgrade_legacy_pwd_hash", namespace)
    return session, stored_user, namespace["authenticate"]


# --- storage: new and changed passwords are bcrypt ---


def test_stored_hashes_are_bcrypt_not_md5():
    hashed = get_password_hash(PASSWORD)
    assert hashed.startswith("$2")
    assert not is_legacy_md5_pwd(hashed)
    assert len(hashed) <= 255  # sys_user.password column


def test_bcrypt_hash_only_verifies_the_original_password():
    hashed = get_password_hash(PASSWORD)
    assert verify_password(PASSWORD, hashed)
    assert not verify_password("Wrong-Pass!23", hashed)


def test_default_password_reset_uses_bcrypt():
    hashed = default_pwd_hash()
    assert hashed.startswith("$2")
    assert not is_legacy_md5_pwd(hashed)
    assert verify_password(default_pwd(), hashed)


# --- legacy digests: accepted for verification, never rewritten to MD5 ---


def test_legacy_md5_digest_still_verifies_a_pre_migration_row():
    assert is_legacy_md5_pwd(LEGACY_DIGEST)
    assert verify_password(PASSWORD, LEGACY_DIGEST)
    assert not verify_password("Wrong-Pass!23", LEGACY_DIGEST)


def test_legacy_helper_matches_the_compatibility_path():
    assert verify_md5pwd(PASSWORD, LEGACY_DIGEST)
    assert not verify_md5pwd("Wrong-Pass!23", LEGACY_DIGEST)


def test_verification_tolerates_empty_and_malformed_stored_values():
    assert not verify_password("", get_password_hash(PASSWORD))
    assert not verify_password(PASSWORD, "")
    assert not verify_password(PASSWORD, "not-a-hash")
    assert not verify_md5pwd("", LEGACY_DIGEST)
    assert not is_legacy_md5_pwd("")


# --- login path: a successful legacy login is upgraded to bcrypt ---


def test_legacy_login_is_migrated_to_bcrypt():
    session, user, authenticate = _login_context(LEGACY_DIGEST)
    assert authenticate(session=session, account="alice", password=PASSWORD) is user
    assert not is_legacy_md5_pwd(user.password)
    assert user.password.startswith("$2")
    assert verify_password(PASSWORD, user.password)
    assert session.added == [user]


def test_bcrypt_login_does_not_rewrite_the_hash():
    hashed = get_password_hash(PASSWORD)
    session, user, authenticate = _login_context(hashed)
    assert authenticate(session=session, account="alice", password=PASSWORD) is user
    assert user.password == hashed
    assert session.added == []


def test_failed_login_never_upgrades_a_legacy_digest():
    session, user, authenticate = _login_context(LEGACY_DIGEST)
    assert (
        authenticate(session=session, account="alice", password="Wrong-Pass!23") is None
    )
    assert user.password == LEGACY_DIGEST
    assert session.added == []


def test_unknown_account_is_rejected_without_writing():
    session, _, authenticate = _login_context(None)
    assert authenticate(session=session, account="alice", password=PASSWORD) is None
    assert session.added == []


# --- repository guard: production code must not store MD5 password hashes ---


def _legacy_storage_lines(path):
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in LEGACY_STORAGE_HELPERS
        ):
            yield f"{path.relative_to(ROOT)}:{node.lineno}"


def test_no_production_module_stores_passwords_with_md5():
    offenders = []
    for package in ("apps", "common"):
        for path in sorted((ROOT / "backend" / package).rglob("*.py")):
            if path == SECURITY_MODULE:
                continue  # holds the legacy helpers themselves
            offenders.extend(_legacy_storage_lines(path))
    assert not offenders, f"unsalted MD5 password hashing is back: {offenders}"


def test_the_storage_helper_never_calls_a_legacy_helper():
    tree = ast.parse(SECURITY_MODULE.read_text())
    storage = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "get_password_hash"
    )
    called = {
        node.func.id
        for node in ast.walk(storage)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert (
        not called & LEGACY_STORAGE_HELPERS
    ), f"storage path calls {called & LEGACY_STORAGE_HELPERS}"
