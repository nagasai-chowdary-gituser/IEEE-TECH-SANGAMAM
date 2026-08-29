from __future__ import annotations

import hmac
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status

from app.core.config import Settings
from app.core.tokens import decode_token, encode_token

GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO = "https://www.googleapis.com/oauth2/v3/userinfo"


def google_start_url(settings: Settings, role: str) -> str:
    _require_google(settings)
    state = encode_token({"purpose": "google_oauth", "role": role}, settings.auth_secret, ttl_seconds=600)
    params = {
        "client_id": settings.google_client_id.strip(),
        "redirect_uri": settings.google_redirect_uri.strip(),
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH}?{urlencode(params)}"


def parse_oauth_state(settings: Settings, state: str) -> str:
    try:
        payload = decode_token(state, settings.auth_secret)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Google sign-in state.") from exc
    if payload.get("purpose") != "google_oauth":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Google sign-in state.")
    role = str(payload.get("role") or "user")
    if role not in {"user", "admin"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")
    return role


def exchange_google_code(settings: Settings, code: str) -> dict[str, Any]:
    _require_google(settings)
    try:
        with httpx.Client(timeout=20.0) as client:
            token_response = client.post(
                GOOGLE_TOKEN,
                data={
                    "code": code,
                    "client_id": settings.google_client_id.strip(),
                    "client_secret": settings.google_client_secret.strip(),
                    "redirect_uri": settings.google_redirect_uri.strip(),
                    "grant_type": "authorization_code",
                },
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            tokens = token_response.json()
            access = tokens.get("access_token")
            if not isinstance(access, str) or not access:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google did not return an access token.")
            profile = client.get(
                GOOGLE_USERINFO,
                headers={"Authorization": f"Bearer {access}", "Accept": "application/json"},
            )
            profile.raise_for_status()
            return profile.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google sign-in could not be completed.",
        ) from exc


def issue_session(settings: Settings, *, role: str, name: str, email: str, method: str) -> str:
    return encode_token(
        {
            "sub": email or name,
            "role": role,
            "name": name,
            "email": email,
            "method": method,
        },
        settings.auth_secret,
    )


def verify_password(settings: Settings, username: str, password: str, role: str) -> dict[str, str]:
    if role == "admin":
        expected_user = settings.auth_admin_username.strip()
        expected_pass = settings.auth_admin_password
    else:
        expected_user = settings.auth_user_username.strip()
        expected_pass = settings.auth_user_password
    if not expected_user or not expected_pass:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Password login is not configured.")
    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    pass_ok = hmac.compare_digest(password.encode(), expected_pass.encode())
    if not (user_ok and pass_ok):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password.")
    return {"username": expected_user, "role": role, "name": expected_user, "email": ""}


def _require_google(settings: Settings) -> None:
    if not settings.google_client_id.strip() or not settings.google_client_secret.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google sign-in is not configured.",
        )
