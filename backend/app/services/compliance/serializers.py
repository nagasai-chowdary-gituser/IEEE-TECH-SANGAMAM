from __future__ import annotations

from app.models.compliance import ComplianceAnalysis
from app.models.document_analysis import AnalysisStatus, DocumentAnalysis
from app.schemas.compliance import (
    CertificateFields,
    ComplianceAggregation,
    ComplianceResponse,
    IdentifierVerification,
    IntegrityAssessment,
)
from app.utils.serializers import public_fusion, shorten_sha256, to_analysis_response


def to_compliance_response(record: ComplianceAnalysis, forensic: DocumentAnalysis | None) -> ComplianceResponse:
    fields = CertificateFields.model_validate_json(record.extracted_fields_json) if record.extracted_fields_json else None
    pan = IdentifierVerification.model_validate_json(record.pan_result_json) if record.pan_result_json else None
    gstin = IdentifierVerification.model_validate_json(record.gst_result_json) if record.gst_result_json else None
    integrity = IntegrityAssessment.model_validate_json(record.integrity_result_json) if record.integrity_result_json else None
    aggregation = ComplianceAggregation.model_validate_json(record.aggregation_json) if record.aggregation_json else None
    forensic_status = forensic.status if forensic else None
    return ComplianceResponse(
        compliance_id=record.id,
        forensic_analysis_id=record.forensic_analysis_id,
        status=record.status,
        pipeline_stage=record.pipeline_stage,
        original_filename=record.original_filename,
        file_type=forensic.file_type if forensic else None,
        file_size=forensic.file_size if forensic else None,
        sha256_short=shorten_sha256(forensic.sha256) if forensic else None,
        certificate_fields=fields,
        pan=pan,
        gstin=gstin,
        integrity=integrity,
        aggregation=aggregation,
        overall_status=record.overall_status,  # type: ignore[arg-type]
        compliance_risk_score=record.compliance_risk_score,
        forensic_status=forensic_status,
        created_at=record.created_at,
        updated_at=record.updated_at,
        error_message=record.error_message,
    )


def forensic_public(record: DocumentAnalysis | None):
    if record is None:
        return None
    if record.status == AnalysisStatus.PROCESSING:
        return to_analysis_response(record)
    return to_analysis_response(record)


def fusion_of(record: DocumentAnalysis | None):
    if record is None:
        return None
    return public_fusion(record.fusion_result_json)
