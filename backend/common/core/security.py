import hashlib
import hmac
import re
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext

from common.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


ALGORITHM = "HS256"

# Issue #1432: passwords used to be stored as unsalted MD5 digests. Rows that
# predate the bcrypt migration still carry one of these; they are accepted for
# verification only and are rewritten as bcrypt on the next successful login.
LEGACY_MD5_PWD_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


def create_access_token(data: dict | Any, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    # to_encode = {"exp": expire, "account": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_password_hash(password: str) -> str:
    """Hash a password for storage: bcrypt, never an unsalted MD5 digest (issue #1432)."""
    return pwd_context.hash(password)


def is_legacy_md5_pwd(hashed_password: str) -> bool:
    """True when a stored value is a legacy unsalted MD5 digest instead of a bcrypt hash."""
    return (
        bool(hashed_password)
        and LEGACY_MD5_PWD_PATTERN.fullmatch(hashed_password) is not None
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a stored hash.

    bcrypt hashes are checked with passlib. Legacy unsalted MD5 digests stay
    accepted so deployments created before issue #1432 was fixed can still log
    in; the caller that owns the session rewrites them with bcrypt right
    afterwards (see `apps.system.crud.user.authenticate`).
    """
    if not plain_password or not hashed_password:
        return False
    if is_legacy_md5_pwd(hashed_password):
        return hmac.compare_digest(md5pwd(plain_password), hashed_password.lower())
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


def md5pwd(password: str) -> str:
    """Legacy unsalted MD5 digest (issue #1432).

    Kept only so rows stored before the migration stay verifiable and can be
    upgraded. Never use it to store a new or changed password.
    """
    m = hashlib.md5()
    m.update(password.encode("utf-8"))
    return m.hexdigest()


def verify_md5pwd(plain_password: str, md5_password: str) -> bool:
    """Legacy-only verification against an unsalted MD5 digest (issue #1432)."""
    if not plain_password or not md5_password:
        return False
    return hmac.compare_digest(md5pwd(plain_password), md5_password.lower())


def default_pwd() -> str:
    return settings.DEFAULT_PWD


def default_pwd_hash() -> str:
    """bcrypt hash of the configured default password, used when resetting a user (issue #1432)."""
    return get_password_hash(default_pwd())


def default_md5_pwd() -> str:
    """Legacy digest of the default password (issue #1432).

    Kept so existing imports keep resolving; new call sites must use
    `default_pwd_hash` instead.
    """
    pwd = default_pwd()
    return md5pwd(pwd)
