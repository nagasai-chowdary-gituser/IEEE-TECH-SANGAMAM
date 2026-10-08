from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.ai_usage import AiAbuseBlock
from app.services.auth_google import google_role


def _login(client: TestClient, username: str, password: str, role: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password, "role": role})
    assert response.status_code == 200
    return response.json()["token"]


def test_admin_overview_requires_admin_session(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/api/v1/admin/overview").status_code == 401
    demo = anonymous_client.get("/api/v1/admin/overview", headers={"X-Demo-Token": "test-demo-token"})
    assert demo.status_code == 401
    user_token = _login(anonymous_client, "user", "user123", "user")
    as_user = anonymous_client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {user_token}"})
    assert as_user.status_code == 403


def test_admin_overview_returns_platform_stats(anonymous_client: TestClient) -> None:
    token = _login(anonymous_client, "admin", "admin123", "admin")
    response = anonymous_client.get("/api/v1/admin/overview", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    for module in ("forensics", "compliance", "certificates"):
        assert body[module]["total"] == sum(body[module]["by_status"].values())
    assert {"last_24h", "all_time", "top_subjects_24h", "active_blocks"} <= body["ai_usage"].keys()
    assert body["services"]["default_passwords_in_use"] is True  # conftest uses the demo passwords
    assert isinstance(body["recent_activity"], list)


def test_admin_can_remove_ai_block(anonymous_client: TestClient) -> None:
    with SessionLocal() as db:
        block = AiAbuseBlock(
            subject="ip:203.0.113.9",
            reason="spike",
            blocked_until=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30),
        )
        db.add(block)
        db.commit()
        block_id = block.id
    headers = {"Authorization": f"Bearer {_login(anonymous_client, 'admin', 'admin123', 'admin')}"}
    overview = anonymous_client.get("/api/v1/admin/overview", headers=headers).json()
    assert block_id in {item["id"] for item in overview["ai_usage"]["active_blocks"]}
    assert anonymous_client.delete(f"/api/v1/admin/ai-blocks/{block_id}", headers=headers).status_code == 200
    assert anonymous_client.delete(f"/api/v1/admin/ai-blocks/{block_id}", headers=headers).status_code == 404


def test_google_admin_requires_allowlisted_email() -> None:
    settings = get_settings().model_copy(update={"auth_admin_emails": "Owner@Example.com"})
    assert google_role(settings, "admin", "owner@example.com") == "admin"
    assert google_role(settings, "user", "someone@example.com") == "user"
    with pytest.raises(HTTPException) as excinfo:
        google_role(settings, "admin", "someone@example.com")
    assert excinfo.value.status_code == 403
