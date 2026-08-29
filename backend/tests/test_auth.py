from __future__ import annotations

from fastapi.testclient import TestClient


def test_health_does_not_require_demo_token(anonymous_client: TestClient) -> None:
    response = anonymous_client.get("/api/v1/health")
    assert response.status_code == 200


def test_protected_routes_reject_missing_token(anonymous_client: TestClient) -> None:
    listing = anonymous_client.get("/api/v1/documents")
    assert listing.status_code == 401
    compliance = anonymous_client.get("/api/v1/compliance")
    assert compliance.status_code == 401
    signatures = anonymous_client.get("/api/v1/signatures/references")
    assert signatures.status_code == 401


def test_password_login_issues_session(anonymous_client: TestClient) -> None:
    denied = anonymous_client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "wrong", "role": "user"},
    )
    assert denied.status_code == 401
    ok = anonymous_client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "user123", "role": "user"},
    )
    assert ok.status_code == 200
    token = ok.json()["token"]
    me = anonymous_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "user"
    listing = anonymous_client.get("/api/v1/documents", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200


def test_artifact_url_accepts_query_token(client: TestClient, anonymous_client: TestClient) -> None:
    from tests.fixtures import png_bytes
    from tests.helpers import analyze_and_wait

    body = analyze_and_wait(client, "auth.png", png_bytes(), "image/png")
    artifact_id = body["ela"]["pages"][0]["evidence"][0]["artifact_id"]
    path = f"/api/v1/documents/{body['analysis_id']}/artifacts/{artifact_id}"
    denied = anonymous_client.get(path)
    assert denied.status_code == 401
    allowed = anonymous_client.get(path, params={"token": "test-demo-token"})
    assert allowed.status_code == 200
