from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ModuleStats(BaseModel):
    total: int
    by_status: dict[str, int]
    by_outcome: dict[str, int]


class AiUsageWindow(BaseModel):
    calls: int
    cached: int
    rate_limited: int
    failures: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float


class AiSubjectUsage(BaseModel):
    subject: str
    calls: int
    tokens: int
    estimated_cost_usd: float


class AiBlock(BaseModel):
    id: str
    subject: str
    reason: str
    blocked_until: datetime


class AiUsageStats(BaseModel):
    last_24h: AiUsageWindow
    all_time: AiUsageWindow
    top_subjects_24h: list[AiSubjectUsage]
    active_blocks: list[AiBlock]


class RecentActivity(BaseModel):
    module: Literal["forensics", "compliance", "certificate"]
    id: str
    original_filename: str
    status: str
    outcome: str | None
    created_at: datetime


class ServiceConfig(BaseModel):
    ai_explanations: bool
    pan_verification: bool
    gst_verification: bool
    google_sign_in: bool
    google_admin_emails: int
    default_passwords_in_use: bool


class AdminOverview(BaseModel):
    forensics: ModuleStats
    compliance: ModuleStats
    certificates: ModuleStats
    ai_usage: AiUsageStats
    recent_activity: list[RecentActivity]
    services: ServiceConfig
