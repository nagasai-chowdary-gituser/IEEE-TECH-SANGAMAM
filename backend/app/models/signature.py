from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SignatureComparisonStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    NEEDS_REGION = "NEEDS_REGION"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class ReferenceSignature(Base):
    __tablename__ = "reference_signatures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(16), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ink_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    preprocessing_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SignatureComparison(Base):
    __tablename__ = "signature_comparisons"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reference_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    forensic_analysis_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=SignatureComparisonStatus.PENDING.value)
    pipeline_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidates_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_region_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_quality_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparison_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fusion_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tamper_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    combined_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    page_preview_artifact: Mapped[str | None] = mapped_column(String(128), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
