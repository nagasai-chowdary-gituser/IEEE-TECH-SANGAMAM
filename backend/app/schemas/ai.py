from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.document_analysis import AnalysisStatus
from app.schemas.fusion import LayerName, RiskLevel

ExplanationSource = Literal["ai", "deterministic_fallback"]


class EvidenceExplanation(BaseModel):
    layer: str
    explanation: str


class AIExplanation(BaseModel):
    summary: str
    risk_explanation: str
    strongest_evidence: list[EvidenceExplanation] = Field(default_factory=list)
    corroboration_explanation: str
    limitations_explanation: str
    recommended_next_step: str
    disclaimer: str = (
        "This assessment is based on available digital forensic evidence and is not "
        "legal proof of forgery or authenticity."
    )
    source: ExplanationSource = "deterministic_fallback"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=800)


class AskGrounding(BaseModel):
    risk_level: RiskLevel | None = None
    referenced_layers: list[LayerName | str] = Field(default_factory=list)


class AskResponse(BaseModel):
    answer: str
    grounding: AskGrounding
    source: ExplanationSource = "deterministic_fallback"


class AnalysisSummaryItem(BaseModel):
    analysis_id: str
    original_filename: str
    document_type: str | None = None
    status: AnalysisStatus
    risk_level: str | None = None
    overall_risk_score: int | None = None
    pipeline_stage: str | None = None
    created_at: datetime


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummaryItem]
    total: int
    limit: int
    offset: int
