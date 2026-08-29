from __future__ import annotations

import threading
import time

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import AiIdentity
from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.document_analysis import AnalysisStatus, DocumentAnalysis
from app.repositories.analysis import AnalysisRepository
from app.schemas.ai import AIExplanation, AnalysisListResponse, AnalysisSummaryItem, AskResponse
from app.schemas.analysis import AnalysisResponse
from app.services.ai.analysis_context_builder import build_analysis_context
from app.services.ai.explanation_service import answer_question, generate_explanation
from app.services.ai.guard import (
    ask_cache_key,
    finish_ai_call,
    prepare_ai_request,
    start_provider_call,
    store_cached_ask,
    try_cached_ask,
)
from app.services.forensics.metadata import analyze_metadata
from app.services.forensics.visual_forensics_service import run_visual_forensics
from app.services.fusion.fusion_service import run_fusion
from app.services.intelligence.service import run_document_intelligence
from app.services.pipeline_stages import (
    STAGE_COMPLETE,
    STAGE_EXPLANATION,
    STAGE_FAILED,
    STAGE_FUSION,
    STAGE_INTELLIGENCE,
    STAGE_METADATA,
    STAGE_PREPROCESSING,
    STAGE_SECURING,
    STAGE_VISUAL,
)
from app.services.preprocessing.service import process_document
from app.services.report.pdf_report import build_report_pdf
from app.utils.files import StoredUpload, generate_stored_filename, sanitize_original_filename
from app.utils.files import detect_extension, validate_content_signature, validate_extension
from app.utils.hashing import sha256_bytes
from app.utils.serializers import public_fusion, to_analysis_response
from app.utils.time import utcnow

logger = get_logger(__name__)


