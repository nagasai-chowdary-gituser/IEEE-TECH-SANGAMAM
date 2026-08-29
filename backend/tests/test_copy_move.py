from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings
from app.services.forensics.copy_move_config import FLAG_THRESHOLD
from app.services.forensics.copy_move_forensics import analyze_copy_move, _score
from tests.fixtures import cloned_region_png_bytes, png_bytes, repeated_icon_png_bytes, write_temp


def test_plain_image_does_not_automatically_flag(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "plain.png", png_bytes())
    result = analyze_copy_move(
        analysis_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        page_images=[(1, path)],
        settings=get_settings(),
    )
    assert result.flagged is False
    assert result.pages[0].regions == []
    assert result.suspicion_score < FLAG_THRESHOLD


def test_cloned_region_can_produce_evidence(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "cloned.png", cloned_region_png_bytes())
    analysis_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    result = analyze_copy_move(
        analysis_id=analysis_id,
        page_images=[(1, path)],
        settings=get_settings(),
    )
    page = result.pages[0]
    assert page.metrics.geometrically_verified_matches >= 8 or page.regions
    assert page.regions
    assert page.evidence
    artifact = get_settings().processed_path / analysis_id / "forensics" / f"{page.evidence[0].artifact_id}.png"
    assert artifact.is_file()
    region = page.regions[0]
    assert region.source_bbox.width > 0
    assert region.matched_bbox.width > 0
    source_cx = region.source_bbox.x + region.source_bbox.width / 2
    match_cx = region.matched_bbox.x + region.matched_bbox.width / 2
    assert abs(source_cx - match_cx) > 20


def test_single_match_is_not_strong_evidence() -> None:
    score, signals = _score(geo_count=1, filtered_count=1, clusters=[], repetition=False, pixel_count=100_000)
    assert score == 0
    assert signals == []


def test_repeated_template_is_not_high_confidence_tampering(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "grid.png", repeated_icon_png_bytes())
    result = analyze_copy_move(
        analysis_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        page_images=[(1, path)],
        settings=get_settings(),
    )
    assert result.confidence < 0.7
    if result.flagged:
        assert result.confidence <= 0.45


def test_copy_move_is_deterministic(tmp_path: Path) -> None:
    path = write_temp(tmp_path / "clone.png", cloned_region_png_bytes())
    kwargs = dict(
        analysis_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
        page_images=[(1, path)],
        settings=get_settings(),
    )
    first = analyze_copy_move(**kwargs)
    second = analyze_copy_move(**kwargs)
    assert first.suspicion_score == second.suspicion_score
    assert first.pages[0].metrics.model_dump() == second.pages[0].metrics.model_dump()
    assert [r.model_dump() for r in first.pages[0].regions] == [r.model_dump() for r in second.pages[0].regions]
