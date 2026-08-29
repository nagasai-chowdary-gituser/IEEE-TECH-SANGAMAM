from __future__ import annotations

import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.tokens import encode_token
from app.models.ai_usage import AiAbuseBlock, AiUsageEvent
from app.services.ai.base import AIProviderError
from app.services.ai.rate_limit import minute_limiter
from app.services.ai.ttl_cache import TtlMemoryCache, ask_response_cache
from app.services.ai.usage_context import add_token_usage
from tests.fixtures import png_bytes
from tests.helpers import analyze_and_wait


@pytest.fixture(autouse=True)
def _reset_ai_guard() -> None:
    minute_limiter.reset()
    ask_response_cache.clear()
    db = SessionLocal()
    try:
        db.execute(delete(AiAbuseBlock))
        db.commit()
    finally:
        db.close()
    yield
    minute_limiter.reset()
    ask_response_cache.clear()


def _session_headers(email: str) -> dict[str, str]:
    token = encode_token(
        {"sub": email, "email": email, "role": "user", "name": "Test", "method": "password"},
        "test-auth-secret",
    )
    return {"Authorization": f"Bearer {token}"}


def _ask(client: TestClient, analysis_id: str, question: str, headers: dict | None = None):
    return client.post(
        f"/api/v1/documents/{analysis_id}/ask",
        json={"question": question},
        headers=headers or {},
    )


def test_ttl_cache_hit_miss_expire_and_failure() -> None:
    cache = TtlMemoryCache()
    assert cache.get("a") is None
    cache.set("a", '{"ok": true}', ttl_seconds=1)
    assert cache.get("a") == '{"ok": true}'
    assert cache.stats.hits == 1
    assert cache.stats.misses == 1
    time.sleep(1.05)
    assert cache.get("a") is None
    assert cache.stats.misses == 2

    cache.set("b", "1", ttl_seconds=60)
    cache.record_failure()
    assert cache.stats.failures == 1
    assert cache.stats.stores == 2


