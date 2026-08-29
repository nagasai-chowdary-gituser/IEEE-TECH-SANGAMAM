from __future__ import annotations

from pathlib import Path

from app.services.forensics.metadata import analyze_metadata
from app.services.forensics.scoring import FLAG_THRESHOLD, SCORE_HIGH_RISK_EDITOR
from tests.fixtures import (
    empty_metadata_pdf_bytes,
    jpeg_with_software,
    jpeg_without_exif,
    photoshop_pdf_bytes,
    write_temp,
)


def test_metadata_scoring_is_deterministic(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "same.pdf", photoshop_pdf_bytes())
    first = analyze_metadata(str(path), "native_pdf")
    second = analyze_metadata(str(path), "native_pdf")
    assert first.model_dump() == second.model_dump()


def test_missing_metadata_is_not_high_suspicion(tmp_path: Path) -> None:
    pdf_path = write_temp(tmp_path / "empty-meta.pdf", empty_metadata_pdf_bytes())
    pdf_result = analyze_metadata(str(pdf_path), "native_pdf")
    assert pdf_result.suspicion_score < FLAG_THRESHOLD
    assert pdf_result.flagged is False
    assert all(signal.severity == "low" for signal in pdf_result.signals)

    jpeg_path = write_temp(tmp_path / "no-exif.jpg", jpeg_without_exif())
    image_result = analyze_metadata(str(jpeg_path), "image")
    assert image_result.suspicion_score < 20
    assert image_result.flagged is False
    assert any(signal.id == "image_missing_exif" for signal in image_result.signals)


def test_editing_software_creates_forensic_signal(tmp_path: Path) -> None:
    pdf_path = write_temp(tmp_path / "edited.pdf", photoshop_pdf_bytes())
    pdf_result = analyze_metadata(str(pdf_path), "native_pdf")
    assert any(signal.id == "pdf_known_editing_software" for signal in pdf_result.signals)
    assert pdf_result.suspicion_score >= SCORE_HIGH_RISK_EDITOR

    jpeg_path = write_temp(tmp_path / "edited.jpg", jpeg_with_software("Adobe Photoshop 24.7 (Windows)"))
    image_result = analyze_metadata(str(jpeg_path), "image")
    assert any(signal.id == "image_known_editing_software" for signal in image_result.signals)
    assert image_result.suspicion_score >= SCORE_HIGH_RISK_EDITOR
