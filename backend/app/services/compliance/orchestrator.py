from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.compliance import ComplianceAnalysis, ComplianceStatus
from app.models.document_analysis import AnalysisStatus
from app.repositories.analysis import AnalysisRepository
from app.repositories.compliance import ComplianceRepository
from app.schemas.compliance import (
    ComplianceListResponse,
    ComplianceResponse,
    ComplianceSummaryItem,
    IdentifierVerification,
)
from app.services.compliance.aggregation import aggregate
from app.services.compliance.extraction import extract_udyam_fields
from app.services.compliance.integrity import integrity_from_fusion
from app.services.compliance.providers import verify_gstin, verify_pan
from app.services.compliance.serializers import to_compliance_response
from app.services.intelligence.extraction import extract_document_text
from app.services.orchestration import AnalysisOrchestrator, execute_pipeline
from app.services.preprocessing.service import process_document
from app.utils.files import sanitize_original_filename
from app.utils.serializers import public_fusion
from app.utils.time import utcnow

logger = get_logger(__name__)

STAGE_SECURING = "securing_certificate"
STAGE_EXTRACTING = "extracting_certificate"
STAGE_VALIDATING = "validating_identifiers"
STAGE_PARALLEL = "verifying_parallel"
STAGE_AGGREGATING = "aggregating_compliance"
STAGE_COMPLETE = "complete"
STAGE_FAILED = "failed"


