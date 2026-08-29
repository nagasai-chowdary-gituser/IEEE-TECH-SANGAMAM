from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.visual import BoundingBox

ExtractionQuality = Literal["high", "medium", "low", "failed"]
ExtractionSource = Literal["native_pdf", "ocr"]
CheckResult = Literal["pass", "warning", "fail", "not_applicable", "insufficient_data"]
DocumentClass = Literal["invoice", "certificate", "generic_document"]
Severity = Literal["low", "medium", "high"]


class TextToken(BaseModel):
    text: str
    bbox: BoundingBox | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    font_size: float | None = None


class ExtractedPage(BaseModel):
    page_number: int
    source: ExtractionSource
    quality: ExtractionQuality
    confidence: float = Field(ge=0.0, le=1.0)
    text: str
    tokens: list[TextToken] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    overall_quality: ExtractionQuality
    overall_confidence: float = Field(ge=0.0, le=1.0)
    pages: list[ExtractedPage] = Field(default_factory=list)
    tesseract_available: bool = True
    notes: list[str] = Field(default_factory=list)


class FieldEvidence(BaseModel):
    label: str | None = None
    bbox: BoundingBox | None = None
    snippet: str | None = None


class ExtractedField(BaseModel):
    field_id: str
    field_type: str
    value: str
    normalized_value: Any = None
    page_number: int | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    source: ExtractionSource | str
    evidence: FieldEvidence | None = None


class CheckEvidence(BaseModel):
    expected: Any = None
    observed: Any = None
    bbox: BoundingBox | None = None
    page_number: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class LogicalCheck(BaseModel):
    check_id: str
    category: str
    result: CheckResult
    severity: Severity
    score_impact: int = 0
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: CheckEvidence = Field(default_factory=CheckEvidence)
    explanation: str
    artifact_id: str | None = None


class BarcodeFinding(BaseModel):
    kind: str
    value: str
    page_number: int
    bbox: BoundingBox | None = None


class DocumentClassification(BaseModel):
    document_class: DocumentClass
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class DocumentIntelligenceResult(BaseModel):
    layer: str = "document_intelligence"
    extraction: ExtractionResult
    classification: DocumentClassification
    fields: list[ExtractedField] = Field(default_factory=list)
    logical_checks: list[LogicalCheck] = Field(default_factory=list)
    barcodes: list[BarcodeFinding] = Field(default_factory=list)
    suspicion_score: int = Field(ge=0, le=100)
    flagged: bool
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str
    limitations: list[str] = Field(default_factory=list)
    module_error: str | None = None
