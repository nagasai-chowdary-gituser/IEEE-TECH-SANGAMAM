from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.intelligence import ExtractedPage, ExtractionResult
from app.schemas.preprocessing import PreprocessingResultInternal
from app.services.intelligence.native_text import extract_native_pdf, pdf_has_meaningful_native_text
from app.services.intelligence.ocr import TesseractUnavailable, ocr_page_image, tesseract_available

logger = get_logger(__name__)

QUALITY_RANK = {"failed": 0, "low": 1, "medium": 2, "high": 3}


def extract_document_text(
    *,
    analysis_id: str,
    file_path: str,
    document_type: str,
    preprocessing: PreprocessingResultInternal,
    settings: Settings,
) -> ExtractionResult:
    notes: list[str] = []
    available, version = tesseract_available(settings)
    if version:
        notes.append(f"Tesseract detected ({version}).")
    pages: list[ExtractedPage] = []

    use_native = document_type == "native_pdf" or (
        document_type != "image" and pdf_has_meaningful_native_text(file_path)
    )
    if document_type == "native_pdf" or use_native:
        logger.info("module=text_extract analysis_id=%s path=native_pdf", analysis_id)
        pages = extract_native_pdf(file_path)
        notes.append("Native PDF text was used as the primary source; OCR was not applied to these pages.")
    else:
        if not available:
            notes.append(
                "Tesseract OCR is not installed or not on PATH. Scanned/image text could not be extracted."
            )
            logger.info("module=text_extract analysis_id=%s path=ocr unavailable", analysis_id)
            for item in preprocessing.page_images:
                pages.append(
                    ExtractedPage(
                        page_number=item.page_number,
                        source="ocr",
                        quality="failed",
                        confidence=0.0,
                        text="",
                        limitations=["Tesseract OCR is unavailable. This is not evidence of tampering."],
                    )
                )
        else:
            work_dir = settings.processed_path / analysis_id / "ocr"
            logger.info("module=text_extract analysis_id=%s path=ocr", analysis_id)
            try:
                for item in preprocessing.page_images:
                    pages.append(ocr_page_image(Path(item.path), item.page_number, work_dir))
            except TesseractUnavailable:
                notes.append("Tesseract OCR became unavailable during extraction.")
                pages = [
                    ExtractedPage(
                        page_number=item.page_number,
                        source="ocr",
                        quality="failed",
                        confidence=0.0,
                        text="",
                        limitations=["Tesseract OCR is unavailable. This is not evidence of tampering."],
                    )
                    for item in preprocessing.page_images
                ]

    overall_quality, overall_conf = _overall(pages)
    return ExtractionResult(
        overall_quality=overall_quality,
        overall_confidence=overall_conf,
        pages=pages,
        tesseract_available=available,
        notes=notes,
    )


def _overall(pages: list[ExtractedPage]) -> tuple[str, float]:
    if not pages:
        return "failed", 0.0
    worst = min(pages, key=lambda p: QUALITY_RANK[p.quality])
    # Document quality follows the weakest extracted page, but confidence
    # is weighted toward pages that actually contain text.
    confidences = [p.confidence for p in pages]
    mean_conf = sum(confidences) / len(confidences)
    if any(p.quality == "failed" for p in pages) and all(not p.text.strip() for p in pages):
        return "failed", round(mean_conf, 3)
    if any(p.quality in {"high", "medium"} for p in pages) and worst.quality == "failed":
        return "medium", round(mean_conf, 3)
    return worst.quality, round(mean_conf, 3)
