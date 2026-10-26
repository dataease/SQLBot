"""Offline behavior tests of password handlers with external boundaries replaced.

Extract actual functions to avoid importing DB/xpack startup. These tests do not
claim coverage of authentication middleware, decorators or real transactions.
"""

import ast
import asyncio
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[2]


def load_function(path, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    node = next(
        n
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
    )
    node.decorator_list = []
    node.returns = None
    for arg in node.args.args:
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


def md5(value):
    return hashlib.md5(value.encode()).hexdigest()


@pytest.fixture
def context():
    user = SimpleNamespace(id=2, password=md5("OldPassword42!"))
    session = Mock()
    args = AsyncMock(
        return_value=[SimpleNamespace(pkey="login.initial_pwd_disabled", pval="true")]
    )
    ns = {
        "get_group_args": args,
        "HTTPException": HTTPException,
        "get_db_user": Mock(return_value=user),
        "md5pwd": md5,
        "verify_md5pwd": lambda value, hashed: md5(value) == hashed,
        "default_pwd": lambda: "InitialPassword42!",
        "settings": SimpleNamespace(DEFAULT_PWD="InitialPassword42!"),
    }
    import re

    ns["re"] = re
    schema = ast.parse(
        (ROOT / "backend/apps/system/schemas/system_schema.py").read_text()
    )
    regex = next(
        n
        for n in schema.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "PWD_REGEX" for t in n.targets)
    )
    exec(
        compile(ast.Module(body=[regex], type_ignores=[]), "<password-regex>", "exec"),
        ns,
    )
    load_function("backend/apps/system/crud/user.py", "check_pwd_format", ns)
    policy_path = "backend/apps/system/crud/password_policy.py"
    if not (ROOT / policy_path).exists():
        policy_path = "backend/apps/system/api/login.py"
    load_function(policy_path, "initial_pwd_disabled", ns)
    handler = load_function("backend/apps/system/api/user.py", "pwdUpdate", ns)
    return user, session, args, ns, handler


def update(context, new="InitialPassword42!", old="OldPassword42!", uid=2):
    _, session, _, _, handler = context
    return asyncio.run(
        handler(
            session,
            SimpleNamespace(id=uid),
            lambda message_key, **kwargs: message_key,
            SimpleNamespace(pwd=old, new_pwd=new),
        )
    )


@pytest.mark.parametrize("uid", [1, 2])
def test_disabled_rejects_initial_password_without_writing(context, uid):
    user, session, _, ns, _ = context
    before = user.password
    with pytest.raises(HTTPException) as exc:
        update(context, uid=uid)
    assert exc.value.status_code == 400
    assert exc.value.detail == "i18n_login.new_pwd_is_initial"
    assert user.password == before
    session.add.assert_not_called()
    ns["get_db_user"].assert_called_once_with(session=session, user_id=uid)


@pytest.mark.parametrize("value", ["false", False, None])
def test_disabled_off_allows_initial_password(context, value):
    user, session, args, _, _ = context
    args.return_value = [SimpleNamespace(pkey="login.initial_pwd_disabled", pval=value)]
    update(context)
    assert user.password == md5("InitialPassword42!")
    session.add.assert_called_once_with(user)


def test_enabled_allows_other_password(context):
    user, session, _, _, _ = context
    update(context, new="DifferentPassword42!")
    assert user.password == md5("DifferentPassword42!")
    session.add.assert_called_once_with(user)


@pytest.mark.parametrize(
    "old,new", [("wrong", "InitialPassword42!"), ("OldPassword42!", "bad")]
)
def test_invalid_credentials_or_format_never_write(context, old, new):
    user, session, _, _, _ = context
    before = user.password
    with pytest.raises(Exception) as exc:
        update(context, old=old, new=new)
    assert str(exc.value) == ("i18n_error" if old == "wrong" else "i18n_format_invalid")
    assert user.password == before
    session.add.assert_not_called()


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        (" TRUE ", True),
        (True, True),
        ("false", False),
        (False, False),
        (None, False),
    ],
)
def test_policy_config_values(context, value, expected):
    _, session, args, ns, _ = context
    args.return_value = [SimpleNamespace(pkey="login.initial_pwd_disabled", pval=value)]
    assert asyncio.run(ns["initial_pwd_disabled"](session)) is expected
    args.assert_awaited_once_with(session=session, flag="login")


def test_missing_policy_defaults_off(context):
    _, session, args, ns, _ = context
    args.return_value = []
    assert asyncio.run(ns["initial_pwd_disabled"](session)) is False


def test_error_translations_present():
    for locale in ["en", "zh-CN", "zh-TW", "ko-KR", "th-TH"]:
        messages = json.loads((ROOT / "backend/locales" / f"{locale}.json").read_text())
        assert messages["i18n_login"]["new_pwd_is_initial"]
