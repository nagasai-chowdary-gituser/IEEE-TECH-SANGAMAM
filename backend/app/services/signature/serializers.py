from __future__ import annotations

from app.models.signature import ReferenceSignature, SignatureComparison
from app.schemas.signature import (
    CertificateIntegrityAssessment,
    CombinedSignatureAssessment,
    ComparisonSignals,
    ReferenceSignatureResponse,
    SignatureComparisonResponse,
    SignatureFusion,
    SignatureQuality,
    SignatureRegion,
)
from app.utils.serializers import shorten_sha256


def to_reference_response(record: ReferenceSignature) -> ReferenceSignatureResponse:
    return ReferenceSignatureResponse(
        reference_id=record.id,
        label=record.label,
        original_filename=record.original_filename,
        file_type=record.file_type,
        file_size=record.file_size,
        width=record.width,
        height=record.height,
        quality_score=record.quality_score,
        created_at=record.created_at,
    )


def to_comparison_response(
    record: SignatureComparison,
    reference: ReferenceSignature | None,
    forensic_status=None,
) -> SignatureComparisonResponse:
    candidates = [SignatureRegion.model_validate(item) for item in _json_list(record.candidates_json)]
    selected = SignatureRegion.model_validate_json(record.selected_region_json) if record.selected_region_json else None
    fusion = SignatureFusion.model_validate_json(record.fusion_json) if record.fusion_json else None
    signals = ComparisonSignals.model_validate_json(record.comparison_json) if record.comparison_json else None
    combined = None
    certificate = None
    if record.combined_json:
        from json import loads

        raw = loads(record.combined_json)
        if isinstance(raw, dict) and "document_content" in raw:
            certificate = CertificateIntegrityAssessment.model_validate(raw)
        else:
            combined = CombinedSignatureAssessment.model_validate(raw)
    document_quality = SignatureQuality.model_validate_json(record.document_quality_json) if record.document_quality_json else None
    tamper = None
    if record.tamper_json:
        from json import loads

        tamper = loads(record.tamper_json)
    artifacts = {}
    if record.page_preview_artifact:
        artifacts["page_preview"] = record.page_preview_artifact
    if record.status == "COMPLETE" and record.selected_region_json:
        artifacts.update(
            {
                "document_signature": "document-signature",
                "document_normalized": "document-normalized",
                "document_contours": "document-contours",
                "region_highlight": "region-highlight",
            }
        )
        if record.fusion_json:
            artifacts["reference_normalized"] = "reference-normalized"
            artifacts["overlay"] = "overlay"
    return SignatureComparisonResponse(
        comparison_id=record.id,
        reference_id=record.reference_id,
        reference_label=reference.label if reference else None,
        forensic_analysis_id=record.forensic_analysis_id,
        status=record.status,
        pipeline_stage=record.pipeline_stage,
        original_filename=record.original_filename,
        file_type=record.file_type,
        file_size=record.file_size,
        sha256_short=shorten_sha256(record.sha256) if record.sha256 else None,
        candidates=candidates,
        selected_region=selected,
        document_quality=document_quality,
        reference_quality=_ref_quality(reference),
        signals=signals,
        fusion=fusion,
        tamper=tamper,
        combined=combined,
        certificate=certificate,
        overall_status=record.overall_status,
        artifacts=artifacts,
        forensic_status=forensic_status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error_message=record.error_message,
    )


def _json_list(raw: str | None) -> list:
    if not raw:
        return []
    from json import loads

    data = loads(raw)
    return data if isinstance(data, list) else []


def _ref_quality(reference: ReferenceSignature | None) -> SignatureQuality | None:
    if reference is None or reference.quality_score is None:
        return None
    meta = {}
    if reference.preprocessing_json:
        from json import loads

        meta = loads(reference.preprocessing_json)
    return SignatureQuality(
        score=reference.quality_score,
        width=reference.width or 0,
        height=reference.height or 0,
        ink_ratio=reference.ink_ratio or 0.0,
        sharpness=float(meta.get("sharpness") or 0.0),
        limitations=list(meta.get("limitations") or []),
    )
