"""Deterministic certificate fusion across independent evidence streams.

Document content, signature integrity, and reference comparison stay separate.
Reference mismatch never changes document-content status.
"""

from __future__ import annotations

from app.schemas.fusion import FusionResult
from app.schemas.signature import (
    CertificateIntegrityAssessment,
    RankedFinding,
    SignatureFusion,
    StreamAssessment,
)

ACTIONS = {
    "CERTIFICATE_CLEAR": (
        "No significant manipulation evidence was detected in the completed analysis. "
        "This result does not independently establish legal authenticity."
    ),
    "REVIEW_REQUIRED": (
        "Manual review is recommended because suspicious evidence was detected but was not sufficient "
        "for a strong technical conclusion."
    ),
    "ELEVATED_CONCERN": "Multiple forensic inconsistencies were detected. Verification against an authoritative source is recommended.",
    "HIGH_MANIPULATION_CONCERN": (
        "Strong or corroborating forensic manipulation indicators were detected. "
        "The document should not be treated as verified without manual or authoritative review."
    ),
    "INCONCLUSIVE": "Reliable assessment was limited by image quality or incomplete analysis coverage.",
}

REFERENCE_LABEL = {
    "REFERENCE_MATCH_HIGH": "HIGH_REFERENCE_MATCH",
    "REFERENCE_MATCH_MODERATE": "MODERATE_REFERENCE_MATCH",
    "POTENTIAL_MISMATCH": "POTENTIAL_MISMATCH",
    "INCONCLUSIVE": "INCONCLUSIVE",
}


def fuse_certificate(
    *,
    document: StreamAssessment,
    signature: StreamAssessment,
    reference: SignatureFusion | None,
    fusion: FusionResult | None,
    completed: list[str],
    unavailable: list[str],
    extra_limitations: list[str],
) -> CertificateIntegrityAssessment:
    reference_stream = _reference_stream(reference)
    overall = _overall(document.status, signature.status)
    findings = _rank(document, signature, reference_stream)
    limitations = _unique(list(document.limitations) + list(signature.limitations) + extra_limitations)
    if reference_stream:
        limitations.extend(reference_stream.limitations)
    coverage = fusion.analysis_coverage if fusion else 0.0
    confidence = fusion.assessment_confidence if fusion else 0.0
    if signature.status == "AWAITING_SELECTION":
        coverage = max(0.0, coverage * 0.85)
        confidence = max(0.0, confidence * 0.9)
        limitations.append("Signature integrity and optional reference comparison are incomplete until a region is confirmed.")
    if signature.status == "INCONCLUSIVE":
        confidence = min(confidence, 0.72)
    summary = _summary(overall, document.status, signature.status, reference_stream.status if reference_stream else "NOT_REQUESTED")
    return CertificateIntegrityAssessment(
        overall_status=overall,  # type: ignore[arg-type]
        confidence=round(min(1.0, confidence), 4),
        analysis_coverage=round(min(1.0, coverage), 4),
        summary=summary,
        recommended_action=ACTIONS[overall],
        completed_checks=completed,
        unavailable_checks=unavailable,
        limitations=_unique(limitations)[:12],
        top_findings=findings,
        document_content=document,
        signature_integrity=signature,
        reference_comparison=reference_stream,
        extracted_fields=[],
        overlay_regions=[],
    )


def _reference_stream(fusion: SignatureFusion | None) -> StreamAssessment | None:
    if fusion is None:
        return None
    status = REFERENCE_LABEL.get(fusion.overall_status, fusion.overall_status)
    return StreamAssessment(
        status=status,
        summary=fusion.assessment_summary,
        confidence=fusion.assessment_confidence,
        risk_score=fusion.similarity_score,
        findings=[f"Technical similarity {fusion.similarity_score}/100 to the supplied reference signature."],
        limitations=list(fusion.limitations),
    )


def _overall(document: str, signature: str) -> str:
    high = {"HIGH_MANIPULATION_RISK"}
    elevated = {"ELEVATED_MANIPULATION_RISK"}
    review = {"REVIEW_REQUIRED", "LOW_MANIPULATION_RISK"}
    inconclusive = {"INCONCLUSIVE", "AWAITING_SELECTION"}
    if document in high or signature in high:
        return "HIGH_MANIPULATION_CONCERN"
    if document in elevated or signature in elevated:
        return "ELEVATED_CONCERN"
    if document in inconclusive and signature in inconclusive:
        return "INCONCLUSIVE"
    if document == "INCONCLUSIVE" and signature not in high | elevated:
        return "INCONCLUSIVE"
    if document in review or signature in review or signature == "AWAITING_SELECTION":
        return "REVIEW_REQUIRED"
    return "CERTIFICATE_CLEAR"


def _rank(document: StreamAssessment, signature: StreamAssessment, reference: StreamAssessment | None) -> list[RankedFinding]:
    items: list[tuple[int, RankedFinding]] = []
    items.append((_strength_rank(document.status), RankedFinding(rank=0, stream="document", finding=document.summary, strength=_strength(document.status))))
    items.append((_strength_rank(signature.status), RankedFinding(rank=0, stream="signature", finding=signature.summary, strength=_strength(signature.status))))
    if reference:
        items.append((_strength_rank(reference.status), RankedFinding(rank=0, stream="reference", finding=reference.summary, strength=_strength(reference.status))))
    items.sort(key=lambda pair: pair[0], reverse=True)
    ranked = []
    for index, (_, finding) in enumerate(items, start=1):
        ranked.append(finding.model_copy(update={"rank": index}))
    return ranked


def _strength(status: str) -> str:
    if status in {"HIGH_MANIPULATION_RISK", "HIGH_MANIPULATION_CONCERN", "POTENTIAL_MISMATCH"}:
        return "high"
    if status in {"ELEVATED_MANIPULATION_RISK", "REVIEW_REQUIRED", "AWAITING_SELECTION"}:
        return "moderate"
    return "low"


def _strength_rank(status: str) -> int:
    return {"high": 3, "moderate": 2, "low": 1}[_strength(status)]


def _summary(overall: str, document: str, signature: str, reference: str) -> str:
    return (
        f"Certificate integrity is {overall.replace('_', ' ')}. "
        f"Document content integrity: {document.replace('_', ' ')}. "
        f"Signature integrity: {signature.replace('_', ' ')}. "
        f"Reference comparison: {reference.replace('_', ' ')}. "
        "These streams are independent and are not averaged into a single authenticity claim."
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
