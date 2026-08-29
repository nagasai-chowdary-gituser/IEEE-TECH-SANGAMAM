from __future__ import annotations

from pathlib import Path

import fitz

from app.schemas.intelligence import ExtractedPage, TextToken
from app.schemas.visual import BoundingBox
from app.services.intelligence.config import NATIVE_HIGH_WORDS, NATIVE_MEDIUM_WORDS
from app.services.preprocessing.pdf import PDF_ZOOM, classify_pdf_text


def extract_native_pdf(file_path: str | Path) -> list[ExtractedPage]:
    pages: list[ExtractedPage] = []
    with fitz.open(file_path) as doc:
        for index, page in enumerate(doc):
            page_number = index + 1
            raw = page.get_text("text") or ""
            tokens = _tokens_from_dict(page.get_text("dict") or {}, PDF_ZOOM)
            words = [t.text for t in tokens if t.text.strip()]
            word_count = len(words)
            quality, confidence = _native_quality(word_count, raw)
            pages.append(
                ExtractedPage(
                    page_number=page_number,
                    source="native_pdf",
                    quality=quality,
                    confidence=confidence,
                    text=raw.strip(),
                    tokens=tokens,
                    limitations=[]
                    if quality == "high"
                    else ["Native PDF text on this page is sparse; logical checks may be limited."],
                )
            )
    return pages


def pdf_has_meaningful_native_text(file_path: str | Path) -> bool:
    with fitz.open(file_path) as doc:
        texts = [(page.get_text("text") or "") for page in doc]
    kind, _ = classify_pdf_text(texts)
    return kind == "native_pdf"


def _native_quality(word_count: int, text: str) -> tuple[str, float]:
    if word_count >= NATIVE_HIGH_WORDS or len(text) >= 200:
        return "high", 0.9
    if word_count >= NATIVE_MEDIUM_WORDS or len(text.strip()) >= 40:
        return "medium", 0.62
    if word_count > 0:
        return "low", 0.34
    return "failed", 0.12


def _tokens_from_dict(payload: dict, zoom: float) -> list[TextToken]:
    tokens: list[TextToken] = []
    for block in payload.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = (span.get("text") or "").strip()
                if not text:
                    continue
                bbox = span.get("bbox") or [0, 0, 0, 0]
                x0, y0, x1, y1 = (float(v) * zoom for v in bbox)
                tokens.append(
                    TextToken(
                        text=text,
                        bbox=BoundingBox(
                            x=int(round(x0)),
                            y=int(round(y0)),
                            width=max(1, int(round(x1 - x0))),
                            height=max(1, int(round(y1 - y0))),
                        ),
                        confidence=1.0,
                        font_size=float(span.get("size") or 0) or None,
                    )
                )
    return tokens
