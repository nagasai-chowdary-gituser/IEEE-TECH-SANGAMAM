"""Deterministic Government Bid Compliance aggregation.

PAN/GST outcomes answer whether a configured verification source validated
an identifier. Forensic integrity answers whether the certificate shows
digital manipulation evidence. These domains are not averaged.

COMPLIANT
  PAN passed, GSTIN passed, integrity is NO_MEANINGFUL or LOW, and there is
  no critical unresolved limitation.

HIGH_RISK
  Integrity is HIGH, or integrity is ELEVATED with at least one identifier
  verification failure, or both identifiers failed verification.
  External API unavailability alone never produces HIGH_RISK.

INCONCLUSIVE
  A required identifier was not extracted, both verification services are
  unavailable/skipped, integrity is INCONCLUSIVE/UNAVAILABLE with no other
  decisive failure, or coverage is too limited for a conclusion.

REVIEW_REQUIRED
  All other combinations, including mixed pass/fail, moderate forensic risk,
  or a single unresolved verification.
"""

from __future__ import annotations

from app.schemas.compliance import (
    ComplianceAggregation,
    IdentifierVerification,
    IntegrityAssessment,
)


def aggregate(
    pan: IdentifierVerification,
    gstin: IdentifierVerification,
    integrity: IntegrityAssessment,
) -> ComplianceAggregation:
    limitations = list(integrity.limitations)
    if pan.limitation:
        limitations.append(pan.limitation)
    if gstin.limitation:
        limitations.append(gstin.limitation)
    score = _risk_score(pan, gstin, integrity)
    status = _status(pan, gstin, integrity)
    summary = _summary(status, pan, gstin, integrity)
    action = {
        "COMPLIANT": "No additional compliance action is required based on completed checks. This is decision support, not legal approval.",
        "REVIEW_REQUIRED": "Manual review is recommended before relying on this certificate for bid compliance.",
        "HIGH_RISK": "Priority manual review is recommended. Independent concerns were recorded.",
        "INCONCLUSIVE": "Reanalyze with a clearer certificate and configured verification services before drawing a compliance conclusion.",
    }[status]
    return ComplianceAggregation(
        overall_status=status,  # type: ignore[arg-type]
        compliance_risk_score=score,
        assessment_summary=summary,
        recommended_action=action,
        limitations=list(dict.fromkeys(limitations)),
        pan=pan,
        gstin=gstin,
        integrity=integrity,
    )


def _status(
    pan: IdentifierVerification,
    gstin: IdentifierVerification,
    integrity: IntegrityAssessment,
) -> str:
    both_failed = pan.outcome == "failed" and gstin.outcome == "failed"
    elevated_plus_fail = integrity.level == "ELEVATED_MANIPULATION_RISK" and (
        pan.outcome == "failed" or gstin.outcome == "failed"
    )
    if integrity.level == "HIGH_MANIPULATION_RISK" or both_failed or elevated_plus_fail:
        return "HIGH_RISK"

    missing = pan.outcome == "not_extracted" or gstin.outcome == "not_extracted"
    both_unresolved = pan.outcome in {"unavailable", "skipped", "error"} and gstin.outcome in {
        "unavailable",
        "skipped",
        "error",
    }
    integrity_blocked = integrity.level in {"INCONCLUSIVE", "UNAVAILABLE"}
    coverage_low = (integrity.analysis_coverage or 1.0) < 0.34
    if missing or both_unresolved or integrity_blocked or coverage_low:
        return "INCONCLUSIVE"

    if (
        pan.outcome == "passed"
        and gstin.outcome == "passed"
        and integrity.level in {"NO_MEANINGFUL_TAMPER_EVIDENCE", "LOW_MANIPULATION_RISK"}
    ):
        return "COMPLIANT"
    return "REVIEW_REQUIRED"


def _risk_score(
    pan: IdentifierVerification,
    gstin: IdentifierVerification,
    integrity: IntegrityAssessment,
) -> int:
    score = 0
    score += {"failed": 40, "format_invalid": 28, "not_extracted": 25, "unavailable": 12, "error": 12, "skipped": 8, "passed": 0}.get(pan.outcome, 10)
    score += {"failed": 40, "format_invalid": 28, "not_extracted": 25, "unavailable": 12, "error": 12, "skipped": 8, "passed": 0}.get(gstin.outcome, 10)
    score += {
        "HIGH_MANIPULATION_RISK": 45,
        "ELEVATED_MANIPULATION_RISK": 32,
        "MODERATE_MANIPULATION_RISK": 18,
        "INCONCLUSIVE": 15,
        "UNAVAILABLE": 15,
        "LOW_MANIPULATION_RISK": 6,
        "NO_MEANINGFUL_TAMPER_EVIDENCE": 0,
    }.get(integrity.level, 10)
    return max(0, min(100, score))


def _summary(
    status: str,
    pan: IdentifierVerification,
    gstin: IdentifierVerification,
    integrity: IntegrityAssessment,
) -> str:
    pan_text = _ident_phrase("PAN", pan)
    gst_text = _ident_phrase("GSTIN", gstin)
    integrity_text = {
        "NO_MEANINGFUL_TAMPER_EVIDENCE": "Certificate forensic analysis found no meaningful manipulation evidence across completed analysis layers.",
        "LOW_MANIPULATION_RISK": "Certificate forensic analysis indicated low manipulation risk.",
        "MODERATE_MANIPULATION_RISK": "Certificate forensic analysis indicated moderate manipulation risk.",
        "ELEVATED_MANIPULATION_RISK": "Certificate forensic analysis indicated elevated manipulation risk.",
        "HIGH_MANIPULATION_RISK": "Certificate forensic analysis indicated high manipulation risk.",
        "INCONCLUSIVE": "Certificate forensic analysis was inconclusive.",
        "UNAVAILABLE": "Certificate integrity assessment was unavailable.",
    }.get(integrity.level, integrity.summary)
    return f"{pan_text} {gst_text} {integrity_text} Final compliance status is {status.replace('_', ' ')}."


def _ident_phrase(label: str, item: IdentifierVerification) -> str:
    mapping = {
        "passed": f"{label} was verified through the configured verification service.",
        "failed": f"The configured {label} verification service did not verify the extracted identifier.",
        "unavailable": f"{label} verification could not be completed because the verification provider was unavailable.",
        "not_extracted": f"{label} could not be extracted from the certificate.",
        "format_invalid": f"Extracted {label} failed format validation and was not sent to the verification service.",
        "skipped": f"{label} verification was skipped by configuration.",
        "error": f"{label} verification returned an unusable response.",
    }
    return mapping.get(item.outcome, f"{label} verification is unresolved.")
