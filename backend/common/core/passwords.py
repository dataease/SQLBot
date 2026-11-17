"""Versioned local credentials. No configuration or application imports.

Legacy MD5 is read-only compatibility. New writes always use Argon2id.
"""

import hashlib
import hmac
import re

from argon2 import PasswordHasher, Type, extract_parameters
from argon2.exceptions import InvalidHashError, VerificationError

HASHER = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
    salt_len=16,
    hash_len=32,
    type=Type.ID,
)
WRAPPED_MD5 = "sqlbot-md5-argon2id-v1:"
LEGACY_MD5 = re.compile(r"[0-9a-f]{32}")


def is_legacy_password(value: str) -> bool:
    return isinstance(value, str) and LEGACY_MD5.fullmatch(value) is not None


def legacy_md5(password: str) -> str:
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    return HASHER.hash(password)


def wrap_legacy_password(value: str) -> str:
    if not is_legacy_password(value):
        raise ValueError("Expected a legacy local credential")
    return WRAPPED_MD5 + HASHER.hash(value)


def verify_password(password: str, stored: str) -> bool:
    if not isinstance(password, str) or not isinstance(stored, str):
        return False
    if is_legacy_password(stored):
        return hmac.compare_digest(legacy_md5(password), stored)
    wrapped = stored.startswith(WRAPPED_MD5)
    encoded = stored[len(WRAPPED_MD5) :] if wrapped else stored
    if not encoded.startswith("$argon2id$v=19$"):
        return False
    try:
        params = extract_parameters(encoded)
        # Reject corrupt/untrusted encodings before allocating excessive resources.
        if not (
            1 <= params.time_cost <= 10
            and 8 <= params.memory_cost <= 262144
            and 1 <= params.parallelism <= 8
            and 8 <= params.salt_len <= 64
            and 16 <= params.hash_len <= 64
        ):
            return False
        return HASHER.verify(encoded, legacy_md5(password) if wrapped else password)
    except (VerificationError, InvalidHashError, ValueError):
        return False


def needs_password_upgrade(stored: str) -> bool:
    if is_legacy_password(stored) or stored.startswith(WRAPPED_MD5):
        return True
    try:
        return HASHER.check_needs_rehash(stored)
    except (InvalidHashError, ValueError):
        return False
