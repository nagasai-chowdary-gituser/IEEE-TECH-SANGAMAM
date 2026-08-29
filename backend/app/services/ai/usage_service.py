from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import get_logger
from app.models.ai_usage import AiAbuseBlock, AiUsageEvent
from app.services.ai.rate_limit import raise_too_many_requests
from app.services.ai.usage_context import TokenUsage

logger = get_logger(__name__)
ALERT_PREFIX = "AI_ABUSE_ALERT"


def record_usage_event(
    db: Session,
    *,
    subject: str,
    ip: str,
    endpoint: str,
    model: str,
    success: bool,
    cached: bool,
    rate_limited: bool,
    usage: TokenUsage,
    estimated_cost_usd: float,
    error_class: str | None = None,
) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    event = AiUsageEvent(
        created_at=now,
        subject=subject,
        ip=ip[:64],
        endpoint=endpoint,
        model=model[:64],
        success=success,
        cached=cached,
        rate_limited=rate_limited,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        estimated_cost_usd=estimated_cost_usd,
        error_class=error_class,
    )
    db.add(event)
    db.commit()


def estimate_cost_usd(settings: Settings, usage: TokenUsage) -> float:
    return round(
        (usage.input_tokens / 1000.0) * settings.ai_usd_per_1k_input
        + (usage.output_tokens / 1000.0) * settings.ai_usd_per_1k_output,
        8,
    )


def enforce_daily_quota(db: Session, *, subject: str, settings: Settings) -> None:
    if settings.ai_rate_limit_daily <= 0:
        return
    start = datetime.now(timezone.utc).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
    count = db.scalar(
        select(func.count()).select_from(AiUsageEvent).where(
            AiUsageEvent.subject == subject,
            AiUsageEvent.created_at >= start,
            AiUsageEvent.cached.is_(False),
            AiUsageEvent.rate_limited.is_(False),
        )
    )
    if int(count or 0) >= settings.ai_rate_limit_daily:
        midnight = start + timedelta(days=1)
        retry = max(1, int((midnight - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds()))
        raise_too_many_requests(retry, daily=True)


def enforce_not_blocked(db: Session, *, subject: str) -> None:
    row = db.scalar(select(AiAbuseBlock).where(AiAbuseBlock.subject == subject))
    if row is None:
        return
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    until = row.blocked_until
    if until.tzinfo is not None:
        until = until.astimezone(timezone.utc).replace(tzinfo=None)
    if until <= now:
        db.delete(row)
        db.commit()
        return
    retry = max(1, int((until - now).total_seconds()))
    raise_too_many_requests(retry)


def evaluate_abuse(
    db: Session,
    *,
    subject: str,
    ip: str,
    settings: Settings,
    usage: TokenUsage,
    success: bool,
    cached: bool,
) -> None:
    if cached:
        return
    reasons: list[str] = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    minute_ago = now - timedelta(minutes=1)
    hour_ago = now - timedelta(hours=1)

    recent = db.scalars(
        select(AiUsageEvent).where(
            AiUsageEvent.subject == subject,
            AiUsageEvent.created_at >= minute_ago,
            AiUsageEvent.cached.is_(False),
        )
    ).all()
    if settings.ai_abuse_spike_per_minute > 0 and len(recent) >= settings.ai_abuse_spike_per_minute:
        reasons.append("request_spike")

    fails = db.scalars(
        select(AiUsageEvent)
        .where(AiUsageEvent.subject == subject, AiUsageEvent.cached.is_(False))
        .order_by(AiUsageEvent.created_at.desc())
        .limit(max(1, settings.ai_abuse_fail_streak))
    ).all()
    if (
        settings.ai_abuse_fail_streak > 0
        and len(fails) >= settings.ai_abuse_fail_streak
        and all(not item.success for item in fails)
    ):
        reasons.append("repeated_failures")

    token_sum = db.scalar(
        select(func.coalesce(func.sum(AiUsageEvent.input_tokens + AiUsageEvent.output_tokens), 0)).where(
            AiUsageEvent.subject == subject,
            AiUsageEvent.created_at >= hour_ago,
        )
    )
    if settings.ai_abuse_token_hour > 0 and int(token_sum or 0) >= settings.ai_abuse_token_hour:
        reasons.append("token_spike")

    if not reasons:
        return
    reason = ",".join(reasons)
    until = now + timedelta(minutes=max(1, settings.ai_abuse_block_minutes))
    existing = db.scalar(select(AiAbuseBlock).where(AiAbuseBlock.subject == subject))
    if existing:
        existing.reason = reason
        existing.blocked_until = until
    else:
        db.add(AiAbuseBlock(subject=subject, reason=reason, blocked_until=until, created_at=now))
    db.commit()
    logger.warning(
        "%s subject=%s ip=%s reason=%s blocked_until=%s success=%s tokens=%s",
        ALERT_PREFIX,
        subject,
        ip,
        reason,
        until.isoformat(),
        success,
        usage.input_tokens + usage.output_tokens,
    )
