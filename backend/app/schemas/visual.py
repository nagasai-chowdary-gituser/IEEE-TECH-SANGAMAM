from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import Severity
from app.schemas.metadata import MetadataSignal

AnalysisQuality = Literal["high", "medium", "limited"]
EvidenceStrength = Literal["low", "medium", "high"]

PIPELINE_MESSAGE = (
    "Multi-layer forensic analysis complete. The overall result is a manipulation "
    "risk assessment based on available digital evidence, not a legal authenticity verdict."
)
LAYERS_COMPLETED_MESSAGE = (
    "Analysis layers completed: Metadata, Visual Forensics, Document Intelligence, Evidence Fusion."
)


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class ForensicEvidence(BaseModel):
    type: str
    artifact_id: str
    description: str


class ElaPageMetrics(BaseModel):
    mean_error: float
    std_error: float
    max_error: float
    high_error_ratio: float


class ElaPageResult(BaseModel):
    page_number: int
    suspicion_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    flagged: bool
    metrics: ElaPageMetrics
    evidence: list[ForensicEvidence] = Field(default_factory=list)
    signals: list[MetadataSignal] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ElaForensicsResult(BaseModel):
    layer: str = "ela"
    suspicion_score: int = Field(ge=0, le=100)
    flagged: bool
    confidence: float = Field(ge=0.0, le=1.0)
    analysis_quality: AnalysisQuality
    pages: list[ElaPageResult] = Field(default_factory=list)
    summary: str
    module_error: str | None = None


class CopyMovePageMetrics(BaseModel):
    keypoints_detected: int
    raw_matches: int
    filtered_matches: int
    geometrically_verified_matches: int
    suspicious_clusters: int


class CopyMoveRegion(BaseModel):
    region_id: str
    source_bbox: BoundingBox
    matched_bbox: BoundingBox
    match_confidence: float = Field(ge=0.0, le=1.0)
    evidence_strength: EvidenceStrength


class CopyMovePageResult(BaseModel):
    page_number: int
    suspicion_score: int = Field(ge=0, le=100)
    confidence: float = Field(ge=0.0, le=1.0)
    flagged: bool
    metrics: CopyMovePageMetrics
    regions: list[CopyMoveRegion] = Field(default_factory=list)
    evidence: list[ForensicEvidence] = Field(default_factory=list)
    signals: list[MetadataSignal] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CopyMoveForensicsResult(BaseModel):
    layer: str = "copy_move"
    suspicion_score: int = Field(ge=0, le=100)
    flagged: bool
    confidence: float = Field(ge=0.0, le=1.0)
    pages: list[CopyMovePageResult] = Field(default_factory=list)
    summary: str
    module_error: str | None = None


class VisualForensicsResult(BaseModel):
    layer: str = "visual"
    ela: ElaForensicsResult | None = None
    copy_move: CopyMoveForensicsResult | None = None
    pipeline_message: str = PIPELINE_MESSAGE
