from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.services.forensics.ela_config import FLAG_THRESHOLD
from app.services.forensics.ela_forensics import analyze_ela
from tests.fixtures import png_bytes, smooth_jpeg_bytes, write_temp


def test_ela_is_deterministic(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "same.jpg", smooth_jpeg_bytes())
    settings = get_settings()
    first = analyze_ela(
        analysis_id="11111111-1111-4111-8111-111111111111",
        document_type="image",
        file_type="jpg",
        page_images=[(1, path)],
        settings=settings,
    )
    second = analyze_ela(
        analysis_id="11111111-1111-4111-8111-111111111111",
        document_type="image",
        file_type="jpg",
        page_images=[(1, path)],
        settings=settings,
    )
    assert first.suspicion_score == second.suspicion_score
    assert first.confidence == second.confidence
    assert first.pages[0].metrics == second.pages[0].metrics
    assert [s.model_dump() for s in first.pages[0].signals] == [s.model_dump() for s in second.pages[0].signals]


def test_clean_input_is_not_max_suspicion(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "clean.jpg", smooth_jpeg_bytes())
    result = analyze_ela(
        analysis_id="22222222-2222-4222-8222-222222222222",
        document_type="image",
        file_type="jpg",
        page_images=[(1, path)],
        settings=get_settings(),
    )
    assert result.suspicion_score < 90
    assert result.suspicion_score < FLAG_THRESHOLD + 20


def test_ela_writes_artifact(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "ela.jpg", smooth_jpeg_bytes())
    analysis_id = "33333333-3333-4333-8333-333333333333"
    result = analyze_ela(
        analysis_id=analysis_id,
        document_type="image",
        file_type="jpg",
        page_images=[(1, path)],
        settings=get_settings(),
    )
    assert result.pages[0].evidence
    artifact = result.pages[0].evidence[0].artifact_id
    stored = get_settings().processed_path / analysis_id / "forensics" / f"{artifact}.png"
    assert stored.is_file()
    assert stored.stat().st_size > 0


def test_corrupt_image_is_handled(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "bad.png", b"this-is-not-an-image")
    result = analyze_ela(
        analysis_id="44444444-4444-4444-8444-444444444444",
        document_type="image",
        file_type="png",
        page_images=[(1, path)],
        settings=get_settings(),
    )
    assert result.pages[0].suspicion_score == 0
    assert result.pages[0].flagged is False
    assert result.pages[0].limitations


def test_png_and_pdf_quality_are_limited(tmp_path: Path) -> None:
    png_path = write_temp(tmp_path / "page.png", png_bytes())
    png_result = analyze_ela(
        analysis_id="55555555-5555-4555-8555-555555555555",
        document_type="image",
        file_type="png",
        page_images=[(1, png_path)],
        settings=get_settings(),
    )
    assert png_result.analysis_quality == "limited"
    assert png_result.confidence < 0.5

    jpeg_path = write_temp(tmp_path / "photo.jpg", smooth_jpeg_bytes())
    jpeg_result = analyze_ela(
        analysis_id="66666666-6666-4666-8666-666666666666",
        document_type="image",
        file_type="jpg",
        page_images=[(1, jpeg_path)],
        settings=get_settings(),
    )
    pdf_result = analyze_ela(
        analysis_id="77777777-7777-4777-8777-777777777777",
        document_type="native_pdf",
        file_type="pdf",
        page_images=[(1, jpeg_path)],
        settings=get_settings(),
    )
    assert pdf_result.analysis_quality == "limited"
    assert jpeg_result.confidence >= png_result.confidence
    assert jpeg_result.confidence > pdf_result.confidence
