from __future__ import annotations

from app.schemas.fusion import (
    CorroborationResult,
    NormalizedLayerEvidence,
    RecommendedAction,
    RiskLevel,
    TopFinding,
)
from app.services.fusion.config import MEANINGFUL_EFFECTIVE, STRONG_EFFECTIVE, STRONG_RELIABILITY


_LAYER_LABEL = {
    "metadata": "metadata analysis",
    "ela": "visual anomaly analysis (ELA)",
    "copy_move": "duplicated-region (copy-move) analysis",
    "document_intelligence": "document intelligence",
}

_LEVEL_PHRASE = {
    "LOW": "low manipulation risk",
    "MODERATE": "moderate manipulation risk",
    "ELEVATED": "elevated manipulation risk",
    "HIGH": "high manipulation risk",
    "INCONCLUSIVE": "inconclusive",
}


def build_explanations(
    *,
    layers: list[NormalizedLayerEvidence],
    overall_risk_score: int,
    risk_level: RiskLevel,
    assessment_confidence: float,
    analysis_coverage: float,
    corroboration: CorroborationResult,
    limitations: list[str],
) -> tuple[str, RecommendedAction, list[TopFinding]]:
    findings = _top_findings(layers)
    summary = _assessment_summary(
        layers=layers,
        overall_risk_score=overall_risk_score,
        risk_level=risk_level,
        analysis_coverage=analysis_coverage,
        corroboration=corroboration,
        findings=findings,
        limitations=limitations,
    )
    action = _recommended_action(risk_level, assessment_confidence, analysis_coverage)
    return summary, action, findings


def _top_findings(layers: list[NormalizedLayerEvidence]) -> list[TopFinding]:
    ranked: list[tuple[int, float, NormalizedLayerEvidence, object]] = []
    for item in layers:
        if item.status in {"failed", "unavailable"}:
            continue
        for signal in item.signals:
            if signal.severity == "low" and item.effective_score < MEANINGFUL_EFFECTIVE:
                continue
            severity_rank = {"high": 3, "medium": 2, "low": 1}[signal.severity]
            ranked.append((severity_rank, signal.confidence, item, signal))
    ranked.sort(key=lambda row: (row[0], row[1], row[2].effective_score), reverse=True)
    findings: list[TopFinding] = []
    seen: set[str] = set()
    for _, _, item, signal in ranked:
        key = f"{item.layer}:{signal.id}"
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            TopFinding(
                rank=len(findings) + 1,
                layer=item.layer,
                finding=signal.finding,
                severity=signal.severity,
                confidence=signal.confidence,
                evidence_reference=signal.evidence_reference,
            )
        )
        if len(findings) >= 5:
            break
    return findings


def _assessment_summary(
    *,
    layers: list[NormalizedLayerEvidence],
    overall_risk_score: int,
    risk_level: RiskLevel,
    analysis_coverage: float,
    corroboration: CorroborationResult,
    findings: list[TopFinding],
    limitations: list[str],
) -> str:
    phrase = _LEVEL_PHRASE[risk_level]
    if risk_level == "INCONCLUSIVE":
        completed = [item.layer for item in layers if item.status in {"available", "limited"}]
        failed = [item.layer for item in layers if item.status in {"failed", "unavailable"}]
        parts = [
            f"Assessment is inconclusive because only limited analysis layers completed successfully "
            f"(coverage {analysis_coverage:.2f})."
        ]
        if completed:
            parts.append("Completed layers: " + ", ".join(_LAYER_LABEL[name] for name in completed) + ".")
        if failed:
            parts.append("Unavailable or failed layers: " + ", ".join(_LAYER_LABEL[name] for name in failed) + ".")
        parts.append("A low score under incomplete analysis is not a finding of low manipulation risk.")
        return " ".join(parts)

    contributors = sorted(layers, key=lambda item: item.effective_score, reverse=True)
    lead = next((item for item in contributors if item.effective_score >= MEANINGFUL_EFFECTIVE), None)
    if not findings and not lead:
        return (
            f"Overall assessment is {phrase} (score {overall_risk_score}). "
            "Little or no meaningful manipulation evidence was detected across completed layers. "
            "This is a forensic risk assessment based on available digital evidence, not legal proof of authenticity."
        )

    why = []
    if corroboration.strength in {"moderate", "strong"}:
        names = ", ".join(_LAYER_LABEL[name] for name in corroboration.independent_layers_with_evidence)
        why.append(
            f"Risk is {phrase} because independent layers indicate potential manipulation ({names})."
        )
    elif lead and lead.effective_score >= STRONG_EFFECTIVE and lead.reliability >= STRONG_RELIABILITY:
        why.append(
            f"Risk is {phrase} because high-confidence evidence was detected in {_LAYER_LABEL[lead.layer]}."
        )
        others = [item for item in layers if item.layer != lead.layer and item.status in {"available", "limited"}]
        if others and not corroboration.independent_layers_with_evidence[1:]:
            why.append(
                "Strong duplicated-region evidence was detected, but other available analysis layers "
                "did not provide independent corroboration."
                if lead.layer == "copy_move"
                else "Strong evidence was detected, but other available analysis layers did not provide independent corroboration."
            )
    elif lead:
        why.append(
            f"Risk is {phrase} because {_LAYER_LABEL[lead.layer]} contributed the strongest effective evidence "
            f"(raw score {lead.raw_score}, reliability {lead.reliability:.2f})."
        )
        if corroboration.strength == "none":
            why.append("Other completed layers did not independently corroborate the finding.")
    if findings:
        why.append(f"Strongest recorded finding: {findings[0].finding}")
    if limitations:
        why.append("Limitations were recorded and must be considered with this assessment.")
    why.append(
        "This is a forensic risk assessment based on available digital evidence. "
        "It is not legal proof of forgery or authenticity and does not verify signer identity."
    )
    return " ".join(why)


def _recommended_action(
    risk_level: RiskLevel,
    assessment_confidence: float,
    analysis_coverage: float,
) -> RecommendedAction:
    if risk_level == "INCONCLUSIVE" or analysis_coverage < 0.40 or assessment_confidence < 0.40:
        return "REANALYZE_WITH_HIGHER_QUALITY_SOURCE"
    if risk_level == "HIGH" and assessment_confidence >= 0.55:
        return "PRIORITY_MANUAL_REVIEW"
    if risk_level in {"MODERATE", "ELEVATED", "HIGH"}:
        return "MANUAL_REVIEW_RECOMMENDED"
    if risk_level == "LOW" and assessment_confidence >= 0.55:
        return "NO_ADDITIONAL_ACTION"
    return "REANALYZE_WITH_HIGHER_QUALITY_SOURCE"
