from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def encode_token(payload: dict[str, Any], secret: str, *, ttl_seconds: int = 60 * 60 * 12) -> str:
    body = {**payload, "exp": int(time.time()) + ttl_seconds}
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    middle = _b64url(json.dumps(body, separators=(",", ":")).encode())
    signing = f"{header}.{middle}"
    signature = _b64url(hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest())
    return f"{signing}.{signature}"


def decode_token(token: str, secret: str) -> dict[str, Any]:
    try:
        header_b64, body_b64, signature = token.split(".")
    except ValueError as exc:
        raise ValueError("Malformed token") from exc
    signing = f"{header_b64}.{body_b64}"
    expected = _b64url(hmac.new(secret.encode(), signing.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid signature")
    body = json.loads(_b64url_decode(body_b64))
    if int(body.get("exp") or 0) < int(time.time()):
        raise ValueError("Token expired")
    return body


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)
