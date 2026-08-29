from __future__ import annotations

from pathlib import Path

from app.services.intelligence.classify import classify_document
from app.services.intelligence.extraction import extract_document_text
from app.services.intelligence.fields import extract_fields
from app.schemas.preprocessing import PageImageInternal, PreprocessingResultInternal
from app.core.config import get_settings
from tests.fixtures import certificate_pdf_bytes, invoice_pdf_bytes, native_pdf_bytes, write_temp


def _extract_pdf(tmp_path: Path, data: bytes, name: str = "doc.pdf"):
    path = write_temp(tmp_path / name, data)
    pre = PreprocessingResultInternal(
        document_type="native_pdf",
        page_count=1,
        page_images=[PageImageInternal(page_number=1, path=str(path), width=100, height=100)],
    )
    return extract_document_text(
        analysis_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        file_path=str(path),
        document_type="native_pdf",
        preprocessing=pre,
        settings=get_settings(),
    )


def test_invoice_fields_extracted(tmp_path: Path) -> None:
    extraction = _extract_pdf(tmp_path, invoice_pdf_bytes())
    fields = extract_fields(extraction)
    types = {f.field_type for f in fields}
    assert "invoice_number" in types
    assert "total" in types
    assert "subtotal" in types
    assert classify_document(extraction, fields).document_class == "invoice"


def test_dob_extracted_from_certificate(tmp_path: Path) -> None:
    extraction = _extract_pdf(tmp_path, certificate_pdf_bytes(), "cert.pdf")
    fields = extract_fields(extraction)
    dobs = [f for f in fields if f.field_type == "date_of_birth"]
    assert dobs
    assert "1990" in dobs[0].value
    assert classify_document(extraction, fields).document_class == "certificate"


def test_missing_fields_do_not_fail(tmp_path: Path) -> None:
    extraction = _extract_pdf(tmp_path, native_pdf_bytes(), "generic.pdf")
    fields = extract_fields(extraction)
    assert isinstance(fields, list)
    assert classify_document(extraction, fields).document_class == "generic_document"


def test_low_confidence_name_not_invented() -> None:
    from app.schemas.intelligence import ExtractedPage, ExtractionResult

    extraction = ExtractionResult(
        overall_quality="failed",
        overall_confidence=0.0,
        pages=[
            ExtractedPage(
                page_number=1,
                source="ocr",
                quality="failed",
                confidence=0.05,
                text="asdf qwer",
            )
        ],
    )
    assert extract_fields(extraction) == []
