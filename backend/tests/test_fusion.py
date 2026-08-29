from __future__ import annotations

from app.schemas.intelligence import (
    DocumentClassification,
    DocumentIntelligenceResult,
    ExtractionResult,
    LogicalCheck,
)
from app.schemas.metadata import MetadataForensicsResult, MetadataSignal
from app.schemas.visual import (
    BoundingBox,
    CopyMoveForensicsResult,
    CopyMovePageMetrics,
    CopyMovePageResult,
    CopyMoveRegion,
    ElaForensicsResult,
    ElaPageMetrics,
    ElaPageResult,
    ForensicEvidence,
)
from app.services.fusion.evidence_normalizer import normalize_layers
from app.services.fusion.fusion_service import run_fusion


def _signal(sid: str, finding: str, severity: str = "medium", impact: int = 20) -> MetadataSignal:
    return MetadataSignal(id=sid, finding=finding, severity=severity, score_impact=impact, detail=finding)


def _metadata(score: int = 5, confidence: float = 0.88, signals: list[MetadataSignal] | None = None) -> MetadataForensicsResult:
    return MetadataForensicsResult(
        suspicion_score=score,
        flagged=score >= 40,
        confidence=confidence,
        signals=signals or [],
        summary="Metadata summary.",
    )


def _ela(
    score: int = 4,
    confidence: float = 0.86,
    quality: str = "high",
    *,
    module_error: str | None = None,
    signals: list[MetadataSignal] | None = None,
    artifact: bool = False,
) -> ElaForensicsResult:
    evidence = []
    if artifact:
        evidence = [ForensicEvidence(type="ela_heatmap", artifact_id="p001_ela", description="ELA heatmap")]
    return ElaForensicsResult(
        suspicion_score=score,
        flagged=score >= 40,
        confidence=confidence,
        analysis_quality=quality,  # type: ignore[arg-type]
        pages=[
            ElaPageResult(
                page_number=1,
                suspicion_score=score,
                confidence=confidence,
                flagged=score >= 40,
                metrics=ElaPageMetrics(mean_error=1.0, std_error=0.2, max_error=3.0, high_error_ratio=0.01),
                evidence=evidence,
                signals=signals or [],
                limitations=["ELA interpretation is limited for this source format."] if quality == "limited" else [],
            )
        ],
        summary="ELA summary.",
        module_error=module_error,
    )


def _copy_move(
    score: int = 0,
    confidence: float = 0.8,
    *,
    verified: int = 0,
    clusters: int = 0,
    keypoints: int = 120,
    raw_matches: int = 10,
    module_error: str | None = None,
    signals: list[MetadataSignal] | None = None,
) -> CopyMoveForensicsResult:
    regions = []
    evidence = []
    if verified or clusters:
        regions = [
            CopyMoveRegion(
                region_id="r1",
                source_bbox=BoundingBox(x=1, y=1, width=20, height=20),
                matched_bbox=BoundingBox(x=80, y=80, width=20, height=20),
                match_confidence=0.9,
                evidence_strength="high",
            )
        ]
        evidence = [ForensicEvidence(type="overlay", artifact_id="p001_copy_move", description="Copy-move overlay")]
        signals = signals or [
            _signal("copy_move_verified_cluster", "Repeated visual pattern detected.", "high", 40)
        ]
    return CopyMoveForensicsResult(
        suspicion_score=score,
        flagged=score >= 40,
        confidence=confidence,
        pages=[
            CopyMovePageResult(
                page_number=1,
                suspicion_score=score,
                confidence=confidence,
                flagged=score >= 40,
                metrics=CopyMovePageMetrics(
                    keypoints_detected=keypoints,
                    raw_matches=raw_matches,
                    filtered_matches=min(raw_matches, 8),
                    geometrically_verified_matches=verified,
                    suspicious_clusters=clusters,
                ),
                regions=regions,
                evidence=evidence,
                signals=signals or [],
            )
        ],
        summary="Copy-move summary.",
        module_error=module_error,
    )


