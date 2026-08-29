from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.schemas.preprocessing import PageImageInternal, PreprocessingResultInternal
from app.services.intelligence.extraction import extract_document_text
from app.services.intelligence.native_text import extract_native_pdf
from tests.fixtures import native_pdf_bytes, png_bytes, readable_ocr_png_bytes, write_temp


def _pre(path: Path, document_type: str = "image") -> PreprocessingResultInternal:
    return PreprocessingResultInternal(
        document_type=document_type,  # type: ignore[arg-type]
        page_count=1,
        page_images=[PageImageInternal(page_number=1, path=str(path), width=10, height=10)],
    )


def test_native_pdf_extracts_without_ocr(tmp_path: Path) -> None:
    pdf = write_temp(tmp_path / "native.pdf", native_pdf_bytes())
    pages = extract_native_pdf(pdf)
    assert pages[0].source == "native_pdf"
    assert "DocuVerify" in pages[0].text
    assert pages[0].tokens


def test_native_extraction_is_deterministic(tmp_path: Path) -> None:
    pdf = write_temp(tmp_path / "same.pdf", native_pdf_bytes())
    first = extract_native_pdf(pdf)
    second = extract_native_pdf(pdf)
    assert first[0].text == second[0].text
    assert first[0].quality == second[0].quality
    assert first[0].confidence == second[0].confidence


def test_image_uses_ocr_when_tesseract_available(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "ocr.png", readable_ocr_png_bytes())
    result = extract_document_text(
        analysis_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        file_path=str(path),
        document_type="image",
        preprocessing=_pre(path, "image"),
        settings=get_settings(),
    )
    assert result.pages[0].source == "ocr"
    if result.tesseract_available:
        assert "INV" in result.pages[0].text or result.pages[0].quality != "failed"
    else:
        assert result.pages[0].quality == "failed"
        assert result.pages[0].text == ""


def test_failed_ocr_does_not_fabricate_text(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "noise.png", png_bytes((12, 12, 12)))
    result = extract_document_text(
        analysis_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        file_path=str(path),
        document_type="image",
        preprocessing=_pre(path, "image"),
        settings=get_settings(),
    )
    if result.pages[0].quality == "failed":
        assert result.pages[0].text == ""
    assert "lorem ipsum" not in result.pages[0].text.lower()


def test_low_quality_is_marked_limited(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "tiny.png", png_bytes())
    result = extract_document_text(
        analysis_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        file_path=str(path),
        document_type="image",
        preprocessing=_pre(path, "image"),
        settings=get_settings(),
    )
    assert result.overall_quality in {"low", "failed", "medium"}
    if result.overall_quality in {"low", "failed"}:
        assert result.pages[0].limitations
