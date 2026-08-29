from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from fastapi import Header, HTTPException, Query, Request, status

from app.core.config import get_settings
from app.core.tokens import decode_token

DEMO_TOKEN_HEADER = "X-Demo-Token"


@dataclass(frozen=True)
class AiIdentity:
    subject: str
    user_id: str | None
    ip: str
    authenticated: bool


def require_demo_token(
    x_demo_token: str | None = Header(default=None, alias=DEMO_TOKEN_HEADER),
    authorization: str | None = Header(default=None),
    token: str | None = Query(
        default=None,
        description="Same secret as X-Demo-Token, or a session token, for image and download URLs.",
    ),
) -> None:
    settings = get_settings()
    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    session = bearer or (token or "").strip()
    if session and _valid_session(session, settings.auth_secret):
        return
    expected = settings.demo_api_token.strip()
    provided = (x_demo_token or token or "").strip()
    if expected and provided and _tokens_match(provided, expected):
        return
    if not expected and not settings.auth_secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured.",
        )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid demo token.",
    )


def resolve_ai_identity(
    request: Request,
    x_demo_token: str | None = Header(default=None, alias=DEMO_TOKEN_HEADER),
    authorization: str | None = Header(default=None),
    token: str | None = Query(default=None),
) -> AiIdentity:
    ip = _client_ip(request)
    settings = get_settings()
    bearer = ""
    if authorization and authorization.lower().startswith("bearer "):
        bearer = authorization.split(" ", 1)[1].strip()
    session = bearer or (token or "").strip()
    if session:
        try:
            payload = decode_token(session, settings.auth_secret)
        except ValueError:
            payload = {}
        role = payload.get("role")
        if role in {"user", "admin"}:
            user_id = str(payload.get("email") or payload.get("sub") or "").strip()
            if user_id:
                return AiIdentity(subject=f"user:{user_id}", user_id=user_id, ip=ip, authenticated=True)
    return AiIdentity(subject=f"ip:{ip}", user_id=None, ip=ip, authenticated=False)


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _valid_session(raw: str, secret: str) -> bool:
    if not secret.strip():
        return False
    try:
        payload = decode_token(raw, secret)
    except ValueError:
        return False
    return payload.get("role") in {"user", "admin"}


def _tokens_match(provided: str, expected: str) -> bool:
    left = hashlib.sha256(provided.encode("utf-8")).digest()
    right = hashlib.sha256(expected.encode("utf-8")).digest()
    return hmac.compare_digest(left, right)
