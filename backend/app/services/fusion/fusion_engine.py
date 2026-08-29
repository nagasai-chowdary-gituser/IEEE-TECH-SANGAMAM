"""Deterministic evidence fusion.

The overall risk score is NOT the mean of layer scores.

base_score =
    0.70 * max(effective_i)
  + 0.20 * second_max(effective_i)
  + 0.10 * mean(remaining effective_i)

where effective_i = raw_score_i * reliability_i.

A single high-reliability layer therefore cannot be washed out by clean layers.
A high raw score with low reliability contributes little.

Independent corroboration (capped):
  Count layers with meaningful evidence:
    raw_score >= 32 AND reliability >= 0.38 AND effective_score >= 22
  Bonus by count: 0→0, 1→0 (isolated), 2→10, 3→16, 4→20 (cap 20).

Related signals inside one layer are already grouped during normalization,
so five similar metadata timestamp notes cannot act as five independent layers.

Failed and unavailable layers contribute 0 effective score and 0 coverage
weight. They are not interpreted as “no manipulation found.”
"""

from __future__ import annotations

from statistics import fmean

from app.schemas.fusion import (
    CorroborationResult,
    FusionResult,
    LayerContribution,
    LayerName,
    NormalizedLayerEvidence,
)
from app.services.fusion.config import (
    CORROBORATION_BONUS,
    CORROBORATION_CAP,
    COVERAGE_AVAILABLE,
    COVERAGE_FAILED,
    COVERAGE_LIMITED,
    COVERAGE_UNAVAILABLE,
    ELEVATED_SCORE,
    HIGH_SCORE,
    INCONCLUSIVE_COVERAGE,
    INCONCLUSIVE_MIN_USABLE_LAYERS,
    MEANINGFUL_EFFECTIVE,
    MEANINGFUL_RAW_SCORE,
    MEANINGFUL_RELIABILITY,
    MODERATE_SCORE,
    STRONG_EFFECTIVE,
    STRONG_RELIABILITY,
    WEIGHT_MAX,
    WEIGHT_REST,
    WEIGHT_SECOND,
)
from app.services.fusion.explanation_builder import build_explanations


def fuse(layers: list[NormalizedLayerEvidence]) -> FusionResult:
    meaningful = [item for item in layers if _is_meaningful(item)]
    bonus = min(CORROBORATION_CAP, CORROBORATION_BONUS.get(len(meaningful), CORROBORATION_CAP))
    base = _base_score(layers)
    overall = int(round(min(100.0, max(0.0, base + bonus))))
    coverage = _analysis_coverage(layers)
    confidence = _assessment_confidence(layers, coverage, meaningful)
    corroboration = _corroboration(meaningful)
    risk_level = _risk_level(overall, coverage, layers)
    contributions = [
        LayerContribution(
            layer=item.layer,
            raw_score=item.raw_score,
            reliability=item.reliability,
            effective_contribution=item.effective_score,
            status=item.status,
            summary=_layer_summary(item),
        )
        for item in layers
    ]
    limitations = _collect_limitations(layers, coverage)
    summary, action, findings = build_explanations(
        layers=layers,
        overall_risk_score=overall,
        risk_level=risk_level,
        assessment_confidence=confidence,
        analysis_coverage=coverage,
        corroboration=corroboration,
        limitations=limitations,
    )
    return FusionResult(
        overall_risk_score=overall,
        risk_level=risk_level,
        assessment_confidence=confidence,
        analysis_coverage=coverage,
        layer_contributions=contributions,
        corroboration=corroboration,
        top_findings=findings,
        limitations=limitations,
        assessment_summary=summary,
        recommended_action=action,
    )


def _is_meaningful(item: NormalizedLayerEvidence) -> bool:
    if item.status in {"failed", "unavailable"}:
        return False
    return (
        item.raw_score >= MEANINGFUL_RAW_SCORE
        and item.reliability >= MEANINGFUL_RELIABILITY
        and item.effective_score >= MEANINGFUL_EFFECTIVE
    )


def _base_score(layers: list[NormalizedLayerEvidence]) -> float:
    values = sorted((item.effective_score for item in layers), reverse=True)
    while len(values) < 4:
        values.append(0.0)
    rest = values[2:]
    rest_mean = fmean(rest) if rest else 0.0
    return WEIGHT_MAX * values[0] + WEIGHT_SECOND * values[1] + WEIGHT_REST * rest_mean