def _intelligence(
    score: int = 6,
    confidence: float = 0.84,
    quality: str = "high",
    *,
    module_error: str | None = None,
    checks: list[LogicalCheck] | None = None,
    limitations: list[str] | None = None,
) -> DocumentIntelligenceResult:
    return DocumentIntelligenceResult(
        extraction=ExtractionResult(
            overall_quality=quality,  # type: ignore[arg-type]
            overall_confidence=0.9 if quality == "high" else 0.4,
            pages=[],
            tesseract_available=True,
        ),
        classification=DocumentClassification(
            document_class="generic_document",
            confidence=0.4,
            rationale="Generic document.",
        ),
        logical_checks=checks or [],
        suspicion_score=score,
        flagged=score >= 40,
        confidence=confidence,
        summary="Document intelligence summary.",
        limitations=limitations or [],
        module_error=module_error,
    )


def test_all_low_scores_high_coverage_is_low() -> None:
    result = run_fusion(_metadata(), _ela(), _copy_move(), _intelligence())
    assert result.risk_level == "LOW"
    assert result.analysis_coverage >= 0.7
    assert result.assessment_confidence >= 0.5
    assert result.overall_risk_score < 28
    assert result.top_findings == []
    assert result.recommended_action == "NO_ADDITIONAL_ACTION"


def test_high_raw_low_reliability_is_not_high() -> None:
    result = run_fusion(
        _metadata(90, 0.18, [_signal("photoshop", "Editor tag present.", "high", 40)]),
        _ela(),
        _copy_move(),
        _intelligence(),
    )
    meta = next(c for c in result.layer_contributions if c.layer == "metadata")
    assert meta.raw_score == 90
    assert meta.reliability < 0.25
    assert result.risk_level != "HIGH"
    assert result.overall_risk_score < 70


def test_isolated_strong_copy_move_is_elevated() -> None:
    result = run_fusion(
        _metadata(),
        _ela(),
        _copy_move(92, 0.93, verified=8, clusters=3),
        _intelligence(),
    )
    assert result.risk_level in {"ELEVATED", "HIGH"}
    assert result.overall_risk_score >= 48
    assert result.corroboration.strength == "none"
    assert "independent corroboration" in result.assessment_summary.lower()
    assert any(item.layer == "copy_move" for item in result.top_findings)


def test_independent_layers_receive_corroboration() -> None:
    result = run_fusion(
        _metadata(50, 0.85, [_signal("pdf_mod_date", "Modification date is after creation.", "medium", 25)]),
        _ela(48, 0.82, signals=[_signal("ela_local", "Localized residual cluster.", "medium", 24)], artifact=True),
        _copy_move(),
        _intelligence(
            52,
            0.88,
            checks=[
                LogicalCheck(
                    check_id="invoice_total_consistency",
                    category="arithmetic",
                    result="fail",
                    severity="high",
                    score_impact=30,
                    confidence=0.9,
                    explanation="Line items do not sum to the stated total.",
                )
            ],
        ),
    )
    assert len(result.corroboration.independent_layers_with_evidence) >= 3
    assert result.corroboration.strength in {"moderate", "strong"}
    assert "Independent corroboration" in result.corroboration.description
    assert "cross-layer" in result.assessment_summary.lower() or "independent" in result.assessment_summary.lower()


def test_related_metadata_signals_are_grouped() -> None:
    signals = [
        _signal(f"pdf_timestamp_{i}", "Timestamp inconsistency.", "medium", 15)
        for i in range(5)
    ]
    layers = normalize_layers(_metadata(40, 0.8, signals), _ela(), _copy_move(), _intelligence())
    meta = next(item for item in layers if item.layer == "metadata")
    assert meta.evidence_count == 1
    result = run_fusion(_metadata(40, 0.8, signals), _ela(), _copy_move(), _intelligence())
    assert result.corroboration.independent_layers_with_evidence.count("metadata") <= 1


def test_failed_layers_are_not_treated_as_clean() -> None:
    failed = run_fusion(
        _metadata(),
        _ela(module_error="ELA engine failed."),
        _copy_move(module_error="Copy-move engine failed."),
        _intelligence(module_error="Text extraction failed.", quality="failed"),
    )
    clean = run_fusion(_metadata(), _ela(), _copy_move(), _intelligence())
    assert failed.risk_level == "INCONCLUSIVE"
    assert failed.analysis_coverage < clean.analysis_coverage
    statuses = {item.layer: item.status for item in failed.layer_contributions}
    assert statuses["ela"] == "failed"
    assert statuses["copy_move"] == "failed"
    assert "not treated as a clean" in failed.layer_contributions[1].summary.lower()
    assert any("failed" in note.lower() for note in failed.limitations)