class AnalysisOrchestrator:
    """Phase 5 pipeline: forensic layers remain source of truth; AI explains afterward."""

    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = AnalysisRepository(db)

    def analyze_upload(self, upload: UploadFile) -> AnalysisResponse:
        original_name = sanitize_original_filename(upload.filename)
        record = self.repo.create(original_name)
        analysis_id = record.id
        logger.info("pipeline_started analysis_id=%s stage=create", analysis_id)
        try:
            record.status = AnalysisStatus.PROCESSING
            record.pipeline_stage = STAGE_SECURING
            record.updated_at = utcnow()
            self.repo.save(record)
            stored = self._store_and_hash(upload)
            record.stored_filename = stored.stored_filename
            record.file_path = str(stored.file_path)
            record.file_type = stored.file_type
            record.file_size = stored.file_size
            record.sha256 = stored.sha256
            record.updated_at = utcnow()
            self.repo.save(record)
        except HTTPException as exc:
            self._fail(record, _client_safe_error(exc), persist_stage=STAGE_FAILED)
            raise
        except Exception:
            logger.exception("pipeline_failed analysis_id=%s stage=store", analysis_id)
            self._fail(record, "The document could not be stored.", persist_stage=STAGE_FAILED)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The document could not be stored.",
            )
        thread = threading.Thread(target=execute_pipeline, args=(analysis_id,), daemon=True)
        thread.start()
        return to_analysis_response(record)

    def get_analysis(self, analysis_id: str) -> AnalysisResponse:
        record = self._require(analysis_id)
        return to_analysis_response(record)

    def list_analyses(self, *, limit: int, offset: int) -> AnalysisListResponse:
        limit = max(1, min(limit, 100))
        offset = max(0, offset)
        items, total = self.repo.list_analyses(limit=limit, offset=offset)
        return AnalysisListResponse(
            items=[
                AnalysisSummaryItem(
                    analysis_id=row.id,
                    original_filename=row.original_filename,
                    document_type=row.document_type,
                    status=row.status,
                    risk_level=row.risk_level,
                    overall_risk_score=row.overall_risk_score,
                    pipeline_stage=row.pipeline_stage,
                    created_at=row.created_at,
                )
                for row in items
            ],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_explanation(self, analysis_id: str, identity: AiIdentity | None = None) -> AIExplanation:
        record = self._require(analysis_id)
        if record.status == AnalysisStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis is still running. The explanation will be available when processing finishes.",
            )
        if record.ai_explanation_json:
            return AIExplanation.model_validate_json(record.ai_explanation_json)
        identity = identity or _anonymous_identity()
        try:
            prepare_ai_request(
                self.db,
                subject=identity.subject,
                ip=identity.ip,
                authenticated=identity.authenticated,
                settings=self.settings,
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                finish_ai_call(
                    self.db,
                    subject=identity.subject,
                    ip=identity.ip,
                    endpoint="explanation",
                    settings=self.settings,
                    cached=False,
                    rate_limited=True,
                    error_class="rate_limited",
                )
            raise
        start_provider_call()
        explanation = _build_explanation(record, self.settings)
        finish_ai_call(
            self.db,
            subject=identity.subject,
            ip=identity.ip,
            endpoint="explanation",
            settings=self.settings,
            cached=False,
            rate_limited=False,
        )
        if record.status == AnalysisStatus.COMPLETE:
            record.ai_explanation_json = explanation.model_dump_json()
            record.ai_explanation_created_at = utcnow()
            self.repo.save(record)
        return explanation

    def ask(self, analysis_id: str, question: str, identity: AiIdentity | None = None) -> AskResponse:
        cleaned = question.strip()
        if not cleaned:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Question cannot be empty.")
        if len(cleaned) > 800:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question is too long. Use at most 800 characters.",
            )
        record = self._require(analysis_id)
        if record.status == AnalysisStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis is still running. Ask questions after it completes.",
            )
        identity = identity or _anonymous_identity()
        cache_key = ask_cache_key(analysis=record, question=cleaned, model=self.settings.ai_model)
        cached = try_cached_ask(cache_key, enabled=self.settings.ai_cache_enabled)
        if cached is not None:
            finish_ai_call(
                self.db,
                subject=identity.subject,
                ip=identity.ip,
                endpoint="ask",
                settings=self.settings,
                cached=True,
                rate_limited=False,
            )
            return cached
        try:
            prepare_ai_request(
                self.db,
                subject=identity.subject,
                ip=identity.ip,
                authenticated=identity.authenticated,
                settings=self.settings,
            )
        except HTTPException as exc:
            if exc.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
                finish_ai_call(
                    self.db,
                    subject=identity.subject,
                    ip=identity.ip,
                    endpoint="ask",
                    settings=self.settings,
                    cached=False,
                    rate_limited=True,
                    error_class="rate_limited",
                )
            raise
        context = build_analysis_context(record)
        fusion = public_fusion(record.fusion_result_json)
        start_provider_call()
        response = answer_question(question=cleaned, fusion=fusion, context=context, settings=self.settings)
        finish_ai_call(
            self.db,
            subject=identity.subject,
            ip=identity.ip,
            endpoint="ask",
            settings=self.settings,
            cached=False,
            rate_limited=False,
        )
        store_cached_ask(
            cache_key,
            response,
            ttl_seconds=self.settings.ai_cache_ttl_seconds,
            enabled=self.settings.ai_cache_enabled,
        )
        return response

    def get_report(self, analysis_id: str) -> bytes:
        record = self._require(analysis_id)
        if record.status == AnalysisStatus.PROCESSING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Analysis is still running. The report will be available when processing finishes.",
            )
        try:
            return build_report_pdf(record, self.settings)
        except Exception:
            logger.exception("report_generation_failed analysis_id=%s", analysis_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="The forensic report could not be generated.",
            )

    def _require(self, analysis_id: str) -> DocumentAnalysis:
        record = self.repo.get(analysis_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found.")
        return record

    def _store_and_hash(self, upload: UploadFile) -> StoredUpload:
        original_filename = sanitize_original_filename(upload.filename)
        extension = detect_extension(original_filename)
        validate_extension(extension)
        content = self._read_limited(upload)
        digest = sha256_bytes(content)
        validate_content_signature(extension, content)

        stored_filename = generate_stored_filename(extension)
        destination = self.settings.upload_path / stored_filename
        resolved = destination.resolve()
        if not str(resolved).startswith(str(self.settings.upload_path)):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid storage path.")
        resolved.write_bytes(content)
        return StoredUpload(
            original_filename=original_filename,
            stored_filename=stored_filename,
            file_path=resolved,
            file_type=extension.lstrip("."),
            file_size=len(content),
            sha256=digest,
            content=content,
        )

    def _read_limited(self, upload: UploadFile) -> bytes:
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > self.settings.max_upload_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File exceeds the maximum upload size of {self.settings.max_upload_size_mb} MB.",
                )
            chunks.append(chunk)
        content = b"".join(chunks)
        if not content:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")
        return content

    def _fail(self, record: DocumentAnalysis, message: str, persist_stage: str = STAGE_FAILED) -> None:
        try:
            self.db.rollback()
            record.status = AnalysisStatus.FAILED
            record.pipeline_stage = persist_stage
            record.error_message = message
            record.updated_at = utcnow()
            self.db.add(record)
            self.db.commit()
            self.db.refresh(record)
        except Exception:
            self.db.rollback()
            logger.exception("pipeline_fail_persist_error analysis_id=%s", record.id)