def _analysis_coverage(layers: list[NormalizedLayerEvidence]) -> float:
    weights = []
    for item in layers:
        if item.status == "available":
            weights.append(COVERAGE_AVAILABLE if item.reliability >= 0.50 else 0.70)
        elif item.status == "limited":
            weights.append(COVERAGE_LIMITED)
        elif item.status == "failed":
            weights.append(COVERAGE_FAILED)
        else:
            weights.append(COVERAGE_UNAVAILABLE)
    return round(sum(weights) / 4.0, 4)


def _assessment_confidence(
    layers: list[NormalizedLayerEvidence],
    coverage: float,
    meaningful: list[NormalizedLayerEvidence],
) -> float:
    usable = [item for item in layers if item.status in {"available", "limited"}]
    mean_rel = fmean(item.reliability for item in usable) if usable else 0.0
    corr = 0.10 if len(meaningful) >= 2 else 0.0
    isolated_strong = (
        len(meaningful) == 1
        and meaningful[0].effective_score >= STRONG_EFFECTIVE
        and meaningful[0].reliability >= STRONG_RELIABILITY
    )
    isolated_penalty = 0.08 if isolated_strong else 0.0
    value = coverage * 0.55 + mean_rel * 0.35 + corr - isolated_penalty
    if len(usable) < INCONCLUSIVE_MIN_USABLE_LAYERS:
        value *= 0.72
    return round(max(0.0, min(1.0, value)), 4)


def _corroboration(meaningful: list[NormalizedLayerEvidence]) -> CorroborationResult:
    names: list[LayerName] = [item.layer for item in meaningful]
    count = len(names)
    if count <= 1:
        strength = "none"
        if count == 1:
            description = (
                "Strong evidence detected in one layer; independent corroboration was not found."
                if meaningful[0].effective_score >= STRONG_EFFECTIVE
                else "Meaningful evidence was found in a single layer without independent corroboration."
            )
        else:
            description = "No meaningful forensic evidence was detected across completed layers."
    elif count == 2:
        min_eff = min(item.effective_score for item in meaningful)
        strength = "moderate" if min_eff >= 28 else "weak"
        description = "Independent corroboration detected across 2 analysis layers."
    else:
        strength = "strong" if all(item.effective_score >= 30 for item in meaningful[:2]) else "moderate"
        description = f"Independent corroboration detected across {count} analysis layers."
    return CorroborationResult(
        independent_layers_with_evidence=names,
        strength=strength,
        description=description,
    )


def _risk_level(score: int, coverage: float, layers: list[NormalizedLayerEvidence]) -> str:
    usable = [item for item in layers if item.status in {"available", "limited"}]
    if coverage < INCONCLUSIVE_COVERAGE or len(usable) < INCONCLUSIVE_MIN_USABLE_LAYERS:
        return "INCONCLUSIVE"
    if score >= HIGH_SCORE:
        return "HIGH"
    if score >= ELEVATED_SCORE:
        return "ELEVATED"
    if score >= MODERATE_SCORE:
        return "MODERATE"
    return "LOW"


def _layer_summary(item: NormalizedLayerEvidence) -> str:
    if item.status == "failed":
        return "Analysis failed. This is not treated as a clean result."
    if item.status == "unavailable":
        return "Analysis was unavailable. This is not the same as finding no evidence."
    if item.status == "limited" and item.effective_score < MEANINGFUL_EFFECTIVE:
        return "Analysis completed with limited quality; contribution is reduced."
    if item.effective_score < MEANINGFUL_EFFECTIVE and item.raw_score < MEANINGFUL_RAW_SCORE:
        return "Analysis completed; no meaningful manipulation evidence was found."
    if item.effective_score < MEANINGFUL_EFFECTIVE:
        return "Signals were present but reliability was too low to treat them as strong evidence."
    return item.summary


def _collect_limitations(layers: list[NormalizedLayerEvidence], coverage: float) -> list[str]:
    notes: list[str] = []
    for item in layers:
        notes.extend(item.limitations)
        if item.status == "failed":
            notes.append(f"{_label(item.layer)} analysis failed.")
        elif item.status == "unavailable":
            notes.append(f"{_label(item.layer)} analysis was unavailable.")
    if coverage < 0.60:
        notes.append("Overall analysis coverage was limited.")
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(notes))


def _label(layer: str) -> str:
    return {
        "metadata": "Metadata",
        "ela": "ELA",
        "copy_move": "Copy-move",
        "document_intelligence": "Document intelligence",
    }.get(layer, layer)
