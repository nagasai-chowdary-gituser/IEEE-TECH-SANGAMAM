from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.ai_usage import AiAbuseBlock, AiUsageEvent
from app.models.compliance import ComplianceAnalysis
from app.models.document_analysis import DocumentAnalysis
from app.models.signature import SignatureComparison
from app.schemas.admin import (
    AdminOverview,
    AiBlock,
    AiSubjectUsage,
    AiUsageStats,
    AiUsageWindow,
    ModuleStats,
    RecentActivity,
    ServiceConfig,
)

RECENT_LIMIT = 15


def build_overview(db: Session, settings: Settings) -> AdminOverview:
    return AdminOverview(
        forensics=_module_stats(db, DocumentAnalysis, DocumentAnalysis.risk_level),
        compliance=_module_stats(db, ComplianceAnalysis, ComplianceAnalysis.overall_status),
        certificates=_module_stats(db, SignatureComparison, SignatureComparison.overall_status),
        ai_usage=_ai_usage(db),
        recent_activity=_recent_activity(db),
        services=_services(settings),
    )


def unblock(db: Session, block_id: str) -> None:
    row = db.get(AiAbuseBlock, block_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Block not found.")
    db.delete(row)
    db.commit()


def _status_text(value: object) -> str:
    return str(getattr(value, "value", value))


def _module_stats(db: Session, model, outcome_column) -> ModuleStats:
    by_status = {
        _status_text(value): int(count)
        for value, count in db.execute(select(model.status, func.count()).group_by(model.status)).all()
    }
    by_outcome = {
        str(value): int(count)
        for value, count in db.execute(
            select(outcome_column, func.count()).where(outcome_column.is_not(None)).group_by(outcome_column)
        ).all()
    }
    return ModuleStats(total=sum(by_status.values()), by_status=by_status, by_outcome=by_outcome)


def _naive_utc_now() -> datetime:
    # Usage timestamps are compared as naive UTC, matching usage_service.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _usage_window(db: Session, since: datetime | None) -> AiUsageWindow:
    conditions = [] if since is None else [AiUsageEvent.created_at >= since]
    rows = db.execute(
        select(
            AiUsageEvent.cached,
            AiUsageEvent.rate_limited,
            AiUsageEvent.success,
            AiUsageEvent.input_tokens,
            AiUsageEvent.output_tokens,
            AiUsageEvent.estimated_cost_usd,
        ).where(*conditions)
    ).all()
    return AiUsageWindow(
        calls=len(rows),
        cached=sum(1 for row in rows if row.cached),
        rate_limited=sum(1 for row in rows if row.rate_limited),
        failures=sum(1 for row in rows if not row.success),
        input_tokens=sum(row.input_tokens for row in rows),
        output_tokens=sum(row.output_tokens for row in rows),
        estimated_cost_usd=round(sum(row.estimated_cost_usd for row in rows), 6),
    )


def _ai_usage(db: Session) -> AiUsageStats:
    now = _naive_utc_now()
    since = now - timedelta(hours=24)
    top = db.execute(
        select(
            AiUsageEvent.subject,
            func.count(),
            func.sum(AiUsageEvent.input_tokens + AiUsageEvent.output_tokens),
            func.sum(AiUsageEvent.estimated_cost_usd),
        )
        .where(AiUsageEvent.created_at >= since)
        .group_by(AiUsageEvent.subject)
        .order_by(func.count().desc())
        .limit(10)
    ).all()
    blocks = []
    for row in db.scalars(select(AiAbuseBlock).order_by(AiAbuseBlock.blocked_until.desc())).all():
        until = row.blocked_until
        if until.tzinfo is not None:
            until = until.astimezone(timezone.utc).replace(tzinfo=None)
        if until > now:
            blocks.append(AiBlock(id=row.id, subject=row.subject, reason=row.reason, blocked_until=until))
    return AiUsageStats(
        last_24h=_usage_window(db, since),
        all_time=_usage_window(db, None),
        top_subjects_24h=[
            AiSubjectUsage(
                subject=subject,
                calls=int(calls),
                tokens=int(tokens or 0),
                estimated_cost_usd=round(float(cost or 0.0), 6),
            )
            for subject, calls, tokens, cost in top
        ],
        active_blocks=blocks,
    )


def _recent_activity(db: Session) -> list[RecentActivity]:
    items: list[RecentActivity] = []
    sources = (
        ("forensics", DocumentAnalysis, DocumentAnalysis.risk_level),
        ("compliance", ComplianceAnalysis, ComplianceAnalysis.overall_status),
        ("certificate", SignatureComparison, SignatureComparison.overall_status),
    )
    for module, model, outcome_column in sources:
        rows = db.execute(
            select(model.id, model.original_filename, model.status, outcome_column, model.created_at)
            .order_by(model.created_at.desc())
            .limit(RECENT_LIMIT)
        ).all()
        items.extend(
            RecentActivity(
                module=module,
                id=row[0],
                original_filename=row[1],
                status=_status_text(row[2]),
                outcome=row[3],
                created_at=row[4],
            )
            for row in rows
        )
    items.sort(key=lambda item: _sortable(item.created_at), reverse=True)
    return items[:RECENT_LIMIT]


def _sortable(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _services(settings: Settings) -> ServiceConfig:
    return ServiceConfig(
        ai_explanations=bool(settings.ai_api_key.strip()) and settings.ai_provider.strip().lower() != "none",
        pan_verification=bool(settings.pan_api_key.strip() and settings.pan_api_secret.strip()),
        gst_verification=bool(settings.gst_in_check.strip()),
        google_sign_in=bool(settings.google_client_id.strip() and settings.google_client_secret.strip()),
        google_admin_emails=len(settings.admin_email_list),
        default_passwords_in_use=settings.auth_user_password == "user123" or settings.auth_admin_password == "admin123",
    )
