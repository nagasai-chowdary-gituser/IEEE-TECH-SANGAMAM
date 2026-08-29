from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import cv2
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal
from app.core.logging import get_logger
from app.models.document_analysis import AnalysisStatus
from app.models.signature import ReferenceSignature, SignatureComparison, SignatureComparisonStatus
from app.repositories.analysis import AnalysisRepository
from app.repositories.signature import SignatureRepository
from app.schemas.signature import (
    ManualRegionRequest,
    ReferenceListResponse,
    SignatureComparisonListResponse,
    SignatureComparisonSummary,
    SignatureRegion,
)
from app.services.compliance.integrity import integrity_from_fusion
from app.services.orchestration import AnalysisOrchestrator, execute_pipeline
from app.services.preprocessing.service import process_document
from app.services.signature.certificate_fusion import fuse_certificate
from app.services.signature.compare import compare_normalized, render_contours, render_overlay
from app.services.signature.content import document_content_integrity
from app.services.signature.detect import crop_region, detect_signature_regions
from app.services.signature.fields import certificate_fields
from app.services.signature.fusion import fuse_comparison
from app.services.signature.overlays import collect_overlays
from app.services.signature.preprocess import assess_and_normalize, decode_image, load_bgr, normalize_crop
from app.services.signature.serializers import to_comparison_response, to_reference_response
from app.services.signature.signature_integrity import analyze_signature_integrity, awaiting_selection
from app.services.signature.storage import reference_dir, signature_dir, write_png
from app.utils.files import detect_extension, generate_stored_filename, sanitize_original_filename
from app.utils.hashing import sha256_bytes
from app.utils.serializers import public_copy_move, public_ela, public_fusion, public_intelligence
from app.utils.time import utcnow

logger = get_logger(__name__)

IMAGE_TYPES = {".png", ".jpg", ".jpeg"}
FORENSIC_STAGE_MAP = {
    "securing_document": "securing_document",
    "preprocessing": "preprocessing_document",
    "metadata_analysis": "visual_forensics",
    "visual_forensics": "visual_forensics",
    "document_intelligence": "extracting_text",
    "evidence_fusion": "checking_suspicious_regions",
    "preparing_explanation": "fusing_evidence",
    "complete": "detecting_signatures",
}


