from __future__ import annotations

from app.schemas.compliance import IntegrityAssessment
from app.schemas.fusion import FusionResult


def integrity_from_fusion(fusion: FusionResult | None, forensic_id: str | None) -> IntegrityAssessment:
    if fusion is None:
        return IntegrityAssessment(
            level="UNAVAILABLE",
            forensic_analysis_id=forensic_id,
            summary="Certificate integrity assessment was unavailable.",
            limitations=["The forensic pipeline did not produce a fused assessment."],
        )
    level = _map_level(fusion)
    findings = [item.finding for item in fusion.top_findings[:5]]
    return IntegrityAssessment(
        level=level,
        forensic_risk_level=fusion.risk_level,
        overall_risk_score=fusion.overall_risk_score,
        assessment_confidence=fusion.assessment_confidence,
        analysis_coverage=fusion.analysis_coverage,
        forensic_analysis_id=forensic_id,
        top_findings=findings,
        limitations=list(fusion.limitations),
        summary=fusion.assessment_summary,
    )


def _map_level(fusion: FusionResult) -> str:
    if fusion.risk_level == "INCONCLUSIVE":
        return "INCONCLUSIVE"
    if fusion.risk_level == "HIGH":
        return "HIGH_MANIPULATION_RISK"
    if fusion.risk_level == "ELEVATED":
        return "ELEVATED_MANIPULATION_RISK"
    if fusion.risk_level == "MODERATE":
        return "MODERATE_MANIPULATION_RISK"
    if fusion.top_findings or fusion.overall_risk_score >= 28:
        return "LOW_MANIPULATION_RISK"
    return "NO_MEANINGFUL_TAMPER_EVIDENCE"
