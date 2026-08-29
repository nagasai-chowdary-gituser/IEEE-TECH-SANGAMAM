from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.schemas.preprocessing import PageImageInternal, PreprocessingResultInternal
from app.services.intelligence.consistency import run_logical_checks
from app.services.intelligence.extraction import extract_document_text
from app.services.intelligence.fields import extract_fields
from app.services.intelligence.scoring import score_intelligence
from tests.fixtures import (
    certificate_pdf_bytes,
    conflicting_invoice_pdf_bytes,
    invoice_pdf_bytes,
    native_pdf_bytes,
    write_temp,
)


def _run(tmp_path: Path, data: bytes, name: str):
    path = write_temp(tmp_path / name, data)
    pre = PreprocessingResultInternal(
        document_type="native_pdf",
        page_count=1,
        page_images=[PageImageInternal(page_number=1, path=str(path), width=100, height=100)],
    )
    extraction = extract_document_text(
        analysis_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        file_path=str(path),
        document_type="native_pdf",
        preprocessing=pre,
        settings=get_settings(),
    )
    fields = extract_fields(extraction)
    checks = run_logical_checks(extraction, fields, [])
    return extraction, fields, checks


def _by_id(checks, check_id: str):
    return next(c for c in checks if c.check_id == check_id)


def test_matching_dob_age_passes(tmp_path: Path) -> None:
    _, _, checks = _run(tmp_path, certificate_pdf_bytes(age="34"), "ok.pdf")
    assert _by_id(checks, "dob_age_consistency").result == "pass"


def test_dob_age_mismatch_is_detected(tmp_path: Path) -> None:
    _, _, checks = _run(tmp_path, certificate_pdf_bytes(age="21"), "bad.pdf")
    assert _by_id(checks, "dob_age_consistency").result == "fail"


def test_birthday_boundary_does_not_false_fail(tmp_path: Path) -> None:
    # Issue date 2024-06-20, DOB 1990-06-15 => age 34, not 33.
    _, _, checks = _run(tmp_path, certificate_pdf_bytes(age="34"), "bday.pdf")
    assert _by_id(checks, "dob_age_consistency").result == "pass"


def test_correct_invoice_arithmetic_passes(tmp_path: Path) -> None:
    _, _, checks = _run(tmp_path, invoice_pdf_bytes(), "inv.pdf")
    assert _by_id(checks, "line_item_arithmetic").result == "pass"
    assert _by_id(checks, "invoice_total_consistency").result == "pass"


def test_incorrect_line_and_total_detected(tmp_path: Path) -> None:
    _, _, checks = _run(tmp_path, conflicting_invoice_pdf_bytes(), "badinv.pdf")
    assert _by_id(checks, "line_item_arithmetic").result == "fail"
    assert _by_id(checks, "invoice_total_consistency").result == "fail"
    assert _by_id(checks, "duplicate_field_consistency").result == "fail"


def test_insufficient_data_is_not_failure(tmp_path: Path) -> None:
    _, _, checks = _run(tmp_path, native_pdf_bytes(), "generic.pdf")
    dob = _by_id(checks, "dob_age_consistency")
    total = _by_id(checks, "invoice_total_consistency")
    assert dob.result == "insufficient_data"
    assert total.result == "insufficient_data"
    assert dob.score_impact == 0
    assert total.score_impact == 0


def test_scoring_is_deterministic(tmp_path: Path) -> None:
    extraction, _, checks = _run(tmp_path, conflicting_invoice_pdf_bytes(), "score.pdf")
    first = score_intelligence(extraction, checks)
    second = score_intelligence(extraction, checks)
    assert first == second
    assert first[0] > 0
