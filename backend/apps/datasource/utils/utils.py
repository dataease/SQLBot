import base64
import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import unpad

# Historical storage and browser wire format.
_LEGACY_KEY = b"SQLBot1234567890"
_VERSION = "gcm1"
_KEY_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")


class DatasourceKeyError(RuntimeError):
    pass


class DatasourceConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class DatasourceKeys:
    active: str
    keys: dict[str, bytes] = field(repr=False)


def datasource_keys_path() -> Path:
    explicit = os.environ.get("SQLBOT_DATASOURCE_KEYS_FILE")
    if explicit:
        return Path(explicit)
    from common.core.config import settings

    return Path(settings.UPLOAD_DIR) / ".secrets" / "datasource-keys.json"


def initialize_datasource_keys(has_encrypted_configurations: bool) -> DatasourceKeys:
    path = datasource_keys_path()
    if (
        not os.environ.get("SQLBOT_DATASOURCE_KEYS_FILE")
        and not has_encrypted_configurations
    ):
        try:
            if not path.exists():
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                # Publish the complete file atomically. Concurrent starters read
                # the winner's key, and an interrupted write leaves no final file.
                with tempfile.NamedTemporaryFile(dir=path.parent) as pending:
                    document = {
                        "active": "primary",
                        "keys": {
                            "primary": base64.b64encode(get_random_bytes(32)).decode(
                                "ascii"
                            )
                        },
                    }
                    pending.write(json.dumps(document).encode("utf-8"))
                    pending.flush()
                    os.fsync(pending.fileno())
                    try:
                        os.link(pending.name, path)
                    except FileExistsError:
                        pass
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        except OSError:
            raise DatasourceKeyError(
                "Unable to initialize datasource key file"
            ) from None
    return load_datasource_keys()


def load_datasource_keys() -> DatasourceKeys:
    path = datasource_keys_path()
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        active = document["active"]
        keys = {}
        for key_id, encoded in document["keys"].items():
            key = base64.b64decode(encoded, validate=True)
            if not _KEY_ID.fullmatch(key_id) or len(key) != 32:
                raise ValueError
            keys[key_id] = key
        if active not in keys:
            raise ValueError
    except FileNotFoundError:
        raise DatasourceKeyError(
            "Datasource key file is missing. Restore the original key file for encrypted data."
        ) from None
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        raise DatasourceKeyError("Invalid or unreadable datasource key file") from None
    return DatasourceKeys(active, keys)


def decode_legacy_configuration(encrypted_data: str | bytes) -> str:
    try:
        encrypted = base64.b64decode(encrypted_data, validate=True)
        cipher = AES.new(_LEGACY_KEY, AES.MODE_ECB)
        return unpad(cipher.decrypt(encrypted), AES.block_size).decode("utf-8")
    except (ValueError, TypeError):
        raise DatasourceConfigurationError(
            "Invalid legacy datasource configuration"
        ) from None


def aes_encrypt(data: str, keys: DatasourceKeys | None = None) -> bytes:
    keys = keys if keys is not None else load_datasource_keys()
    header = f"{_VERSION}:{keys.active}:".encode("ascii")
    nonce = get_random_bytes(12)
    cipher = AES.new(keys.keys[keys.active], AES.MODE_GCM, nonce=nonce)
    cipher.update(header)
    encrypted, tag = cipher.encrypt_and_digest(data.encode("utf-8"))
    return header + base64.b64encode(nonce + tag + encrypted)


def aes_decrypt(encrypted_data: str | bytes, keys: DatasourceKeys | None = None) -> str:
    try:
        data = (
            encrypted_data.encode("ascii")
            if isinstance(encrypted_data, str)
            else encrypted_data
        )
        version, key_id, payload = data.split(b":", 2)
        key_id = key_id.decode("ascii")
        if version != _VERSION.encode("ascii") or not _KEY_ID.fullmatch(key_id):
            raise ValueError
        raw = base64.b64decode(payload, validate=True)
        if len(raw) < 28:
            raise ValueError
    except (ValueError, AttributeError, TypeError):
        raise DatasourceConfigurationError(
            "Invalid datasource storage format"
        ) from None

    keys = keys if keys is not None else load_datasource_keys()
    if key_id not in keys.keys:
        raise DatasourceKeyError("Datasource storage key is unavailable")
    try:
        cipher = AES.new(keys.keys[key_id], AES.MODE_GCM, nonce=raw[:12])
        cipher.update(f"{_VERSION}:{key_id}:".encode("ascii"))
        return cipher.decrypt_and_verify(raw[28:], raw[12:28]).decode("utf-8")
    except ValueError:
        raise DatasourceConfigurationError(
            "Datasource configuration authentication failed"
        ) from None


def parse_configuration(data: str) -> dict:
    try:
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError
        return value
    except ValueError:
        raise DatasourceConfigurationError("Invalid datasource configuration") from None
