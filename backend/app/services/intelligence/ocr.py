from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytesseract
from pytesseract import Output

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.intelligence import ExtractedPage, TextToken
from app.schemas.visual import BoundingBox
from app.services.intelligence.config import (
    LOW_TOKEN_CONFIDENCE,
    OCR_HIGH_MEAN,
    OCR_LOW_MEAN,
    OCR_MEDIUM_MEAN,
    OCR_MIN_TOKENS_HIGH,
)

logger = get_logger(__name__)


class TesseractUnavailable(RuntimeError):
    pass


def configure_tesseract(settings: Settings) -> None:
    cmd = getattr(settings, "tesseract_cmd", "") or ""
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd


def tesseract_available(settings: Settings) -> tuple[bool, str | None]:
    configure_tesseract(settings)
    try:
        version = str(pytesseract.get_tesseract_version())
        return True, version
    except Exception:
        return False, None


def ocr_page_image(image_path: Path, page_number: int, work_dir: Path) -> ExtractedPage:
    """OCR a copy of a processing image. The original file is not modified."""
    original = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if original is None:
        return ExtractedPage(
            page_number=page_number,
            source="ocr",
            quality="failed",
            confidence=0.0,
            text="",
            limitations=["The processing image could not be read for OCR."],
        )
    prepared = _preprocess_copy(original)
    work_dir.mkdir(parents=True, exist_ok=True)
    copy_path = work_dir / f"ocr_page_{page_number:03d}.png"
    cv2.imwrite(str(copy_path), prepared)
    try:
        data = pytesseract.image_to_data(prepared, output_type=Output.DICT)
    except pytesseract.TesseractNotFoundError as exc:
        raise TesseractUnavailable("Tesseract OCR is not installed or not on PATH.") from exc
    except Exception:
        logger.exception("ocr_failed page=%s", page_number)
        return ExtractedPage(
            page_number=page_number,
            source="ocr",
            quality="failed",
            confidence=0.0,
            text="",
            limitations=["OCR failed on this page. This is not evidence of tampering."],
        )
    tokens: list[TextToken] = []
    parts: list[str] = []
    confidences: list[float] = []
    n = len(data.get("text", []))
    for i in range(n):
        raw = (data["text"][i] or "").strip()
        if not raw:
            continue
        try:
            conf = float(data["conf"][i])
        except (TypeError, ValueError):
            conf = -1.0
        if conf < 0:
            continue
        tokens.append(
            TextToken(
                text=raw,
                bbox=BoundingBox(
                    x=int(data["left"][i]),
                    y=int(data["top"][i]),
                    width=int(data["width"][i]),
                    height=int(data["height"][i]),
                ),
                confidence=round(min(1.0, max(0.0, conf / 100.0)), 3),
            )
        )
        parts.append(raw)
        confidences.append(conf)
    text = " ".join(parts)
    quality, confidence, limitations = _ocr_quality(confidences, tokens)
    return ExtractedPage(
        page_number=page_number,
        source="ocr",
        quality=quality,
        confidence=confidence,
        text=text,
        tokens=tokens,
        limitations=limitations,
    )


def _preprocess_copy(bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    denoise = cv2.fastNlMeansDenoising(gray, None, 7, 7, 21)
    binary = cv2.adaptiveThreshold(
        denoise, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11
    )
    return binary


def _ocr_quality(confidences: list[float], tokens: list[TextToken]) -> tuple[str, float, list[str]]:
    if not tokens:
        return "failed", 0.0, ["No OCR tokens were produced. Logical checks cannot run on this page."]
    mean = float(np.mean(confidences))
    low_ratio = sum(1 for c in confidences if c < LOW_TOKEN_CONFIDENCE) / max(len(confidences), 1)
    mapped = round(min(1.0, max(0.0, mean / 100.0)), 3)
    notes: list[str] = []
    if low_ratio > 0.35:
        notes.append("A large share of OCR tokens have low confidence; field extraction may be incomplete.")
    if mean >= OCR_HIGH_MEAN and len(tokens) >= OCR_MIN_TOKENS_HIGH:
        return "high", max(mapped, 0.75), notes
    if mean >= OCR_MEDIUM_MEAN:
        notes.append("OCR quality is medium. Logical checks may be limited.")
        return "medium", mapped, notes
    if mean >= OCR_LOW_MEAN or tokens:
        notes.append("OCR quality is low. Logical checks may be limited and are not treated as tampering evidence.")
        return "low", mapped, notes
    return "failed", mapped, notes + ["OCR produced unusable text."]
