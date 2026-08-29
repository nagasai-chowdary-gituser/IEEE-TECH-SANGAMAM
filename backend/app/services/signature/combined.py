"""Deterministic combined assessment of reference comparison and tamper analysis.

These domains stay independent. Combined concern never overrides either source.

Scores and verdicts are computed after status. They do not change the status:

  originality_score — digital originality of the uploaded document
    (100 = no meaningful manipulation evidence in completed forensic layers).
    Inverse of forensic manipulation risk. None if tamper analysis is unavailable.

  originality_verdict — SAFE / NOT_SAFE / REVIEW / UNAVAILABLE from originality_score
    and tamper level. This is a document-integrity check, not signer identity.

  final_score — blend of reference similarity and originality.
    Inconclusive comparisons are capped. Not identity confidence.

  overall_verdict — SAFE / NOT_SAFE / REVIEW for the completed comparison.
"""

from __future__ import annotations

from app.schemas.signature import CombinedSignatureAssessment, SignatureFusion

ORIGINALITY_BY_LEVEL = {
    "NO_MEANINGFUL_TAMPER_EVIDENCE": 94,
    "LOW_MANIPULATION_RISK": 80,
    "MODERATE_MANIPULATION_RISK": 58,
    "ELEVATED_MANIPULATION_RISK": 34,
    "HIGH_MANIPULATION_RISK": 12,
}


def combine(
    fusion: SignatureFusion,
    tamper_level: str | None,
    tamper_risk_score: int | None = None,
) -> CombinedSignatureAssessment:
    comparison = fusion.overall_status
    tamper = tamper_level or "UNAVAILABLE"
    high_tamper = tamper in {"HIGH_MANIPULATION_RISK", "ELEVATED_MANIPULATION_RISK"}
    low_tamper = tamper in {"NO_MEANINGFUL_TAMPER_EVIDENCE", "LOW_MANIPULATION_RISK"}

    if comparison == "INCONCLUSIVE" and not high_tamper:
        concern = "INCONCLUSIVE"
    elif high_tamper and comparison == "POTENTIAL_MISMATCH":
        concern = "ELEVATED_CONCERN"
    elif high_tamper and comparison == "REFERENCE_MATCH_HIGH":
        concern = "ELEVATED_CONCERN"
    elif comparison == "REFERENCE_MATCH_HIGH" and low_tamper:
        concern = "LOW_CONCERN"
    elif tamper == "HIGH_MANIPULATION_RISK":
        concern = "ELEVATED_CONCERN"
    else:
        concern = "REVIEW_REQUIRED"

    originality = _originality_score(tamper, tamper_risk_score)
    originality_verdict = _originality_verdict(originality, tamper)
    final = _final_score(fusion.similarity_score, originality, comparison)
    overall_verdict = _overall_verdict(concern, originality_verdict, comparison, final)

    return CombinedSignatureAssessment(
        overall_concern=concern,  # type: ignore[arg-type]
        summary=_summary(comparison, tamper, concern, final, originality, originality_verdict, overall_verdict),
        comparison_status=comparison,
        tamper_level=tamper,
        final_score=final,
        originality_score=originality,
        originality_verdict=originality_verdict,  # type: ignore[arg-type]
        overall_verdict=overall_verdict,  # type: ignore[arg-type]
    )


def _originality_score(tamper: str, risk_score: int | None) -> int | None:
    if tamper in {"INCONCLUSIVE", "UNAVAILABLE"}:
        return None
    if risk_score is not None:
        return max(0, min(100, 100 - int(risk_score)))
    return ORIGINALITY_BY_LEVEL.get(tamper)


def _originality_verdict(score: int | None, tamper: str) -> str:
    if score is None or tamper in {"INCONCLUSIVE", "UNAVAILABLE"}:
        return "UNAVAILABLE"
    if tamper in {"HIGH_MANIPULATION_RISK", "ELEVATED_MANIPULATION_RISK"} or score < 50:
        return "NOT_SAFE"
    if score >= 70:
        return "SAFE"
    return "REVIEW"


def _final_score(similarity: int, originality: int | None, comparison: str) -> int:
    if originality is None:
        raw = similarity
    else:
        raw = int(round(0.58 * similarity + 0.42 * originality))
    if comparison == "INCONCLUSIVE":
        raw = min(raw, 45)
    if comparison == "POTENTIAL_MISMATCH":
        raw = min(raw, 62)
    return max(0, min(100, raw))


def _overall_verdict(concern: str, originality_verdict: str, comparison: str, final: int) -> str:
    if originality_verdict == "NOT_SAFE" or concern == "ELEVATED_CONCERN":
        return "NOT_SAFE"
    if comparison == "POTENTIAL_MISMATCH" and final < 55:
        return "NOT_SAFE"
    if originality_verdict == "SAFE" and concern == "LOW_CONCERN" and final >= 70:
        return "SAFE"
    return "REVIEW"


def _summary(
    comparison: str,
    tamper: str,
    concern: str,
    final: int,
    originality: int | None,
    originality_verdict: str,
    overall_verdict: str,
) -> str:
    comparison_text = {
        "REFERENCE_MATCH_HIGH": "Reference similarity is high",
        "REFERENCE_MATCH_MODERATE": "Reference similarity is moderate",
        "POTENTIAL_MISMATCH": "Reference comparison indicates a potential mismatch",
        "INCONCLUSIVE": "Reference comparison is inconclusive",
    }[comparison]
    tamper_text = {
        "NO_MEANINGFUL_TAMPER_EVIDENCE": "no meaningful digital manipulation evidence was detected in completed analysis",
        "LOW_MANIPULATION_RISK": "digital manipulation risk was low",
        "MODERATE_MANIPULATION_RISK": "moderate digital manipulation evidence was recorded",
        "ELEVATED_MANIPULATION_RISK": "elevated digital manipulation evidence was recorded",
        "HIGH_MANIPULATION_RISK": "high digital manipulation evidence was recorded",
        "INCONCLUSIVE": "tamper analysis was inconclusive",
        "UNAVAILABLE": "tamper analysis was unavailable",
    }.get(tamper, "tamper analysis status is unresolved")
    orig = f"{originality}/100" if originality is not None else "unavailable"
    orig_label = {"SAFE": "Safe", "NOT_SAFE": "Not safe", "REVIEW": "Review", "UNAVAILABLE": "Unavailable"}[originality_verdict]
    overall_label = {"SAFE": "Safe", "NOT_SAFE": "Not safe", "REVIEW": "Review"}[overall_verdict]
    return (
        f"{comparison_text}, and {tamper_text}. Combined concern is {concern.replace('_', ' ')}. "
        f"Final score {final}/100. Originality {orig_label} ({orig}). Overall verdict {overall_label}."
    )
