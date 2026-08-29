import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PARTIAL_COMPLETE = "PARTIAL_COMPLETE"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    document_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[AnalysisStatus] = mapped_column(
        Enum(
            AnalysisStatus,
            name="analysis_status",
            native_enum=False,
            values_callable=lambda items: [item.value for item in items],
        ),
        nullable=False,
        default=AnalysisStatus.PENDING,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    metadata_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preprocessing_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ela_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_move_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_forensics_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_intelligence_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fusion_result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    overall_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assessment_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    analysis_coverage: Mapped[float | None] = mapped_column(Float, nullable=True)
    pipeline_stage: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_explanation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_explanation_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    final_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    final_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
