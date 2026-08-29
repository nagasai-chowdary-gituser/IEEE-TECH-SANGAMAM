from __future__ import annotations

from app.schemas.fusion import NormalizedLayerEvidence, NormalizedSignal
from app.schemas.intelligence import DocumentIntelligenceResult
from app.schemas.metadata import MetadataForensicsResult, MetadataSignal
from app.schemas.visual import CopyMoveForensicsResult, ElaForensicsResult


def normalize_layers(
    metadata: MetadataForensicsResult | None,
    ela: ElaForensicsResult | None,
    copy_move: CopyMoveForensicsResult | None,
    intelligence: DocumentIntelligenceResult | None,
) -> list[NormalizedLayerEvidence]:
    return [
        _normalize_metadata(metadata),
        _normalize_ela(ela),
        _normalize_copy_move(copy_move),
        _normalize_intelligence(intelligence),
    ]


def _signals_from_metadata(items: list[MetadataSignal], confidence: float) -> list[NormalizedSignal]:
    grouped: dict[str, MetadataSignal] = {}
    for item in items:
        family = item.id.rsplit("_", 1)[0] if "_" in item.id else item.id
        # Related signals from one root cause (e.g. several missing-metadata
        # fields) collapse to the strongest member of the family.
        current = grouped.get(family)
        if current is None or item.score_impact > current.score_impact:
            grouped[family] = item
    return [
        NormalizedSignal(
            id=signal.id,
            finding=signal.finding,
            severity=signal.severity,
            confidence=confidence,
        )
        for signal in grouped.values()
    ]


def _normalize_metadata(result: MetadataForensicsResult | None) -> NormalizedLayerEvidence:
    if result is None:
        return _unavailable("metadata")
    signals = _signals_from_metadata(result.signals, result.confidence)
    strong = sum(1 for s in signals if s.severity in {"medium", "high"})
    missing_only = strong == 0 and any("missing" in s.id or "stripped" in s.id for s in signals)
    return NormalizedLayerEvidence(
        layer="metadata",
        raw_score=result.suspicion_score,
        normalized_score=result.suspicion_score / 100.0,
        confidence=result.confidence,
        reliability=0.0,  # filled by confidence_model
        effective_score=0.0,
        evidence_count=len(signals),
        strong_evidence_count=strong,
        status="limited" if missing_only else "available",
        summary=result.summary,
        limitations=["Missing or stripped metadata is weak evidence and is not treated as proof of manipulation."]
        if missing_only
        else [],
        signals=signals,
    )


def _normalize_ela(result: ElaForensicsResult | None) -> NormalizedLayerEvidence:
    if result is None:
        return _unavailable("ela")
    if result.module_error:
        return _failed("ela", result.module_error, result.suspicion_score, result.confidence)
    page_signals = [s for page in result.pages for s in page.signals]
    evidence_refs = [e.artifact_id for page in result.pages for e in page.evidence]
    signals = _signals_from_metadata(page_signals, result.confidence)
    for index, signal in enumerate(signals):
        if index < len(evidence_refs):
            signal.evidence_reference = evidence_refs[index]
    limitations = [note for page in result.pages for note in page.limitations]
    quality = result.analysis_quality
    status = "limited" if quality == "limited" else "available"
    if quality == "limited":
        limitations = list(dict.fromkeys(limitations + ["ELA interpretation is limited for this source format."]))
    strong = sum(1 for s in signals if s.severity in {"medium", "high"})
    return NormalizedLayerEvidence(
        layer="ela",
        raw_score=result.suspicion_score,
        normalized_score=result.suspicion_score / 100.0,
        confidence=result.confidence,
        reliability=0.0,
        effective_score=0.0,
        evidence_count=len(signals),
        strong_evidence_count=strong,
        status=status,
        summary=result.summary,
        limitations=list(dict.fromkeys(limitations)),
        signals=signals,
    )


