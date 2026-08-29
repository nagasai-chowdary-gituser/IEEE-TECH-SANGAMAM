from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

LayerName = Literal["metadata", "ela", "copy_move", "document_intelligence"]
LayerStatus = Literal["available", "limited", "failed", "unavailable"]
RiskLevel = Literal["LOW", "MODERATE", "ELEVATED", "HIGH", "INCONCLUSIVE"]
CorroborationStrength = Literal["none", "weak", "moderate", "strong"]
RecommendedAction = Literal[
    "NO_ADDITIONAL_ACTION",
    "MANUAL_REVIEW_RECOMMENDED",
    "PRIORITY_MANUAL_REVIEW",
    "REANALYZE_WITH_HIGHER_QUALITY_SOURCE",
]
Severity = Literal["low", "medium", "high"]


class NormalizedSignal(BaseModel):
    id: str
    finding: str
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_reference: str | None = None


class NormalizedLayerEvidence(BaseModel):
    layer: LayerName
    raw_score: int = Field(ge=0, le=100)
    normalized_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reliability: float = Field(ge=0.0, le=1.0)
    effective_score: float = Field(ge=0.0, le=100.0)
    evidence_count: int = 0
    strong_evidence_count: int = 0
    status: LayerStatus
    summary: str
    limitations: list[str] = Field(default_factory=list)
    signals: list[NormalizedSignal] = Field(default_factory=list)


class LayerContribution(BaseModel):
    layer: LayerName
    raw_score: int
    reliability: float
    effective_contribution: float
    status: LayerStatus
    summary: str


class CorroborationResult(BaseModel):
    independent_layers_with_evidence: list[LayerName] = Field(default_factory=list)
    strength: CorroborationStrength
    description: str


class TopFinding(BaseModel):
    rank: int
    layer: LayerName
    finding: str
    severity: Severity
    confidence: float
    evidence_reference: str | None = None


class FusionResult(BaseModel):
    layer: str = "fusion"
    overall_risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    assessment_confidence: float = Field(ge=0.0, le=1.0)
    analysis_coverage: float = Field(ge=0.0, le=1.0)
    layer_contributions: list[LayerContribution]
    corroboration: CorroborationResult
    top_findings: list[TopFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    assessment_summary: str
    recommended_action: RecommendedAction
