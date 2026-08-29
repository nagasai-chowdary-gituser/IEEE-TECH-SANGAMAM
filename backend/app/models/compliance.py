from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ComplianceStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ComplianceAnalysis(Base):
    __tablename__ = "compliance_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    forensic_analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=ComplianceStatus.PENDING.value)
    pipeline_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extracted_fields_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    pan_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    gst_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    integrity_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    aggregation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    compliance_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enterprise_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
