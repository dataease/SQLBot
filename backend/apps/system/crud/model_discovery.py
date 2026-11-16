"""Bounded, administrator initiated OpenAI-compatible model discovery."""

import asyncio
import json
from urllib.parse import urlsplit, urlunsplit

import httpx

MAX_BYTES = 1024 * 1024
MAX_MODELS = 2000


class ModelDiscoveryError(Exception):
    """Only a safe classification crosses the HTTP boundary."""


def models_url(base: str) -> str:
    try:
        parts = urlsplit(base)
        if (
            parts.scheme not in ("http", "https")
            or not parts.hostname
            or parts.username is not None
            or parts.password is not None
            or parts.query
            or parts.fragment
            or "\\" in base
            or any(c.isspace() or ord(c) < 32 for c in base)
        ):
            raise ValueError
        _ = parts.port
        return urlunsplit(
            (parts.scheme, parts.netloc, parts.path.rstrip("/") + "/models", "", "")
        )
    except ValueError:
        raise ModelDiscoveryError("address") from None


async def discover_models(base: str, key: str) -> list[str]:
    url = models_url(base)
    if len(key) > 16384 or any(ord(c) < 32 or ord(c) > 126 for c in key):
        raise ModelDiscoveryError("credentials")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    try:
        async with asyncio.timeout(10):
            async with httpx.AsyncClient(
                follow_redirects=False, trust_env=False, timeout=10
            ) as client:
                async with client.stream("GET", url, headers=headers) as response:
                    if response.status_code in (401, 403):
                        raise ModelDiscoveryError("credentials")
                    if response.status_code in (404, 405, 501):
                        raise ModelDiscoveryError("unsupported")
                    if response.status_code != 200:
                        raise ModelDiscoveryError("failed")
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=65536):
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            raise ModelDiscoveryError("invalid")
        payload = json.loads(body)
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or len(rows) > MAX_MODELS:
            raise ModelDiscoveryError("invalid")
        result = []
        for row in rows:
            model_id = row.get("id") if isinstance(row, dict) else None
            if (
                not isinstance(model_id, str)
                or not model_id.strip()
                or len(model_id) > 255
                or any(ord(c) < 32 for c in model_id)
                or (key and key in model_id)
            ):
                raise ModelDiscoveryError("invalid")
            if model_id not in result:
                result.append(model_id)
        return result
    except (TimeoutError, httpx.TimeoutException):
        raise ModelDiscoveryError("timeout") from None
    except (httpx.HTTPError, httpx.InvalidURL, ValueError):
        raise ModelDiscoveryError("failed") from None