def test_ask_openai_usage_and_cache(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    analysis_id = analysis["analysis_id"]
    monkeypatch.setattr(settings, "ai_api_key", "test-key")
    monkeypatch.setattr(settings, "ai_cache_enabled", True)
    monkeypatch.setattr(settings, "ai_cache_ttl_seconds", 3600)
    calls = {"n": 0}

    def fake_complete(*_args, **_kwargs) -> str:
        calls["n"] += 1
        add_token_usage(input_tokens=120, output_tokens=30)
        return json.dumps({"answer": "Metadata timing is the strongest evidence.", "referenced_layers": ["metadata"]})

    with patch("app.services.ai.explanation_service.OpenAICompatibleProvider.complete_json", side_effect=fake_complete):
        first = _ask(client, analysis_id, "What is the strongest evidence?", _session_headers("cache-user@example.com"))
        second = _ask(client, analysis_id, "What is the strongest evidence?", _session_headers("cache-user@example.com"))

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert first.json()["source"] == "ai"
    assert first.json()["answer"] == second.json()["answer"]
    assert calls["n"] == 1

    db = SessionLocal()
    try:
        rows = db.scalars(select(AiUsageEvent).where(AiUsageEvent.subject == "user:cache-user@example.com")).all()
        assert len(rows) == 2
        live = [row for row in rows if not row.cached]
        hit = [row for row in rows if row.cached]
        assert len(live) == 1 and len(hit) == 1
        assert live[0].input_tokens == 120
        assert live[0].output_tokens == 30
        assert live[0].estimated_cost_usd > 0
        assert live[0].success is True
        assert live[0].endpoint == "ask"
        assert "sk-" not in (live[0].error_class or "")
    finally:
        db.close()


def test_cache_failure_still_serves_ask(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    monkeypatch.setattr(settings, "ai_api_key", "test-key")

    def boom(_key: str):
        raise RuntimeError("cache down")

    with (
        patch("app.services.ai.ttl_cache.ask_response_cache.get", side_effect=boom),
        patch(
            "app.services.ai.explanation_service.OpenAICompatibleProvider.complete_json",
            return_value=json.dumps({"answer": "ok", "referenced_layers": []}),
        ),
    ):
        response = _ask(client, analysis["analysis_id"], "Is coverage limited?", _session_headers("failopen@example.com"))
    assert response.status_code == 200, response.text
    assert ask_response_cache.stats.failures >= 1


def test_ip_rate_limit_and_429(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_rate_limit_ip_per_minute", 1)
    monkeypatch.setattr(settings, "ai_cache_enabled", False)
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    analysis_id = analysis["analysis_id"]
    first = _ask(client, analysis_id, "Question one?")
    second = _ask(client, analysis_id, "Question two?")
    assert first.status_code == 200, first.text
    assert second.status_code == 429
    assert second.json()["detail"]
    assert second.headers.get("retry-after")
    db = SessionLocal()
    try:
        limited = db.scalars(select(AiUsageEvent).where(AiUsageEvent.rate_limited.is_(True))).all()
        assert limited
        assert limited[-1].endpoint == "ask"
    finally:
        db.close()


def test_per_user_limits_are_isolated(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_rate_limit_per_minute", 1)
    monkeypatch.setattr(settings, "ai_cache_enabled", False)
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    analysis_id = analysis["analysis_id"]
    user_a = _session_headers("alpha@example.com")
    user_b = _session_headers("beta@example.com")
    assert _ask(client, analysis_id, "A1?", user_a).status_code == 200
    assert _ask(client, analysis_id, "A2?", user_a).status_code == 429
    assert _ask(client, analysis_id, "B1?", user_b).status_code == 200


def test_daily_quota_per_user(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_rate_limit_daily", 1)
    monkeypatch.setattr(settings, "ai_cache_enabled", False)
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    headers = _session_headers("daily@example.com")
    assert _ask(client, analysis["analysis_id"], "First?", headers).status_code == 200
    blocked = _ask(client, analysis["analysis_id"], "Second?", headers)
    assert blocked.status_code == 429
    assert "quota" in blocked.json()["detail"].lower()


def test_repeated_failures_block_source(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_abuse_fail_streak", 2)
    monkeypatch.setattr(settings, "ai_abuse_spike_per_minute", 99)
    monkeypatch.setattr(settings, "ai_cache_enabled", False)
    monkeypatch.setattr(settings, "ai_abuse_block_minutes", 15)
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    analysis_id = analysis["analysis_id"]
    monkeypatch.setattr(settings, "ai_api_key", "test-key")
    headers = _session_headers("fails@example.com")
    with patch(
        "app.services.ai.explanation_service.OpenAICompatibleProvider.complete_json",
        side_effect=AIProviderError("unavailable"),
    ):
        assert _ask(client, analysis_id, "Fail one?", headers).status_code == 200
        assert _ask(client, analysis_id, "Fail two?", headers).status_code == 200
        blocked = _ask(client, analysis_id, "Fail three?", headers)
    assert blocked.status_code == 429
    db = SessionLocal()
    try:
        block = db.scalar(select(AiAbuseBlock).where(AiAbuseBlock.subject == "user:fails@example.com"))
        assert block is not None
        assert "repeated_failures" in block.reason
    finally:
        db.close()


def test_token_spike_block(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_abuse_token_hour", 50)
    monkeypatch.setattr(settings, "ai_abuse_spike_per_minute", 99)
    monkeypatch.setattr(settings, "ai_cache_enabled", False)
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    monkeypatch.setattr(settings, "ai_api_key", "test-key")
    headers = _session_headers("tokens@example.com")

    def fake_complete(*_args, **_kwargs) -> str:
        add_token_usage(input_tokens=80, output_tokens=20)
        return json.dumps({"answer": "limited coverage", "referenced_layers": []})

    with patch("app.services.ai.explanation_service.OpenAICompatibleProvider.complete_json", side_effect=fake_complete):
        assert _ask(client, analysis["analysis_id"], "Token question?", headers).status_code == 200
        blocked = _ask(client, analysis["analysis_id"], "Token question two?", headers)
    assert blocked.status_code == 429


def test_explanation_db_cache_skips_rate_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_rate_limit_ip_per_minute", 1)
    monkeypatch.setattr(settings, "ai_rate_limit_per_minute", 1)
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    first = client.get(f"/api/v1/documents/{analysis['analysis_id']}/explanation")
    second = client.get(f"/api/v1/documents/{analysis['analysis_id']}/explanation")
    assert first.status_code == 200
    assert second.status_code == 200


def test_request_spike_block(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_abuse_spike_per_minute", 2)
    monkeypatch.setattr(settings, "ai_cache_enabled", False)
    analysis = analyze_and_wait(client, "page.png", png_bytes(), "image/png")
    headers = _session_headers("spike@example.com")
    assert _ask(client, analysis["analysis_id"], "S1?", headers).status_code == 200
    assert _ask(client, analysis["analysis_id"], "S2?", headers).status_code == 200
    blocked = _ask(client, analysis["analysis_id"], "S3?", headers)
    assert blocked.status_code == 429
