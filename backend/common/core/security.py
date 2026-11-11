from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from common.core.config import settings

# Keep these public names for integrations; credential formats live in one module.
from common.core.passwords import (
    hash_password as get_password_hash,
)
from common.core.passwords import (
    legacy_md5,
    verify_password,
)

ALGORITHM = "HS256"


def create_access_token(data: dict | Any, expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + expires_delta
    to_encode.update({"exp": expire})
    # to_encode = {"exp": expire, "account": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def md5pwd(password: str) -> str:
    """Legacy fixture/integration helper; never use for new credential writes."""
    return legacy_md5(password)


def verify_md5pwd(plain_password: str, md5_password: str) -> bool:
    """Compatibility name; accepts all supported versioned credential formats."""
    return verify_password(plain_password, md5_password)


def default_pwd() -> str:
    return settings.DEFAULT_PWD


def default_password_hash() -> str:
    return get_password_hash(default_pwd())


def default_md5_pwd() -> str:
    """Compatibility alias: new default credentials must never be bare MD5."""
    return default_password_hash()