class SignatureOrchestrator:
    def __init__(self, db: Session, settings: Settings) -> None:
        self.db = db
        self.settings = settings
        self.repo = SignatureRepository(db)
        self.forensics = AnalysisOrchestrator(db, settings)

    def create_reference(self, upload: UploadFile, label: str | None) -> ReferenceSignature:
        original = sanitize_original_filename(upload.filename)
        if detect_extension(original) not in IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reference signatures must be PNG or JPEG images.",
            )
        stored = self.forensics._store_and_hash(upload)
        try:
            image = decode_image(stored.content)
            _, normalized, quality = assess_and_normalize(image)
        except HTTPException:
            stored.file_path.unlink(missing_ok=True)
            raise
        dest_dir = reference_dir(self.settings)
        stored_name = generate_stored_filename(".png")
        dest = dest_dir / stored_name
        dest.write_bytes(stored.file_path.read_bytes())
        write_png(dest_dir / f"{dest.stem}-normalized.png", normalized)
        stored.file_path.unlink(missing_ok=True)
        record = ReferenceSignature(
            label=(label or "").strip()[:128] or None,
            original_filename=stored.original_filename,
            stored_filename=stored_name,
            file_path=str(dest),
            file_type="png",
            file_size=dest.stat().st_size,
            sha256=sha256_bytes(dest.read_bytes()),
            width=quality.width,
            height=quality.height,
            ink_ratio=quality.ink_ratio,
            quality_score=quality.score,
            preprocessing_json=quality.model_dump_json(),
        )
        return self.repo.create_reference(record)

    def list_references(self) -> ReferenceListResponse:
        items = self.repo.list_references()
        return ReferenceListResponse(items=[to_reference_response(item) for item in items], total=len(items))

    def delete_reference(self, reference_id: str) -> None:
        record = self._require_reference(reference_id)
        path = Path(record.file_path)
        if path.is_file() and str(path.resolve()).startswith(str(self.settings.upload_path.resolve())):
            path.unlink(missing_ok=True)
            path.with_name(f"{path.stem}-normalized.png").unlink(missing_ok=True)
        self.repo.delete_reference(record)

    def start_comparison(self, upload: UploadFile, reference_id: str | None) -> SignatureComparisonResponse:
        reference = self._require_reference(reference_id) if reference_id else None
        forensic = self.forensics.repo.create(sanitize_original_filename(upload.filename))
        try:
            forensic.status = AnalysisStatus.PROCESSING
            stored = self.forensics._store_and_hash(upload)
            forensic.stored_filename = stored.stored_filename
            forensic.file_path = str(stored.file_path)
            forensic.file_type = stored.file_type
            forensic.file_size = stored.file_size
            forensic.sha256 = stored.sha256
            self.forensics.repo.save(forensic)
        except HTTPException:
            self.forensics._fail(forensic, "The document could not be stored.")
            raise
        record = SignatureComparison(
            reference_id=reference.id if reference else None,
            forensic_analysis_id=forensic.id,
            original_filename=forensic.original_filename,
            stored_filename=forensic.stored_filename,
            file_path=forensic.file_path,
            file_type=forensic.file_type,
            file_size=forensic.file_size,
            sha256=forensic.sha256,
            status=SignatureComparisonStatus.PROCESSING.value,
            pipeline_stage="securing_document",
        )
        self.repo.create_comparison(record)
        threading.Thread(target=execute_signature_comparison, args=(record.id,), daemon=True).start()
        return self.get_comparison(record.id)

    def apply_region(self, comparison_id: str, payload: ManualRegionRequest) -> SignatureComparisonResponse:
        record = self._require_comparison(comparison_id)
        if record.status not in {SignatureComparisonStatus.NEEDS_REGION.value, SignatureComparisonStatus.COMPLETE.value}:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This analysis is not waiting for a signature region.")
        region = SignatureRegion(
            page_number=payload.page_number,
            x=payload.x,
            y=payload.y,
            width=payload.width,
            height=payload.height,
            score=1.0,
            source="manual",
            reason="Region selected by the reviewer.",
        )
        record.selected_region_json = region.model_dump_json()
        record.status = SignatureComparisonStatus.PROCESSING.value
        record.pipeline_stage = "analyzing_signature_integrity"
        record.error_message = None
        self.repo.save_comparison(record)
        threading.Thread(target=execute_signature_compare_only, args=(record.id,), daemon=True).start()
        return self.get_comparison(record.id)

    def get_comparison(self, comparison_id: str) -> SignatureComparisonResponse:
        record = self._require_comparison(comparison_id)
        reference = self.repo.get_reference(record.reference_id) if record.reference_id else None
        forensic = self.forensics.repo.get(record.forensic_analysis_id) if record.forensic_analysis_id else None
        return to_comparison_response(record, reference, forensic.status if forensic else None)

    def list_comparisons(self, *, limit: int, offset: int) -> SignatureComparisonListResponse:
        items, total = self.repo.list_comparisons(limit=limit, offset=offset)
        summaries = []
        for row in items:
            reference = self.repo.get_reference(row.reference_id) if row.reference_id else None
            tamper = None
            combined = None
            certificate_status = None
            if row.tamper_json:
                tamper = json.loads(row.tamper_json).get("level")
            if row.combined_json:
                combined = json.loads(row.combined_json)
                certificate_status = combined.get("overall_status") if "document_content" in combined else None
            summaries.append(
                SignatureComparisonSummary(
                    comparison_id=row.id,
                    original_filename=row.original_filename,
                    reference_label=reference.label if reference else None,
                    overall_status=row.overall_status,
                    certificate_status=certificate_status,
                    tamper_level=tamper,
                    final_score=(combined or {}).get("final_score"),
                    originality_score=(combined or {}).get("originality_score"),
                    originality_verdict=(combined or {}).get("originality_verdict"),
                    overall_verdict=(combined or {}).get("overall_verdict"),
                    created_at=row.created_at,
                )
            )
        return SignatureComparisonListResponse(items=summaries, total=total, limit=limit, offset=offset)

    def _require_reference(self, reference_id: str) -> ReferenceSignature:
        record = self.repo.get_reference(reference_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference signature not found.")
        return record

    def _require_comparison(self, comparison_id: str) -> SignatureComparison:
        record = self.repo.get_comparison(comparison_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate analysis not found.")
        return record


def execute_signature_comparison(comparison_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    repo = SignatureRepository(db)
    forensic_repo = AnalysisRepository(db)
    record = repo.get_comparison(comparison_id)
    if record is None:
        db.close()
        return
    try:
        forensic = forensic_repo.get(record.forensic_analysis_id) if record.forensic_analysis_id else None
        if forensic is None or not forensic.file_path:
            raise RuntimeError("missing_document")
        record.pipeline_stage = "preprocessing_document"
        repo.save_comparison(record)
        threading.Thread(target=execute_pipeline, args=(forensic.id,), daemon=True).start()
        preprocessing = process_document(
            forensic.file_path,
            analysis_id=record.id,
            file_type=forensic.file_type or "png",
            settings=settings,
        )
        page = cv2.imread(preprocessing.page_images[0].path, cv2.IMREAD_COLOR)
        if page is None:
            raise RuntimeError("page_read_failed")
        art = signature_dir(settings, record.id)
        write_png(art / "page-preview.png", page)
        record.page_preview_artifact = "page-preview"
        record.pipeline_stage = "visual_forensics"
        repo.save_comparison(record)
        forensic = _wait_forensic(forensic.id, record, repo)
        record.pipeline_stage = "detecting_signatures"
        repo.save_comparison(record)
        candidates = detect_signature_regions(page, page_number=1)
        record.candidates_json = json.dumps([item.model_dump() for item in candidates])
        selected, uncertain = _auto_select(candidates)
        if selected is not None:
            record.selected_region_json = selected.model_dump_json()
        repo.save_comparison(record)
        _persist_assessment(record, repo, settings, page, forensic, selected, uncertain)
    except Exception:
        logger.exception("certificate_analysis_failed id=%s", comparison_id)
        record.status = SignatureComparisonStatus.FAILED.value
        record.pipeline_stage = "failed"
        record.error_message = "Certificate analysis failed while processing the document."
        record.updated_at = utcnow()
        repo.save_comparison(record)
    finally:
        db.close()


def execute_signature_compare_only(comparison_id: str) -> None:
    settings = get_settings()
    db = SessionLocal()
    repo = SignatureRepository(db)
    forensic_repo = AnalysisRepository(db)
    record = repo.get_comparison(comparison_id)
    if record is None:
        db.close()
        return
    try:
        art = signature_dir(settings, record.id, create=False)
        page = cv2.imread(str(art / "page-preview.png"), cv2.IMREAD_COLOR)
        if page is None and record.file_path:
            preprocessing = process_document(
                record.file_path,
                analysis_id=record.id,
                file_type=record.file_type or "png",
                settings=settings,
            )
            page = cv2.imread(preprocessing.page_images[0].path, cv2.IMREAD_COLOR)
        if page is None:
            raise RuntimeError("page_read_failed")
        forensic = forensic_repo.get(record.forensic_analysis_id) if record.forensic_analysis_id else None
        region = SignatureRegion.model_validate_json(record.selected_region_json)
        _persist_assessment(record, repo, settings, page, forensic, region, uncertain=False)
    except Exception:
        logger.exception("certificate_signature_stage_failed id=%s", comparison_id)
        record.status = SignatureComparisonStatus.FAILED.value
        record.pipeline_stage = "failed"
        record.error_message = "Certificate analysis failed after signature region selection."
        record.updated_at = utcnow()
        repo.save_comparison(record)
    finally:
        db.close()


def _auto_select(candidates: list[SignatureRegion]) -> tuple[SignatureRegion | None, bool]:
    if not candidates:
        return None, False
    top = candidates[0]
    second = candidates[1] if len(candidates) > 1 else None
    if len(candidates) == 1 and (top.score or 0) >= 0.62:
        return top, False
    if (top.score or 0) >= 0.70 and (second is None or (top.score or 0) - (second.score or 0) >= 0.15):
        return top, False
    return None, True


def _persist_assessment(record, repo, settings, page, forensic, selected, uncertain: bool) -> None:
    fusion = public_fusion(forensic.fusion_result_json) if forensic else None
    intelligence = public_intelligence(forensic.document_intelligence_result_json) if forensic else None
    ela = public_ela(forensic.ela_result_json) if forensic else None
    copy_move = public_copy_move(forensic.copy_move_result_json) if forensic else None
    tamper = integrity_from_fusion(fusion, forensic.id if forensic else None)
    document = document_content_integrity(fusion, intelligence, ela, copy_move)
    candidates = [SignatureRegion.model_validate(item) for item in json.loads(record.candidates_json or "[]")]
    overlays = collect_overlays(copy_move=copy_move, ela=ela, intelligence=intelligence, signatures=candidates)
    fields = certificate_fields(intelligence)
    completed = ["upload_validation", "document_normalization", "visual_forensics", "ocr_layout", "evidence_fusion"]
    unavailable: list[str] = []
    if fusion is None:
        unavailable.append("full_document_fusion")
    if intelligence is None:
        unavailable.append("ocr_layout")
    extra_limitations: list[str] = []
    reference_fusion = None
    document_quality = None

    if uncertain:
        signature_stream = awaiting_selection(len(candidates))
        extra_limitations.append("Automatic signature detection was uncertain; the wrong crop was not scored.")
        record.pipeline_stage = "awaiting_region"
    elif selected is None:
        signature_stream = analyze_signature_integrity(page, None, None)
        extra_limitations.append("No signature region was confirmed.")
        record.pipeline_stage = "fusing_evidence"
    else:
        record.pipeline_stage = "analyzing_signature_integrity"
        repo.save_comparison(record)
        crop = crop_region(page, selected)
        _, doc_norm, document_quality = normalize_crop(crop)
        signature_stream = analyze_signature_integrity(page, selected, document_quality)
        art = signature_dir(settings, record.id)
        write_png(art / "document-signature.png", crop)
        write_png(art / "document-normalized.png", doc_norm)
        write_png(art / "document-contours.png", render_contours(doc_norm))
        highlight = page.copy()
        cv2.rectangle(highlight, (selected.x, selected.y), (selected.x + selected.width, selected.y + selected.height), (36, 92, 210), 2)
        write_png(art / "region-highlight.png", highlight)
        record.document_quality_json = document_quality.model_dump_json()
        completed.append("signature_integrity")
        if record.reference_id:
            record.pipeline_stage = "comparing_reference"
            repo.save_comparison(record)
            reference = repo.get_reference(record.reference_id)
            if reference is None:
                unavailable.append("reference_comparison")
            else:
                ref_bgr = load_bgr(reference.file_path)
                _, ref_norm, ref_quality = assess_and_normalize(ref_bgr)
                signals = compare_normalized(doc_norm, ref_norm, document_quality, ref_quality, selected.score)
                reference_fusion = fuse_comparison(signals)
                write_png(art / "reference-normalized.png", ref_norm)
                write_png(art / "overlay.png", render_overlay(doc_norm, ref_norm))
                record.comparison_json = signals.model_dump_json()
                record.fusion_json = reference_fusion.model_dump_json()
                completed.append("reference_comparison")
        else:
            unavailable.append("reference_comparison")
        record.pipeline_stage = "fusing_evidence"

    if uncertain:
        unavailable.extend(["signature_integrity", "reference_comparison"] if not record.reference_id else ["signature_integrity", "reference_comparison"])
        if "signature_integrity" not in unavailable:
            unavailable.append("signature_integrity")
        if record.reference_id:
            extra_limitations.append("Reference comparison is deferred until the signature region is confirmed.")
        elif "reference_comparison" not in unavailable:
            unavailable.append("reference_comparison")

    certificate = fuse_certificate(
        document=document,
        signature=signature_stream,
        reference=reference_fusion,
        fusion=fusion,
        completed=completed,
        unavailable=_unique(unavailable),
        extra_limitations=extra_limitations,
    )
    certificate.extracted_fields = fields
    certificate.overlay_regions = overlays
    record.tamper_json = tamper.model_dump_json() if tamper else None
    record.combined_json = certificate.model_dump_json()
    record.overall_status = certificate.overall_status
    if uncertain:
        record.status = SignatureComparisonStatus.NEEDS_REGION.value
    else:
        record.status = SignatureComparisonStatus.COMPLETE.value
        record.pipeline_stage = "complete"
    record.error_message = None
    record.updated_at = utcnow()
    repo.save_comparison(record)
    logger.info("certificate_analysis_saved id=%s status=%s", record.id, record.status)


def _wait_forensic(forensic_id: str, record, repo):
    db = SessionLocal()
    try:
        forensic_repo = AnalysisRepository(db)
        last = None
        for _ in range(120):
            last = forensic_repo.get(forensic_id)
            if last and last.pipeline_stage:
                mapped = FORENSIC_STAGE_MAP.get(last.pipeline_stage)
                if mapped and record.pipeline_stage != mapped and last.status == AnalysisStatus.PROCESSING:
                    record.pipeline_stage = mapped
                    repo.save_comparison(record)
            if last and last.status in {AnalysisStatus.COMPLETE, AnalysisStatus.FAILED, AnalysisStatus.PARTIAL_COMPLETE}:
                return last
            time.sleep(0.25)
        return last
    finally:
        db.close()


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out