class ComplianceOrchestrator:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = ComplianceRepository(db)
        self.forensics = AnalysisOrchestrator(db, settings)

    def start(self, upload: UploadFile) -> ComplianceResponse:
        original = sanitize_original_filename(upload.filename)
        forensic = self.forensics.repo.create(original)
        try:
            forensic.status = AnalysisStatus.PROCESSING
            forensic.pipeline_stage = "securing_document"
            stored = self.forensics._store_and_hash(upload)
            forensic.stored_filename = stored.stored_filename
            forensic.file_path = str(stored.file_path)
            forensic.file_type = stored.file_type
            forensic.file_size = stored.file_size
            forensic.sha256 = stored.sha256
            forensic.updated_at = utcnow()
            self.forensics.repo.save(forensic)
        except HTTPException as exc:
            self.forensics._fail(forensic, exc.detail if isinstance(exc.detail, str) else "Upload failed.")
            raise
        record = self.repo.create(forensic.original_filename, forensic.id)
        record.status = ComplianceStatus.PROCESSING.value
        record.pipeline_stage = STAGE_SECURING
        self.repo.save(record)
        threading.Thread(target=execute_compliance, args=(record.id,), daemon=True).start()
        return self.get(record.id)

    def get(self, compliance_id: str) -> ComplianceResponse:
        record = self._require(compliance_id)
        forensic = self.forensics.repo.get(record.forensic_analysis_id) if record.forensic_analysis_id else None
        return to_compliance_response(record, forensic)

    def list_analyses(self, *, limit: int, offset: int) -> ComplianceListResponse:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        items, total = self.repo.list_analyses(limit=limit, offset=offset)
        summaries = []
        for row in items:
            pan = IdentifierVerification.model_validate_json(row.pan_result_json) if row.pan_result_json else None
            gst = IdentifierVerification.model_validate_json(row.gst_result_json) if row.gst_result_json else None
            integrity = None
            if row.integrity_result_json:
                from app.schemas.compliance import IntegrityAssessment

                integrity = IntegrityAssessment.model_validate_json(row.integrity_result_json)
            summaries.append(
                ComplianceSummaryItem(
                    compliance_id=row.id,
                    original_filename=row.original_filename,
                    enterprise_name=row.enterprise_name,
                    overall_status=row.overall_status,
                    pan_outcome=pan.outcome if pan else None,
                    gstin_outcome=gst.outcome if gst else None,
                    integrity_level=integrity.level if integrity else None,
                    created_at=row.created_at,
                )
            )
        return ComplianceListResponse(items=summaries, total=total, limit=limit, offset=offset)

    def _require(self, compliance_id: str) -> ComplianceAnalysis:
        record = self.repo.get(compliance_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance analysis not found.")
        return record


def execute_compliance(compliance_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    repo = ComplianceRepository(db)
    forensic_repo = AnalysisRepository(db)
    record = repo.get(compliance_id)
    if record is None:
        db.close()
        return
    forensic = forensic_repo.get(record.forensic_analysis_id) if record.forensic_analysis_id else None
    try:
        if forensic is None or not forensic.file_path:
            raise RuntimeError("missing_certificate")
        _stage(repo, record, STAGE_EXTRACTING)
        preprocessing = process_document(
            forensic.file_path,
            analysis_id=forensic.id,
            file_type=forensic.file_type,
            settings=settings,
        )
        extraction = extract_document_text(
            analysis_id=forensic.id,
            file_path=forensic.file_path,
            document_type=preprocessing.document_type,
            preprocessing=preprocessing,
            settings=settings,
        )
        fields = extract_udyam_fields(extraction)
        record.extracted_fields_json = fields.model_dump_json()
        record.enterprise_name = fields.enterprise_name
        repo.save(record)

        _stage(repo, record, STAGE_VALIDATING)
        _stage(repo, record, STAGE_PARALLEL)

        pan_result: IdentifierVerification | None = None
        gst_result: IdentifierVerification | None = None

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(
                    verify_pan,
                    fields.pan.value,
                    fields.pan.format_status,
                    settings,
                    fields.enterprise_name,
                    fields.registration_date,
                ): "pan",
                pool.submit(verify_gstin, fields.gstin.value, fields.gstin.format_status, settings): "gst",
                pool.submit(execute_pipeline, forensic.id): "forensic",
            }
            for future in as_completed(futures):
                label = futures[future]
                try:
                    result = future.result()
                except Exception:
                    logger.exception("compliance_parallel_failed label=%s", label)
                    if label == "pan":
                        pan_result = IdentifierVerification(
                            kind="pan",
                            extracted_value=fields.pan.value,
                            format_status=fields.pan.format_status,
                            outcome="error",
                            limitation="PAN verification could not be completed because of an internal error.",
                        )
                    elif label == "gst":
                        gst_result = IdentifierVerification(
                            kind="gstin",
                            extracted_value=fields.gstin.value,
                            format_status=fields.gstin.format_status,
                            outcome="error",
                            limitation="GSTIN verification could not be completed because of an internal error.",
                        )
                    continue
                if label == "pan":
                    pan_result = result
                    record.pan_result_json = pan_result.model_dump_json()
                    repo.save(record)
                elif label == "gst":
                    gst_result = result
                    record.gst_result_json = gst_result.model_dump_json()
                    repo.save(record)

        if pan_result is None:
            pan_result = IdentifierVerification(
                kind="pan",
                format_status=fields.pan.format_status,
                extracted_value=fields.pan.value,
                outcome="error",
                limitation="PAN verification did not return a result.",
            )
        if gst_result is None:
            gst_result = IdentifierVerification(
                kind="gstin",
                format_status=fields.gstin.format_status,
                extracted_value=fields.gstin.value,
                outcome="error",
                limitation="GSTIN verification did not return a result.",
            )
        record.pan_result_json = pan_result.model_dump_json()
        record.gst_result_json = gst_result.model_dump_json()

        forensic = forensic_repo.get(forensic.id)
        fusion = public_fusion(forensic.fusion_result_json) if forensic else None
        integrity = integrity_from_fusion(fusion, forensic.id if forensic else None)
        record.integrity_result_json = integrity.model_dump_json()

        _stage(repo, record, STAGE_AGGREGATING)
        aggregation = aggregate(pan_result, gst_result, integrity)
        record.aggregation_json = aggregation.model_dump_json()
        record.overall_status = aggregation.overall_status
        record.compliance_risk_score = aggregation.compliance_risk_score
        record.status = ComplianceStatus.COMPLETE.value
        record.pipeline_stage = STAGE_COMPLETE
        record.error_message = None
        record.updated_at = utcnow()
        repo.save(record)
        logger.info(
            "compliance_complete id=%s status=%s pan=%s gst=%s integrity=%s",
            compliance_id,
            aggregation.overall_status,
            pan_result.outcome,
            gst_result.outcome,
            integrity.level,
        )
    except Exception:
        logger.exception("compliance_failed id=%s", compliance_id)
        record.status = ComplianceStatus.FAILED.value
        record.pipeline_stage = STAGE_FAILED
        record.error_message = "Compliance analysis failed while processing the certificate."
        record.updated_at = utcnow()
        repo.save(record)
    finally:
        db.close()


def _stage(repo: ComplianceRepository, record: ComplianceAnalysis, stage: str) -> None:
    record.pipeline_stage = stage
    record.status = ComplianceStatus.PROCESSING.value
    record.updated_at = utcnow()
    repo.save(record)
