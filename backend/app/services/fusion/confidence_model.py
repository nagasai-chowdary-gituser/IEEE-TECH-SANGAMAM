from __future__ import annotations

from app.schemas.fusion import NormalizedLayerEvidence
from app.schemas.intelligence import DocumentIntelligenceResult
from app.schemas.metadata import MetadataForensicsResult
from app.schemas.visual import CopyMoveForensicsResult, ElaForensicsResult
from app.services.fusion.evidence_normalizer import normalize_layers


def apply_reliability(
    layers: list[NormalizedLayerEvidence],
    *,
    metadata: MetadataForensicsResult | None,
    ela: ElaForensicsResult | None,
    copy_move: CopyMoveForensicsResult | None,
    intelligence: DocumentIntelligenceResult | None,
) -> list[NormalizedLayerEvidence]:
    """Attach reliability and effective_score. Failed/unavailable stay at 0 reliability."""
    by_name = {item.layer: item for item in layers}
    updated = [
        _with_effective(_metadata_reliability(by_name["metadata"], metadata)),
        _with_effective(_ela_reliability(by_name["ela"], ela)),
        _with_effective(_copy_move_reliability(by_name["copy_move"], copy_move)),
        _with_effective(_intelligence_reliability(by_name["document_intelligence"], intelligence)),
    ]
    return updated


def apply_reliability_from_results(
    metadata: MetadataForensicsResult | None,
    ela: ElaForensicsResult | None,
    copy_move: CopyMoveForensicsResult | None,
    intelligence: DocumentIntelligenceResult | None,
) -> list[NormalizedLayerEvidence]:
    return apply_reliability(
        normalize_layers(metadata, ela, copy_move, intelligence),
        metadata=metadata,
        ela=ela,
        copy_move=copy_move,
        intelligence=intelligence,
    )


def _with_effective(item: NormalizedLayerEvidence) -> NormalizedLayerEvidence:
    if item.status in {"failed", "unavailable"}:
        item.reliability = 0.0
        item.effective_score = 0.0
        return item
    item.reliability = _clamp(item.reliability)
    item.effective_score = round(item.raw_score * item.reliability, 4)
    return item


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def _metadata_reliability(
    item: NormalizedLayerEvidence,
    result: MetadataForensicsResult | None,
) -> NormalizedLayerEvidence:
    if item.status in {"failed", "unavailable"} or result is None:
        item.reliability = 0.0
        return item
    reliability = result.confidence
    missing_family = [s for s in item.signals if "missing" in s.id or "stripped" in s.id]
    strong = [s for s in item.signals if s.severity in {"medium", "high"}]
    if missing_family and not strong:
        # Absence of metadata is weak evidence of manipulation, not high-reliability proof.
        reliability *= 0.55
        item.status = "limited"
        item.limitations = list(
            dict.fromkeys(
                item.limitations
                + ["Source metadata is limited; missing fields are not treated as manipulation."]
            )
        )
    elif item.evidence_count == 0:
        reliability = max(reliability, 0.70)
    item.reliability = reliability
    return item


def _ela_reliability(
    item: NormalizedLayerEvidence,
    result: ElaForensicsResult | None,
) -> NormalizedLayerEvidence:
    if item.status in {"failed", "unavailable"} or result is None:
        item.reliability = 0.0
        return item
    quality_scale = {"high": 1.0, "medium": 0.82, "limited": 0.52}
    reliability = result.confidence * quality_scale.get(result.analysis_quality, 0.52)
    if result.analysis_quality == "limited":
        item.status = "limited"
    if item.strong_evidence_count == 0 and result.analysis_quality != "high":
        reliability *= 0.85
    item.reliability = reliability
    return item


def _copy_move_reliability(
    item: NormalizedLayerEvidence,
    result: CopyMoveForensicsResult | None,
) -> NormalizedLayerEvidence:
    if item.status in {"failed", "unavailable"} or result is None:
        item.reliability = 0.0
        return item
    verified = sum(page.metrics.geometrically_verified_matches for page in result.pages)
    clusters = sum(page.metrics.suspicious_clusters for page in result.pages)
    keypoints = sum(page.metrics.keypoints_detected for page in result.pages)
    raw_matches = sum(page.metrics.raw_matches for page in result.pages)
    if verified > 0 or clusters > 0:
        geometric = min(0.95, 0.58 + 0.06 * min(verified, 6) + 0.08 * min(clusters, 4))
        reliability = result.confidence * geometric
    elif keypoints == 0:
        item.status = "limited"
        item.limitations = list(
            dict.fromkeys(item.limitations + ["Copy-move analysis did not have sufficient feature evidence."])
        )
        reliability = min(result.confidence, 0.28)
    else:
        # Raw ORB matches without geometric verification do not confer high reliability.
        reliability = min(result.confidence, 0.32) * (0.4 if raw_matches else 0.25)
        item.limitations = list(
            dict.fromkeys(
                item.limitations
                + ["Copy-move raw feature matches were not treated as verified duplicated-region evidence."]
            )
        )
    item.reliability = reliability
    return item


def _intelligence_reliability(
    item: NormalizedLayerEvidence,
    result: DocumentIntelligenceResult | None,
) -> NormalizedLayerEvidence:
    if item.status in {"failed", "unavailable"} or result is None:
        item.reliability = 0.0
        return item
    quality_scale = {"high": 1.0, "medium": 0.78, "low": 0.48, "failed": 0.22}
    reliability = result.confidence * quality_scale.get(result.extraction.overall_quality, 0.48)
    if result.extraction.overall_quality in {"low", "failed"}:
        item.status = "limited"
        item.limitations = list(
            dict.fromkeys(item.limitations + ["OCR extraction quality was low."])
            if result.extraction.overall_quality == "low"
            else item.limitations
        )
    failing = [c for c in result.logical_checks if c.result == "fail"]
    if failing:
        input_confidence = min(c.confidence for c in failing)
        if input_confidence >= 0.8 and result.extraction.overall_quality == "high":
            reliability = max(reliability, 0.82)
        else:
            reliability = min(reliability, max(0.25, input_confidence * quality_scale.get(result.extraction.overall_quality, 0.48)))
    item.reliability = reliability
    return item
