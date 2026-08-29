from __future__ import annotations

import time
from pathlib import Path

import cv2

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.intelligence import DocumentIntelligenceResult, LogicalCheck
from app.schemas.preprocessing import PreprocessingResultInternal
from app.services.forensics.artifacts import forensics_dir
from app.services.intelligence.barcode import extract_barcodes
from app.services.intelligence.classify import classify_document
from app.services.intelligence.consistency import run_logical_checks
from app.services.intelligence.extraction import extract_document_text
from app.services.intelligence.fields import extract_fields
from app.services.intelligence.scoring import score_intelligence

logger = get_logger(__name__)


def run_document_intelligence(
    *,
    analysis_id: str,
    file_path: str,
    document_type: str,
    preprocessing: PreprocessingResultInternal,
    settings: Settings,
) -> DocumentIntelligenceResult:
    started = time.perf_counter()
    try:
        extraction = extract_document_text(
            analysis_id=analysis_id,
            file_path=file_path,
            document_type=document_type,
            preprocessing=preprocessing,
            settings=settings,
        )
        fields = extract_fields(extraction)
        classification = classify_document(extraction, fields)
        barcodes = extract_barcodes(preprocessing)
        barcode_pairs = [(item.value, item.page_number) for item in barcodes]
        checks = run_logical_checks(extraction, fields, barcode_pairs)
        _attach_highlights(analysis_id, preprocessing, checks, settings)
        score, flagged, confidence = score_intelligence(extraction, checks)
        limitations = list(extraction.notes)
        if extraction.overall_quality in {"low", "failed"}:
            limitations.append("Logical checks may be limited because text extraction quality is reduced.")
        limitations.append("Document intelligence checks internal consistency only. It does not verify records in an external registry.")
        summary = _summarize(score, flagged, checks, extraction.overall_quality, classification.document_class)
        logger.info(
            "module=document_intelligence analysis_id=%s success duration_ms=%s score=%s quality=%s",
            analysis_id,
            int((time.perf_counter() - started) * 1000),
            score,
            extraction.overall_quality,
        )
        return DocumentIntelligenceResult(
            layer="document_intelligence",
            extraction=extraction,
            classification=classification,
            fields=fields,
            logical_checks=checks,
            barcodes=barcodes,
            suspicion_score=score,
            flagged=flagged,
            confidence=confidence,
            summary=summary,
            limitations=limitations,
        )
    except Exception:
        logger.exception("module=document_intelligence analysis_id=%s failure", analysis_id)
        from app.schemas.intelligence import DocumentClassification, ExtractionResult

        return DocumentIntelligenceResult(
            layer="document_intelligence",
            extraction=ExtractionResult(
                overall_quality="failed",
                overall_confidence=0.0,
                pages=[],
                tesseract_available=False,
                notes=["Document intelligence did not complete."],
            ),
            classification=DocumentClassification(
                document_class="generic_document",
                confidence=0.0,
                rationale="Extraction did not complete.",
            ),
            suspicion_score=0,
            flagged=False,
            confidence=0.0,
            summary="Document intelligence did not complete. This is not evidence of tampering.",
            limitations=["Module failure is not a tampering signal."],
            module_error="Document intelligence failed while processing this document.",
        )


def _attach_highlights(
    analysis_id: str,
    preprocessing: PreprocessingResultInternal,
    checks: list[LogicalCheck],
    settings: Settings,
) -> None:
    by_page = {item.page_number: item.path for item in preprocessing.page_images}
    directory = forensics_dir(settings, analysis_id)
    for index, check in enumerate(checks, start=1):
        if check.result not in {"fail", "warning"}:
            continue
        if check.evidence.bbox is None or check.evidence.page_number is None:
            continue
        source = by_page.get(check.evidence.page_number)
        if not source:
            continue
        image = cv2.imread(source, cv2.IMREAD_COLOR)
        if image is None:
            continue
        box = check.evidence.bbox
        overlay = image.copy()
        cv2.rectangle(overlay, (box.x, box.y), (box.x + box.width, box.y + box.height), (0, 180, 255), 2)
        artifact_id = f"p{check.evidence.page_number:03d}_di_{index:02d}"
        cv2.imwrite(str(directory / f"{artifact_id}.png"), overlay)
        check.artifact_id = artifact_id


def _summarize(score: int, flagged: bool, checks: list[LogicalCheck], quality: str, document_class: str) -> str:
    fails = [c for c in checks if c.result == "fail"]
    if quality == "failed" and not fails:
        return (
            "Text extraction did not yield usable content. No internal consistency contradiction was evaluated. "
            "This is not a tampering finding."
        )
    if fails:
        return (
            f"{len(fails)} internal consistency contradiction(s) were detected in this {document_class.replace('_', ' ')} "
            f"(suspicion {score}/100). These signals are not a final authenticity decision."
        )
    warnings = [c for c in checks if c.result == "warning"]
    if warnings:
        return (
            f"No confirmed contradiction; {len(warnings)} warning(s) were recorded (suspicion {score}/100). "
            "This is not a forgery verdict."
        )
    evaluated = [c for c in checks if c.result == "pass"]
    if evaluated:
        return (
            f"No internal inconsistency was detected among the checks that could be evaluated "
            f"({len(evaluated)} pass). Could-not-evaluate checks are listed separately and are not failures."
        )
    return "Could not evaluate internal consistency because required fields were not extracted."