def test_unavailable_is_not_the_same_as_no_evidence() -> None:
    unavailable = run_fusion(_metadata(), None, None, None)
    none_found = run_fusion(_metadata(), _ela(), _copy_move(), _intelligence())
    statuses = {item.layer: item.status for item in unavailable.layer_contributions}
    assert statuses["ela"] == "unavailable"
    assert statuses["copy_move"] == "unavailable"
    assert "not the same as finding no evidence" in unavailable.layer_contributions[1].summary.lower()
    assert none_found.layer_contributions[1].status == "available"
    assert "no meaningful" in none_found.layer_contributions[1].summary.lower()
    assert unavailable.risk_level == "INCONCLUSIVE"


def test_low_coverage_clean_result_is_inconclusive() -> None:
    result = run_fusion(_metadata(4, 0.9), None, None, None)
    assert result.risk_level == "INCONCLUSIVE"
    assert result.analysis_coverage < 0.4
    assert result.overall_risk_score < 28
    assert "inconclusive" in result.assessment_summary.lower()


def test_fusion_is_deterministic_and_bounded() -> None:
    args = (
        _metadata(35, 0.7, [_signal("pdf_producer", "Producer indicates an editor.", "medium", 20)]),
        _ela(12, 0.6, quality="limited"),
        _copy_move(8, 0.5),
        _intelligence(10, 0.7, quality="medium"),
    )
    first = run_fusion(*args)
    second = run_fusion(*args)
    assert first.model_dump() == second.model_dump()
    assert 0 <= first.overall_risk_score <= 100
    assert 0.0 <= first.assessment_confidence <= 1.0
    assert 0.0 <= first.analysis_coverage <= 1.0


def test_explanation_references_actual_evidence() -> None:
    result = run_fusion(
        _metadata(),
        _ela(55, 0.8, signals=[_signal("ela_local", "Localized residual cluster on page 1.", "high", 30)], artifact=True),
        _copy_move(60, 0.88, verified=4, clusters=2),
        _intelligence(),
    )
    assert result.top_findings
    assert "Localized residual cluster on page 1." in {item.finding for item in result.top_findings} or any(
        "Repeated visual pattern" in item.finding for item in result.top_findings
    )
    joined = result.assessment_summary.lower()
    assert "ai thinks" not in joined
    assert "forgery confirmed" not in joined
    assert result.top_findings[0].evidence_reference in {"p001_ela", "p001_copy_move"}


def test_no_evidence_does_not_fabricate_findings() -> None:
    result = run_fusion(_metadata(), _ela(), _copy_move(), _intelligence())
    assert result.top_findings == []
    assert "no meaningful manipulation evidence" in result.assessment_summary.lower()


def test_limitations_appear_for_limited_and_failed_modules() -> None:
    result = run_fusion(
        _metadata(),
        _ela(8, 0.5, quality="limited"),
        _copy_move(module_error="Copy-move engine failed."),
        _intelligence(12, 0.4, quality="low", limitations=["OCR extraction quality was low."]),
    )
    text = " ".join(result.limitations).lower()
    assert "ela interpretation is limited" in text
    assert "copy-move" in text and "failed" in text
    assert "ocr extraction quality was low" in text or "limited" in text


def test_isolated_and_corroborated_wording() -> None:
    isolated = run_fusion(_metadata(), _ela(), _copy_move(92, 0.93, verified=6, clusters=2), _intelligence())
    assert "did not provide independent corroboration" in isolated.assessment_summary
    corroborated = run_fusion(
        _metadata(55, 0.86, [_signal("pdf_mod_date", "Modification date is after creation.", "high", 30)]),
        _ela(50, 0.8, signals=[_signal("ela_local", "Localized residual cluster.", "medium", 24)]),
        _copy_move(),
        _intelligence(),
    )
    assert "independent" in corroborated.assessment_summary.lower()
    assert corroborated.corroboration.strength in {"weak", "moderate", "strong"}
