from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.document_analysis import AnalysisStatus

ComparisonStatus = Literal[
    "REFERENCE_MATCH_HIGH",
    "REFERENCE_MATCH_MODERATE",
    "POTENTIAL_MISMATCH",
    "INCONCLUSIVE",
]
CombinedConcern = Literal["LOW_CONCERN", "REVIEW_REQUIRED", "ELEVATED_CONCERN", "INCONCLUSIVE"]
OriginalityVerdict = Literal["SAFE", "NOT_SAFE", "REVIEW", "UNAVAILABLE"]
OverallVerdict = Literal["SAFE", "NOT_SAFE", "REVIEW"]


class SignatureRegion(BaseModel):
    page_number: int = 1
    x: int
    y: int
    width: int
    height: int
    score: float | None = None
    source: Literal["auto", "manual"] = "auto"
    reason: str | None = None


class SignatureQuality(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    width: int
    height: int
    ink_ratio: float
    sharpness: float
    limitations: list[str] = Field(default_factory=list)


class ComparisonSignals(BaseModel):
    structural_similarity: float | None = None
    contour_similarity: float | None = None
    feature_match_score: float | None = None
    geometry_similarity: float | None = None
    histogram_similarity: float | None = None
    image_quality_score: float | None = None
    region_detection_confidence: float | None = None
    unavailable: list[str] = Field(default_factory=list)


class SignatureFusion(BaseModel):
    overall_status: ComparisonStatus
    similarity_score: int = Field(ge=0, le=100)
    assessment_confidence: float = Field(ge=0.0, le=1.0)
    assessment_summary: str
    recommended_action: str
    limitations: list[str] = Field(default_factory=list)
    signals: ComparisonSignals


class CombinedSignatureAssessment(BaseModel):
    overall_concern: CombinedConcern
    summary: str
    comparison_status: ComparisonStatus
    tamper_level: str | None = None
    final_score: int | None = Field(default=None, ge=0, le=100)
    originality_score: int | None = Field(default=None, ge=0, le=100)
    originality_verdict: OriginalityVerdict | None = None
    overall_verdict: OverallVerdict | None = None


CertificateStatus = Literal[
    "CERTIFICATE_CLEAR",
    "REVIEW_REQUIRED",
    "ELEVATED_CONCERN",
    "HIGH_MANIPULATION_CONCERN",
    "INCONCLUSIVE",
]
ContentStatus = Literal[
    "NO_SIGNIFICANT_MANIPULATION_EVIDENCE",
    "LOW_MANIPULATION_RISK",
    "REVIEW_REQUIRED",
    "ELEVATED_MANIPULATION_RISK",
    "HIGH_MANIPULATION_RISK",
    "INCONCLUSIVE",
]
SignatureIntegrityStatus = Literal[
    "NO_SIGNIFICANT_MANIPULATION_EVIDENCE",
    "LOW_MANIPULATION_RISK",
    "REVIEW_REQUIRED",
    "ELEVATED_MANIPULATION_RISK",
    "HIGH_MANIPULATION_RISK",
    "INCONCLUSIVE",
    "AWAITING_SELECTION",
]
ReferenceDisplayStatus = Literal[
    "HIGH_REFERENCE_MATCH",
    "MODERATE_REFERENCE_MATCH",
    "POTENTIAL_MISMATCH",
    "INCONCLUSIVE",
    "NOT_REQUESTED",
]


class OverlayRegion(BaseModel):
    kind: Literal["text", "copy_move", "compression", "signature", "suspicious"]
    label: str
    page_number: int = 1
    x: int
    y: int
    width: int
    height: int
    score: float | None = None
    explanation: str


class CertificateField(BaseModel):
    field_id: str
    label: str
    value: str
    confidence: float | None = None
    source: str | None = None


class RankedFinding(BaseModel):
    rank: int
    stream: Literal["document", "signature", "reference"]
    finding: str
    strength: Literal["low", "moderate", "high"]


class StreamAssessment(BaseModel):
    status: str
    summary: str
    confidence: float | None = None
    risk_score: int | None = None
    findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class CertificateIntegrityAssessment(BaseModel):
    overall_status: CertificateStatus
    confidence: float = Field(ge=0.0, le=1.0)
    analysis_coverage: float = Field(ge=0.0, le=1.0)
    summary: str
    recommended_action: str
    completed_checks: list[str] = Field(default_factory=list)
    unavailable_checks: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    top_findings: list[RankedFinding] = Field(default_factory=list)
    document_content: StreamAssessment
    signature_integrity: StreamAssessment
    reference_comparison: StreamAssessment | None = None
    extracted_fields: list[CertificateField] = Field(default_factory=list)
    overlay_regions: list[OverlayRegion] = Field(default_factory=list)


class ReferenceSignatureResponse(BaseModel):
    reference_id: str
    label: str | None
    original_filename: str
    file_type: str
    file_size: int
    width: int | None
    height: int | None
    quality_score: float | None
    created_at: datetime


class ReferenceListResponse(BaseModel):
    items: list[ReferenceSignatureResponse]
    total: int


class SignatureComparisonResponse(BaseModel):
    comparison_id: str
    reference_id: str | None = None
    reference_label: str | None = None
    forensic_analysis_id: str | None = None
    status: str
    pipeline_stage: str | None = None
    original_filename: str
    file_type: str | None = None
    file_size: int | None = None
    sha256_short: str | None = None
    candidates: list[SignatureRegion] = Field(default_factory=list)
    selected_region: SignatureRegion | None = None
    document_quality: SignatureQuality | None = None
    reference_quality: SignatureQuality | None = None
    signals: ComparisonSignals | None = None
    fusion: SignatureFusion | None = None
    tamper: dict | None = None
    combined: CombinedSignatureAssessment | None = None
    certificate: CertificateIntegrityAssessment | None = None
    overall_status: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    forensic_status: AnalysisStatus | None = None
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


class SignatureComparisonSummary(BaseModel):
    comparison_id: str
    original_filename: str
    reference_label: str | None
    overall_status: str | None
    certificate_status: str | None = None
    tamper_level: str | None
    final_score: int | None = None
    originality_score: int | None = None
    originality_verdict: OriginalityVerdict | None = None
    overall_verdict: OverallVerdict | None = None
    created_at: datetime


class SignatureComparisonListResponse(BaseModel):
    items: list[SignatureComparisonSummary]
    total: int
    limit: int
    offset: int


class ManualRegionRequest(BaseModel):
    page_number: int = 1
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=4)
    height: int = Field(gt=4)
