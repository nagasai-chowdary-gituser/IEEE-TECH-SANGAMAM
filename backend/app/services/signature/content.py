"""Document content integrity from the existing forensic fusion + intelligence layers."""

from __future__ import annotations

from app.schemas.fusion import FusionResult
from app.schemas.intelligence import DocumentIntelligenceResult
from app.schemas.signature import StreamAssessment
from app.schemas.visual import CopyMoveForensicsResult, ElaForensicsResult
from app.services.compliance.integrity import integrity_from_fusion


def document_content_integrity(
    fusion: FusionResult | None,
    intelligence: DocumentIntelligenceResult | None,
    ela: ElaForensicsResult | None,
    copy_move: CopyMoveForensicsResult | None,
) -> StreamAssessment:
    integrity = integrity_from_fusion(fusion, None)
    findings: list[str] = []
    limitations = list(integrity.limitations)
    if fusion:
        findings.extend(item.finding for item in fusion.top_findings[:6])
    if intelligence:
        for check in intelligence.logical_checks:
            if check.result in {"fail", "warning"}:
                findings.append(check.explanation)
        limitations.extend(intelligence.limitations[:4])
        if intelligence.extraction.overall_quality in {"low", "failed"}:
            limitations.append("OCR/text extraction quality was limited. Low OCR confidence is not treated as tampering.")
    if ela and ela.flagged:
        findings.append(ela.summary)
    if copy_move and copy_move.flagged:
        findings.append(copy_move.summary)

    unique_findings = _unique(findings)
    status = integrity.level
    if fusion is None:
        status = "INCONCLUSIVE"
        summary = "Analysis inconclusive due to scan/image quality."
    elif fusion.risk_level == "INCONCLUSIVE":
        status = "INCONCLUSIVE"
        summary = "Analysis inconclusive due to scan/image quality."
    elif fusion.risk_level == "HIGH":
        status = "HIGH_MANIPULATION_RISK"
        summary = "Multiple forensic inconsistencies detected."
    elif fusion.risk_level == "ELEVATED" or len(unique_findings) >= 3:
        status = "ELEVATED_MANIPULATION_RISK"
        summary = "Multiple forensic inconsistencies detected."
    elif unique_findings or fusion.risk_level == "MODERATE":
        status = "REVIEW_REQUIRED" if unique_findings else "LOW_MANIPULATION_RISK"
        summary = "Suspicious region detected requiring review." if unique_findings else integrity.summary
    elif integrity.level == "LOW_MANIPULATION_RISK":
        status = "LOW_MANIPULATION_RISK"
        summary = "No significant manipulation evidence detected in the completed analysis."
    else:
        status = "NO_SIGNIFICANT_MANIPULATION_EVIDENCE"
        summary = "No significant manipulation evidence detected in the completed analysis."

    return StreamAssessment(
        status=status,
        summary=summary,
        confidence=fusion.assessment_confidence if fusion else None,
        risk_score=fusion.overall_risk_score if fusion else None,
        findings=unique_findings[:8],
        limitations=_unique(limitations)[:8],
    )


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
