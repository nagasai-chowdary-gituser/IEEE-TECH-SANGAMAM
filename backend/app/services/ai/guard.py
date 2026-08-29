from __future__ import annotations

import hashlib
import json

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.document_analysis import DocumentAnalysis
from app.schemas.ai import AskResponse
from app.schemas.fusion import FusionResult
from app.services.ai.prompts import PROMPT_VERSION
from app.services.ai.rate_limit import enforce_minute_limit
from app.services.ai.ttl_cache import ask_response_cache
from app.services.ai.usage_context import TokenUsage, consume_provider_failed, consume_token_usage, reset_ai_call_stats
from app.services.ai.usage_service import (
    enforce_daily_quota,
    enforce_not_blocked,
    estimate_cost_usd,
    evaluate_abuse,
    record_usage_event,
)

logger = get_logger(__name__)


def ask_cache_key(
    *,
    analysis: DocumentAnalysis,
    question: str,
    model: str,
) -> str:
    payload = {
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "analysis_id": analysis.id,
        "fusion_sha256": hashlib.sha256((record_text(analysis.fusion_result_json)).encode("utf-8")).hexdigest(),
        "question": question,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"ask:{digest}"


def record_text(value: str | None) -> str:
    return value or ""


def prepare_ai_request(db: Session, *, subject: str, ip: str, authenticated: bool, settings: Settings) -> None:
    enforce_not_blocked(db, subject=subject)
    enforce_minute_limit(subject=subject, ip=ip, authenticated=authenticated, settings=settings)
    enforce_daily_quota(db, subject=subject, settings=settings)


def try_cached_ask(key: str, *, enabled: bool) -> AskResponse | None:
    if not enabled:
        return None
    try:
        raw = ask_response_cache.get(key)
    except Exception:
        ask_response_cache.record_failure()
        logger.warning("ai_cache_get_failed")
        return None
    if not raw:
        return None
    try:
        return AskResponse.model_validate_json(raw)
    except Exception:
        ask_response_cache.record_failure()
        logger.warning("ai_cache_poison_ignored")
        return None


def store_cached_ask(key: str, response: AskResponse, *, ttl_seconds: int, enabled: bool) -> None:
    if not enabled or ttl_seconds <= 0:
        return
    try:
        ask_response_cache.set(key, response.model_dump_json(), ttl_seconds)
    except Exception:
        ask_response_cache.record_failure()
        logger.warning("ai_cache_set_failed")


def finish_ai_call(
    db: Session,
    *,
    subject: str,
    ip: str,
    endpoint: str,
    settings: Settings,
    cached: bool,
    rate_limited: bool,
    error_class: str | None = None,
    success_override: bool | None = None,
) -> TokenUsage:
    usage = TokenUsage() if cached else consume_token_usage()
    provider_failed = False if cached else consume_provider_failed()
    if cached:
        success = True
    elif rate_limited:
        success = False
    elif success_override is not None:
        success = success_override
    else:
        success = not provider_failed
    cost = 0.0 if cached or rate_limited else estimate_cost_usd(settings, usage)
    record_usage_event(
        db,
        subject=subject,
        ip=ip,
        endpoint=endpoint,
        model=settings.ai_model,
        success=success,
        cached=cached,
        rate_limited=rate_limited,
        usage=usage,
        estimated_cost_usd=cost,
        error_class=error_class,
    )
    if not rate_limited:
        evaluate_abuse(
            db,
            subject=subject,
            ip=ip,
            settings=settings,
            usage=usage,
            success=success,
            cached=cached,
        )
    return usage


def start_provider_call() -> None:
    reset_ai_call_stats()