def _normalize_copy_move(result: CopyMoveForensicsResult | None) -> NormalizedLayerEvidence:
    if result is None:
        return _unavailable("copy_move")
    if result.module_error:
        return _failed("copy_move", result.module_error, result.suspicion_score, result.confidence)
    page_signals = [s for page in result.pages for s in page.signals]
    regions = [r for page in result.pages for r in page.regions]
    artifacts = [e.artifact_id for page in result.pages for e in page.evidence]
    signals = _signals_from_metadata(page_signals, result.confidence)
    if regions and not signals:
        signals.append(
            NormalizedSignal(
                id="copy_move_verified_cluster",
                finding="Repeated visual pattern detected.",
                severity="high" if any(r.evidence_strength == "high" for r in regions) else "medium",
                confidence=result.confidence,
                evidence_reference=artifacts[0] if artifacts else None,
            )
        )
    elif signals and artifacts:
        signals[0].evidence_reference = artifacts[0]
    verified = sum(page.metrics.geometrically_verified_matches for page in result.pages)
    limitations = [note for page in result.pages for note in page.limitations]
    if verified == 0 and not regions:
        limitations = list(dict.fromkeys(limitations + ["Copy-move analysis did not have sufficient geometrically verified evidence."]))
    return NormalizedLayerEvidence(
        layer="copy_move",
        raw_score=result.suspicion_score,
        normalized_score=result.suspicion_score / 100.0,
        confidence=result.confidence,
        reliability=0.0,
        effective_score=0.0,
        evidence_count=len(regions) or len(signals),
        strong_evidence_count=sum(1 for r in regions if r.evidence_strength in {"medium", "high"}),
        status="available",
        summary=result.summary,
        limitations=list(dict.fromkeys(limitations)),
        signals=signals,
    )


def _normalize_intelligence(result: DocumentIntelligenceResult | None) -> NormalizedLayerEvidence:
    if result is None:
        return _unavailable("document_intelligence")
    if result.module_error:
        return _failed(
            "document_intelligence",
            result.module_error,
            result.suspicion_score,
            result.confidence,
        )
    quality = result.extraction.overall_quality
    if quality == "failed" and not result.logical_checks:
        return _failed(
            "document_intelligence",
            "Text extraction did not yield usable content.",
            result.suspicion_score,
            result.confidence,
            extra_limitations=result.limitations,
        )
    status = "limited" if quality in {"low", "medium"} else "available"
    if quality == "failed":
        status = "limited"
    signals: list[NormalizedSignal] = []
    for check in result.logical_checks:
        if check.result not in {"fail", "warning"}:
            continue
        signals.append(
            NormalizedSignal(
                id=check.check_id,
                finding=check.explanation,
                severity=check.severity if check.result == "fail" else "low",
                confidence=check.confidence,
                evidence_reference=check.artifact_id,
            )
        )
    return NormalizedLayerEvidence(
        layer="document_intelligence",
        raw_score=result.suspicion_score,
        normalized_score=result.suspicion_score / 100.0,
        confidence=result.confidence,
        reliability=0.0,
        effective_score=0.0,
        evidence_count=len(signals),
        strong_evidence_count=sum(1 for s in signals if s.severity in {"medium", "high"}),
        status=status,
        summary=result.summary,
        limitations=list(result.limitations),
        signals=signals,
    )


def _unavailable(layer: str) -> NormalizedLayerEvidence:
    return NormalizedLayerEvidence(
        layer=layer,  # type: ignore[arg-type]
        raw_score=0,
        normalized_score=0.0,
        confidence=0.0,
        reliability=0.0,
        effective_score=0.0,
        status="unavailable",
        summary="This analysis layer was not available. That is not the same as finding no evidence.",
        limitations=["Layer was unavailable and is not treated as a clean result."],
    )


def _failed(
    layer: str,
    reason: str,
    raw_score: int,
    confidence: float,
    extra_limitations: list[str] | None = None,
) -> NormalizedLayerEvidence:
    notes = [reason, "A failed layer is not treated as a clean (no-evidence) result."]
    if extra_limitations:
        notes.extend(extra_limitations)
    return NormalizedLayerEvidence(
        layer=layer,  # type: ignore[arg-type]
        raw_score=raw_score,
        normalized_score=raw_score / 100.0,
        confidence=confidence,
        reliability=0.0,
        effective_score=0.0,
        status="failed",
        summary=reason,
        limitations=list(dict.fromkeys(notes)),
    )
