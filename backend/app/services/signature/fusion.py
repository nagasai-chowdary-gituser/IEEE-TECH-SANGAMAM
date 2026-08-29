"""Deterministic reference-signature fusion.

Signals are not averaged blindly. Quality and detection confidence gate
whether a similarity score may support a match or mismatch claim.

INCONCLUSIVE when:
  - image_quality_score < 0.34
  - region_detection_confidence is present and < 0.38
  - fewer than two usable similarity signals

REFERENCE_MATCH_HIGH when quality is adequate and the quality-weighted
similarity is >= 0.78 with at least two corroborating signals >= 0.62.

REFERENCE_MATCH_MODERATE when quality is adequate and weighted similarity
is >= 0.56.

POTENTIAL_MISMATCH when quality is adequate and weighted similarity < 0.56.

Similarity score is 0–100 technical similarity, not identity confidence.
"""

from __future__ import annotations

from app.schemas.signature import ComparisonSignals, SignatureFusion

ACTIONS = {
    "REFERENCE_MATCH_HIGH": "No major signature mismatch indicators detected. Review alongside other document verification evidence.",
    "REFERENCE_MATCH_MODERATE": "Similarity evidence is present but not conclusive. Manual review is recommended for high-stakes use.",
    "POTENTIAL_MISMATCH": "Meaningful differences from the provided reference signature were detected. Manual verification against an authoritative source is recommended.",
    "INCONCLUSIVE": "Image quality or extraction limitations prevented a reliable comparison. Request a higher-quality document or manually select the signature region.",
}


def fuse_comparison(signals: ComparisonSignals) -> SignatureFusion:
    limitations: list[str] = []
    usable = _usable(signals)
    quality = signals.image_quality_score if signals.image_quality_score is not None else 0.0
    detection = signals.region_detection_confidence
    if quality < 0.34:
        limitations.append("Image quality was too low for a reliable reference comparison.")
    if detection is not None and detection < 0.38:
        limitations.append("Signature-region detection confidence was too low to treat the comparison as reliable.")
    if len(usable) < 2:
        limitations.append("Fewer than two independent visual signals were available.")

    weighted = _weighted_similarity(usable, quality)
    score = int(round(weighted * 100))
    if quality < 0.34 or (detection is not None and detection < 0.38) or len(usable) < 2:
        status = "INCONCLUSIVE"
    elif weighted >= 0.78 and _corroboration(usable) >= 2:
        status = "REFERENCE_MATCH_HIGH"
    elif weighted >= 0.56:
        status = "REFERENCE_MATCH_MODERATE"
    else:
        status = "POTENTIAL_MISMATCH"

    summary = _summary(status, score, quality, usable)
    return SignatureFusion(
        overall_status=status,  # type: ignore[arg-type]
        similarity_score=score,
        assessment_confidence=round(min(1.0, 0.35 + 0.4 * quality + 0.05 * len(usable)), 4),
        assessment_summary=summary,
        recommended_action=ACTIONS[status],
        limitations=limitations,
        signals=signals,
    )


def _usable(signals: ComparisonSignals) -> list[tuple[str, float, float]]:
    items: list[tuple[str, float, float]] = []
    mapping = [
        ("structural_similarity", signals.structural_similarity, 0.34),
        ("contour_similarity", signals.contour_similarity, 0.26),
        ("feature_match_score", signals.feature_match_score, 0.18),
        ("geometry_similarity", signals.geometry_similarity, 0.12),
        ("histogram_similarity", signals.histogram_similarity, 0.10),
    ]
    for name, value, weight in mapping:
        if value is None:
            continue
        items.append((name, value, weight))
    return items


def _weighted_similarity(usable: list[tuple[str, float, float]], quality: float) -> float:
    if not usable:
        return 0.0
    total_w = sum(weight for _, _, weight in usable)
    raw = sum(value * weight for _, value, weight in usable) / total_w
    return raw * (0.55 + 0.45 * quality)


def _corroboration(usable: list[tuple[str, float, float]]) -> int:
    return sum(1 for _, value, _ in usable if value >= 0.62)


def _summary(status: str, score: int, quality: float, usable: list[tuple[str, float, float]]) -> str:
    names = ", ".join(name.replace("_", " ") for name, _, _ in usable) or "no usable signals"
    if status == "REFERENCE_MATCH_HIGH":
        return (
            f"The extracted document signature shows high similarity to the provided reference "
            f"(technical similarity {score}/100) across {names}. Image quality was sufficient for comparison."
        )
    if status == "REFERENCE_MATCH_MODERATE":
        return (
            f"Meaningful similarity to the provided reference was detected (technical similarity {score}/100), "
            f"but the evidence is not strong enough for a high-confidence match."
        )
    if status == "POTENTIAL_MISMATCH":
        return (
            f"Comparison shows low similarity to the provided reference signature (technical similarity {score}/100). "
            f"This is not legal proof of forgery."
        )
    return (
        f"Comparison is inconclusive. Quality score was {quality:.2f} and usable signals were: {names}. "
        f"The similarity score alone is not sufficient for a reliable assessment."
    )