def execute_pipeline(analysis_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    repo = AnalysisRepository(db)
    record = repo.get(analysis_id)
    if record is None:
        db.close()
        return
    started = time.perf_counter()
    try:
        if not record.file_path:
            raise RuntimeError("missing_file")
        _set_stage(repo, record, STAGE_PREPROCESSING)
        preprocess_started = time.perf_counter()
        preprocessing = process_document(
            record.file_path,
            analysis_id=analysis_id,
            file_type=record.file_type,
            settings=settings,
        )
        record.document_type = preprocessing.document_type
        record.preprocessing_result_json = preprocessing.model_dump_json()
        repo.save(record)
        logger.info(
            "pipeline_stage analysis_id=%s stage=preprocessing success duration_ms=%s document_type=%s",
            analysis_id,
            int((time.perf_counter() - preprocess_started) * 1000),
            preprocessing.document_type,
        )

        _set_stage(repo, record, STAGE_METADATA)
        metadata_started = time.perf_counter()
        metadata = analyze_metadata(record.file_path, preprocessing.document_type)
        record.metadata_result_json = metadata.model_dump_json()
        repo.save(record)
        logger.info(
            "pipeline_stage analysis_id=%s stage=metadata_forensics success duration_ms=%s suspicion=%s",
            analysis_id,
            int((time.perf_counter() - metadata_started) * 1000),
            metadata.suspicion_score,
        )

        _set_stage(repo, record, STAGE_VISUAL)
        visual_started = time.perf_counter()
        visual = run_visual_forensics(
            analysis_id=analysis_id,
            document_type=preprocessing.document_type,
            file_type=record.file_type,
            preprocessing=preprocessing,
            settings=settings,
        )
        record.ela_result_json = visual.ela.model_dump_json() if visual.ela else None
        record.copy_move_result_json = visual.copy_move.model_dump_json() if visual.copy_move else None
        record.visual_forensics_result_json = visual.model_dump_json()
        repo.save(record)
        logger.info(
            "pipeline_stage analysis_id=%s stage=visual_forensics success duration_ms=%s ela=%s copy_move=%s",
            analysis_id,
            int((time.perf_counter() - visual_started) * 1000),
            visual.ela.suspicion_score if visual.ela else None,
            visual.copy_move.suspicion_score if visual.copy_move else None,
        )

        _set_stage(repo, record, STAGE_INTELLIGENCE)
        intelligence_started = time.perf_counter()
        intelligence = run_document_intelligence(
            analysis_id=analysis_id,
            file_path=record.file_path,
            document_type=preprocessing.document_type,
            preprocessing=preprocessing,
            settings=settings,
        )
        record.document_intelligence_result_json = intelligence.model_dump_json()
        repo.save(record)
        logger.info(
            "pipeline_stage analysis_id=%s stage=document_intelligence success duration_ms=%s score=%s quality=%s",
            analysis_id,
            int((time.perf_counter() - intelligence_started) * 1000),
            intelligence.suspicion_score,
            intelligence.extraction.overall_quality,
        )

        _set_stage(repo, record, STAGE_FUSION)
        fusion_started = time.perf_counter()
        fusion = run_fusion(metadata, visual.ela, visual.copy_move, intelligence)
        record.fusion_result_json = fusion.model_dump_json()
        record.overall_risk_score = fusion.overall_risk_score
        record.risk_level = fusion.risk_level
        record.assessment_confidence = fusion.assessment_confidence
        record.analysis_coverage = fusion.analysis_coverage
        record.final_score = fusion.overall_risk_score
        record.final_status = fusion.risk_level
        repo.save(record)
        logger.info(
            "pipeline_stage analysis_id=%s stage=evidence_fusion success duration_ms=%s risk=%s level=%s",
            analysis_id,
            int((time.perf_counter() - fusion_started) * 1000),
            fusion.overall_risk_score,
            fusion.risk_level,
        )

        _set_stage(repo, record, STAGE_EXPLANATION)
        try:
            start_provider_call()
            explanation = _build_explanation(record, settings)
            record.ai_explanation_json = explanation.model_dump_json()
            record.ai_explanation_created_at = utcnow()
            finish_ai_call(
                db,
                subject="system",
                ip="pipeline",
                endpoint="pipeline.explanation",
                settings=settings,
                cached=False,
                rate_limited=False,
            )
        except Exception:
            logger.exception("explanation_stage_failed analysis_id=%s", analysis_id)

        record.status = AnalysisStatus.COMPLETE
        record.pipeline_stage = STAGE_COMPLETE
        record.error_message = None
        record.updated_at = utcnow()
        repo.save(record)
        logger.info(
            "pipeline_complete analysis_id=%s status=COMPLETE duration_ms=%s",
            analysis_id,
            int((time.perf_counter() - started) * 1000),
        )
    except HTTPException as exc:
        _fail_in_session(repo, record, _client_safe_error(exc))
    except Exception:
        logger.exception("pipeline_failed analysis_id=%s stage=unhandled", analysis_id)
        _fail_in_session(repo, record, "Analysis failed while processing the document.")
    finally:
        db.close()


def _anonymous_identity() -> AiIdentity:
    return AiIdentity(subject="ip:unknown", user_id=None, ip="unknown", authenticated=False)


def _build_explanation(record: DocumentAnalysis, settings: Settings) -> AIExplanation:
    context = build_analysis_context(record)
    fusion = public_fusion(record.fusion_result_json)
    return generate_explanation(fusion=fusion, context=context, settings=settings)


def _set_stage(repo: AnalysisRepository, record: DocumentAnalysis, stage: str) -> None:
    record.pipeline_stage = stage
    record.status = AnalysisStatus.PROCESSING
    record.updated_at = utcnow()
    repo.save(record)


def _fail_in_session(repo: AnalysisRepository, record: DocumentAnalysis, message: str) -> None:
    record.status = AnalysisStatus.FAILED
    record.pipeline_stage = STAGE_FAILED
    record.error_message = message
    record.updated_at = utcnow()
    repo.save(record)


def _client_safe_error(exc: HTTPException) -> str:
    if isinstance(exc.detail, str):
        return exc.detail
    return "The document could not be processed."
