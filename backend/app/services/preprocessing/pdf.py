from __future__ import annotations

import re
from pathlib import Path

import fitz

from app.schemas.preprocessing import PageImageInternal, PreprocessingResultInternal

PDF_DPI = 300
PDF_ZOOM = PDF_DPI / 72.0

# Classification uses extractable text volume, not the mere presence of a few characters.
MIN_WORDS_MEANINGFUL_PAGE = 20
MIN_ALNUM_MEANINGFUL_PAGE = 80
MIN_NATIVE_PAGE_RATIO = 0.35
MIN_NATIVE_TOTAL_WORDS = 60

WORD_RE = re.compile(r"[A-Za-z0-9]{2,}")
ALNUM_RE = re.compile(r"[A-Za-z0-9]")


def classify_pdf_text(page_texts: list[str]) -> tuple[str, list[str]]:
    notes: list[str] = []
    if not page_texts:
        return "scanned_pdf", ["PDF contains no pages."]

    meaningful_pages = 0
    total_words = 0
    for text in page_texts:
        words = WORD_RE.findall(text)
        alnum = len(ALNUM_RE.findall(text))
        total_words += len(words)
        if len(words) >= MIN_WORDS_MEANINGFUL_PAGE or alnum >= MIN_ALNUM_MEANINGFUL_PAGE:
            meaningful_pages += 1

    ratio = meaningful_pages / max(len(page_texts), 1)
    notes.append(
        f"Extracted {total_words} tokens across {len(page_texts)} page(s); "
        f"{meaningful_pages} page(s) had meaningful text."
    )
    if ratio >= MIN_NATIVE_PAGE_RATIO or total_words >= MIN_NATIVE_TOTAL_WORDS:
        return "native_pdf", notes
    notes.append(
        "Insufficient extractable text to treat this file as a native PDF; classified as scanned_pdf."
    )
    return "scanned_pdf", notes


def process_pdf(file_path: Path, output_dir: Path) -> PreprocessingResultInternal:
    output_dir.mkdir(parents=True, exist_ok=True)
    notes: list[str] = []
    page_images: list[PageImageInternal] = []
    page_texts: list[str] = []
    pdf_info: dict = {}

    with fitz.open(file_path) as doc:
        pdf_info = {
            "page_count": doc.page_count,
            "is_encrypted": bool(doc.is_encrypted),
            "metadata": {
                key: (doc.metadata or {}).get(key)
                for key in ("format", "title", "creator", "producer", "creationDate", "modDate")
            },
        }
        matrix = fitz.Matrix(PDF_ZOOM, PDF_ZOOM)
        for index, page in enumerate(doc):
            page_number = index + 1
            page_texts.append(page.get_text("text") or "")
            if page.rotation:
                notes.append(f"Page {page_number} reported rotation {page.rotation} degrees; render uses page rotation.")
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            destination = output_dir / f"page_{page_number:03d}.png"
            pixmap.save(str(destination))
            page_images.append(
                PageImageInternal(
                    page_number=page_number,
                    path=str(destination),
                    width=pixmap.width,
                    height=pixmap.height,
                )
            )

    document_type, class_notes = classify_pdf_text(page_texts)
    notes.extend(class_notes)
    notes.append(f"Rendered {len(page_images)} page image(s) at approximately {PDF_DPI} DPI.")
    return PreprocessingResultInternal(
        document_type=document_type,
        page_count=len(page_images),
        page_images=page_images,
        processing_notes=notes,
        pdf_info=pdf_info,
    )
