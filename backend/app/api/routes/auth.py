from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.config import Settings, get_settings
from app.core.tokens import decode_token
from app.services.auth_google import (
    exchange_google_code,
    google_start_url,
    issue_session,
    parse_oauth_state,
    verify_password,
)

router = APIRouter()


class PasswordLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    role: str = Field(pattern="^(user|admin)$")


class SessionResponse(BaseModel):
    token: str
    role: str
    name: str
    email: str
    method: str


@router.post("/auth/login", response_model=SessionResponse)
def password_login(payload: PasswordLoginRequest, settings: Settings = Depends(get_settings)) -> SessionResponse:
    account = verify_password(settings, payload.username.strip(), payload.password, payload.role)
    token = issue_session(
        settings,
        role=account["role"],
        name=account["name"],
        email=account["email"],
        method="password",
    )
    return SessionResponse(
        token=token,
        role=account["role"],
        name=account["name"],
        email=account["email"],
        method="password",
    )


@router.get("/auth/google/url")
def google_auth_url(
    role: str = Query(default="user"),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    if role not in {"user", "admin"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")
    return {"url": google_start_url(settings, role)}


@router.get("/auth/google/start")
def google_start(
    role: str = Query(default="user"),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    if role not in {"user", "admin"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role.")
    return RedirectResponse(google_start_url(settings, role), status_code=status.HTTP_302_FOUND)


@router.get("/auth/google/complete", response_model=SessionResponse)
def google_complete(
    code: str = Query(...),
    state: str = Query(...),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    role = parse_oauth_state(settings, state)
    profile = exchange_google_code(settings, code)
    email = str(profile.get("email") or "").strip()
    name = str(profile.get("name") or email or "Google user")
    if not email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google did not return an email.")
    token = issue_session(settings, role=role, name=name, email=email, method="google")
    return SessionResponse(token=token, role=role, name=name, email=email, method="google")


@router.get("/auth/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    frontend = settings.frontend_origin.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{frontend}/?auth_error=google", status_code=status.HTTP_302_FOUND)
    role = parse_oauth_state(settings, state)
    profile = exchange_google_code(settings, code)
    email = str(profile.get("email") or "").strip()
    name = str(profile.get("name") or email or "Google user")
    if not email:
        return RedirectResponse(f"{frontend}/?auth_error=google", status_code=status.HTTP_302_FOUND)
    token = issue_session(settings, role=role, name=name, email=email, method="google")
    return RedirectResponse(f"{frontend}/auth/callback?token={quote(token)}", status_code=status.HTTP_302_FOUND)


@router.get("/auth/me", response_model=SessionResponse)
def auth_me(
    authorization: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> SessionResponse:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in.")
    raw = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(raw, settings.auth_secret)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not signed in.") from exc
    return SessionResponse(
        token=raw,
        role=str(payload.get("role") or "user"),
        name=str(payload.get("name") or ""),
        email=str(payload.get("email") or ""),
        method=str(payload.get("method") or "google"),
    )
