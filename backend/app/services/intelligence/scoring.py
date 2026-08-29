from __future__ import annotations

from app.schemas.intelligence import ExtractionResult, LogicalCheck
from app.services.intelligence.config import (
    CONFIDENCE_MAX,
    CONFIDENCE_MIN,
    CONFIDENCE_QUALITY,
    FLAG_THRESHOLD,
    WARNING_FACTOR,
)


def score_intelligence(extraction: ExtractionResult, checks: list[LogicalCheck]) -> tuple[int, bool, float]:
    """Document-level Phase 3 score.

    formula: min(100, sum(fail score_impact) + WARNING_FACTOR * sum(warning score_impact))

    Insufficient/not_applicable checks add nothing. A strong contradiction on
    one page is not diluted by pages with no checkable data because scoring
    uses checks, not a page average.
    """
    score = 0
    for check in checks:
        if check.result == "fail":
            score += check.score_impact
        elif check.result == "warning":
            score += int(round(check.score_impact * WARNING_FACTOR)) if check.score_impact else int(round(10 * WARNING_FACTOR))
    score = min(100, score)
    flagged = score >= FLAG_THRESHOLD or any(c.result == "fail" and c.severity == "high" for c in checks)
    quality_conf = CONFIDENCE_QUALITY.get(extraction.overall_quality, 0.4)
    evaluable = [c for c in checks if c.result in {"pass", "warning", "fail"}]
    if evaluable:
        mean_check = sum(c.confidence for c in evaluable) / len(evaluable)
        confidence = 0.55 * quality_conf + 0.45 * mean_check
    else:
        confidence = quality_conf * 0.6
    confidence = round(min(CONFIDENCE_MAX, max(CONFIDENCE_MIN, confidence)), 2)
    return score, flagged, confidence
