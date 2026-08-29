from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.document_analysis import AnalysisStatus

IdentifierKind = Literal["pan", "gstin"]
FormatStatus = Literal["valid", "invalid", "not_extracted"]
VerificationOutcome = Literal[
    "not_extracted",
    "format_invalid",
    "skipped",
    "passed",
    "failed",
    "unavailable",
    "error",
]
IntegrityLevel = Literal[
    "NO_MEANINGFUL_TAMPER_EVIDENCE",
    "LOW_MANIPULATION_RISK",
    "MODERATE_MANIPULATION_RISK",
    "ELEVATED_MANIPULATION_RISK",
    "HIGH_MANIPULATION_RISK",
    "INCONCLUSIVE",
    "UNAVAILABLE",
]
OverallCompliance = Literal["COMPLIANT", "REVIEW_REQUIRED", "HIGH_RISK", "INCONCLUSIVE"]


class ExtractedIdentifier(BaseModel):
    kind: IdentifierKind
    value: str | None = None
    format_status: FormatStatus
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_page: int | None = None
    snippet: str | None = None


class CertificateFields(BaseModel):
    pan: ExtractedIdentifier
    gstin: ExtractedIdentifier
    udyam_number: str | None = None
    enterprise_name: str | None = None
    registration_date: str | None = None
    limitations: list[str] = Field(default_factory=list)


class IdentifierVerification(BaseModel):
    kind: IdentifierKind
    extracted_value: str | None = None
    format_status: FormatStatus
    outcome: VerificationOutcome
    provider_status: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    verified_at: datetime | None = None
    limitation: str | None = None


class IntegrityAssessment(BaseModel):
    level: IntegrityLevel
    forensic_risk_level: str | None = None
    overall_risk_score: int | None = None
    assessment_confidence: float | None = None
    analysis_coverage: float | None = None
    forensic_analysis_id: str | None = None
    top_findings: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    summary: str


class ComplianceAggregation(BaseModel):
    overall_status: OverallCompliance
    compliance_risk_score: int = Field(ge=0, le=100)
    assessment_summary: str
    recommended_action: str
    limitations: list[str] = Field(default_factory=list)
    pan: IdentifierVerification
    gstin: IdentifierVerification
    integrity: IntegrityAssessment


class ComplianceResponse(BaseModel):
    compliance_id: str
    forensic_analysis_id: str | None = None
    status: str
    pipeline_stage: str | None = None
    original_filename: str
    file_type: str | None = None
    file_size: int | None = None
    sha256_short: str | None = None
    certificate_fields: CertificateFields | None = None
    pan: IdentifierVerification | None = None
    gstin: IdentifierVerification | None = None
    integrity: IntegrityAssessment | None = None
    aggregation: ComplianceAggregation | None = None
    overall_status: OverallCompliance | None = None
    compliance_risk_score: int | None = None
    forensic_status: AnalysisStatus | None = None
    created_at: datetime
    updated_at: datetime
    error_message: str | None = None


class ComplianceSummaryItem(BaseModel):
    compliance_id: str
    original_filename: str
    enterprise_name: str | None = None
    overall_status: str | None = None
    pan_outcome: str | None = None
    gstin_outcome: str | None = None
    integrity_level: str | None = None
    created_at: datetime


class ComplianceListResponse(BaseModel):
    items: list[ComplianceSummaryItem]
    total: int
    limit: int
    offset: int
