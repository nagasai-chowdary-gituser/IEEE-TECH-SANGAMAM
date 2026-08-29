from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.schemas.signature import ComparisonSignals, SignatureFusion
from app.services.signature.combined import combine
from app.services.signature.compare import compare_normalized
from app.services.signature.detect import detect_signature_regions
from app.services.signature.fusion import fuse_comparison
from app.services.signature.preprocess import assess_and_normalize, decode_image, normalize_crop
from tests.fixtures import (
    blank_png_bytes,
    certificate_with_signature_png_bytes,
    native_pdf_bytes,
    signature_stroke_png_bytes,
)
from tests.helpers import analyze_and_wait


def test_blank_reference_rejected(client: TestClient) -> None:
    response = client.post(
        "/api/v1/signatures/references",
        files={"file": ("blank.png", blank_png_bytes(), "image/png")},
        data={"label": "Principal"},
    )
    assert response.status_code == 400


def test_valid_reference_persists_and_can_be_replaced(client: TestClient) -> None:
    created = client.post(
        "/api/v1/signatures/references",
        files={"file": ("ref.png", signature_stroke_png_bytes(), "image/png")},
        data={"label": "Registrar"},
    )
    assert created.status_code == 200
    reference_id = created.json()["reference_id"]
    listing = client.get("/api/v1/signatures/references")
    assert any(item["reference_id"] == reference_id for item in listing.json()["items"])
    image = client.get(f"/api/v1/signatures/references/{reference_id}/image")
    assert image.status_code == 200
    deleted = client.delete(f"/api/v1/signatures/references/{reference_id}")
    assert deleted.status_code == 200
    listing2 = client.get("/api/v1/signatures/references")
    assert all(item["reference_id"] != reference_id for item in listing2.json()["items"])


def test_similar_and_different_signatures_are_deterministic() -> None:
    similar_a = decode_image(signature_stroke_png_bytes(seed=4))
    similar_b = decode_image(signature_stroke_png_bytes(seed=4, shift=1))
    different = decode_image(signature_stroke_png_bytes(seed=21, shift=12))
    _, a_norm, a_q = assess_and_normalize(similar_a)
    _, b_norm, b_q = normalize_crop(similar_b)
    _, d_norm, d_q = assess_and_normalize(different)
    close = fuse_comparison(compare_normalized(a_norm, b_norm, a_q, b_q, 0.8))
    far = fuse_comparison(compare_normalized(a_norm, d_norm, a_q, d_q, 0.8))
    again = fuse_comparison(compare_normalized(a_norm, b_norm, a_q, b_q, 0.8))
    assert close.model_dump() == again.model_dump()
    assert close.similarity_score >= far.similarity_score


def test_low_quality_is_inconclusive() -> None:
    signals = ComparisonSignals(
        structural_similarity=0.9,
        contour_similarity=0.9,
        geometry_similarity=0.9,
        histogram_similarity=0.9,
        image_quality_score=0.2,
        region_detection_confidence=0.8,
    )
    result = fuse_comparison(signals)
    assert result.overall_status == "INCONCLUSIVE"
    assert "GENUINE" not in result.assessment_summary
    assert "FORGED" not in result.assessment_summary


def test_combined_assessment_rules() -> None:
    high = SignatureFusion(
        overall_status="REFERENCE_MATCH_HIGH",
        similarity_score=84,
        assessment_confidence=0.8,
        assessment_summary="High similarity.",
        recommended_action="Review.",
        signals=ComparisonSignals(structural_similarity=0.9),
    )
    mismatch = high.model_copy(update={"overall_status": "POTENTIAL_MISMATCH"})
    inconclusive = high.model_copy(update={"overall_status": "INCONCLUSIVE"})
    assert combine(high, "LOW_MANIPULATION_RISK").overall_concern == "LOW_CONCERN"
    assert combine(high, "ELEVATED_MANIPULATION_RISK").overall_concern == "ELEVATED_CONCERN"
    assert combine(mismatch, "LOW_MANIPULATION_RISK").overall_concern == "REVIEW_REQUIRED"
    assert combine(inconclusive, "LOW_MANIPULATION_RISK").overall_concern == "INCONCLUSIVE"
    assert combine(inconclusive, "HIGH_MANIPULATION_RISK").overall_concern == "ELEVATED_CONCERN"
    scored = combine(high, "LOW_MANIPULATION_RISK", 20)
    assert scored.originality_score == 80
    assert scored.originality_verdict == "SAFE"
    assert scored.overall_verdict == "SAFE"
    assert scored.final_score is not None
    assert 0 <= scored.final_score <= 100
    unsafe = combine(high, "HIGH_MANIPULATION_RISK", 88)
    assert unsafe.originality_verdict == "NOT_SAFE"
    assert unsafe.overall_verdict == "NOT_SAFE"
    unavailable = combine(high, None)
    assert unavailable.originality_score is None
    assert unavailable.originality_verdict == "UNAVAILABLE"
    assert unavailable.final_score == high.similarity_score


def test_signature_api_and_forensics_still_work(client: TestClient) -> None:
    reference = client.post(
        "/api/v1/signatures/references",
        files={"file": ("ref.png", signature_stroke_png_bytes(seed=3), "image/png")},
        data={"label": "Authorized Signatory"},
    )
    assert reference.status_code == 200
    reference_id = reference.json()["reference_id"]
    created = client.post(
        "/api/v1/signatures/compare",
        files={"file": ("cert.png", certificate_with_signature_png_bytes(seed=3), "image/png")},
        data={"reference_id": reference_id},
    )
    assert created.status_code == 200
    comparison_id = created.json()["comparison_id"]
    body = created.json()
    for _ in range(160):
        body = client.get(f"/api/v1/signatures/comparisons/{comparison_id}").json()
        if body["status"] in {"COMPLETE", "FAILED", "NEEDS_REGION"}:
            break
        time.sleep(0.25)
    assert body["status"] in {"COMPLETE", "NEEDS_REGION"}, body.get("error_message")
    assert body.get("certificate") is not None
    assert body["certificate"]["document_content"]["status"]
    if body["status"] == "NEEDS_REGION":
        assert body["certificate"]["signature_integrity"]["status"] == "AWAITING_SELECTION"
        page = client.get(f"/api/v1/signatures/comparisons/{comparison_id}/artifacts/page-preview")
        assert page.status_code == 200
        region = client.post(
            f"/api/v1/signatures/comparisons/{comparison_id}/region",
            json={"page_number": 1, "x": 80, "y": 470, "width": 360, "height": 140},
        )
        assert region.status_code == 200
        for _ in range(120):
            body = client.get(f"/api/v1/signatures/comparisons/{comparison_id}").json()
            if body["status"] in {"COMPLETE", "FAILED"}:
                break
            time.sleep(0.25)
    assert body["status"] == "COMPLETE", body.get("error_message")
    assert body["fusion"]["overall_status"] in {
        "REFERENCE_MATCH_HIGH",
        "REFERENCE_MATCH_MODERATE",
        "POTENTIAL_MISMATCH",
        "INCONCLUSIVE",
    }
    assert "genuine" not in (body["fusion"]["assessment_summary"] or "").lower()
    assert body["certificate"]["overall_status"] in {
        "CERTIFICATE_CLEAR",
        "REVIEW_REQUIRED",
        "ELEVATED_CONCERN",
        "HIGH_MANIPULATION_CONCERN",
        "INCONCLUSIVE",
    }
    assert body["certificate"]["reference_comparison"]["status"] in {
        "HIGH_REFERENCE_MATCH",
        "MODERATE_REFERENCE_MATCH",
        "POTENTIAL_MISMATCH",
        "INCONCLUSIVE",
    }
    report = client.get(f"/api/v1/signatures/comparisons/{comparison_id}/report")
    assert report.status_code == 200
    assert report.content.startswith(b"%PDF")
    forensic = analyze_and_wait(client, "still-works.pdf", native_pdf_bytes(), "application/pdf")
    assert forensic["fusion"]["layer"] == "fusion"


def test_certificate_analysis_without_reference(client: TestClient) -> None:
    created = client.post(
        "/api/v1/signatures/compare",
        files={"file": ("cert.png", certificate_with_signature_png_bytes(seed=5), "image/png")},
    )
    assert created.status_code == 200
    comparison_id = created.json()["comparison_id"]
    body = created.json()
    for _ in range(160):
        body = client.get(f"/api/v1/signatures/comparisons/{comparison_id}").json()
        if body["status"] in {"COMPLETE", "FAILED", "NEEDS_REGION"}:
            break
        time.sleep(0.25)
    assert body["status"] in {"COMPLETE", "NEEDS_REGION"}, body.get("error_message")
    assert body["reference_id"] is None
    assert body["certificate"] is not None
    assert body["certificate"]["document_content"]["status"]
    if body["status"] == "NEEDS_REGION":
        assert body["certificate"]["reference_comparison"] is None
        region = client.post(
            f"/api/v1/signatures/comparisons/{comparison_id}/region",
            json={"page_number": 1, "x": 80, "y": 470, "width": 360, "height": 140},
        )
        assert region.status_code == 200
        for _ in range(120):
            body = client.get(f"/api/v1/signatures/comparisons/{comparison_id}").json()
            if body["status"] in {"COMPLETE", "FAILED"}:
                break
            time.sleep(0.25)
    assert body["status"] == "COMPLETE", body.get("error_message")
    assert body["fusion"] is None
    assert body["certificate"]["reference_comparison"] is None
    assert "AUTHENTIC" not in body["certificate"]["overall_status"]


def test_certificate_streams_stay_independent() -> None:
    from app.schemas.signature import StreamAssessment
    from app.services.signature.certificate_fusion import fuse_certificate

    document = StreamAssessment(status="NO_SIGNIFICANT_MANIPULATION_EVIDENCE", summary="clean document")
    signature = StreamAssessment(status="ELEVATED_MANIPULATION_RISK", summary="inserted signature evidence")
    high = SignatureFusion(
        overall_status="REFERENCE_MATCH_HIGH",
        similarity_score=84,
        assessment_confidence=0.8,
        assessment_summary="High similarity.",
        recommended_action="Review.",
        signals=ComparisonSignals(structural_similarity=0.9),
    )
    result = fuse_certificate(
        document=document,
        signature=signature,
        reference=high,
        fusion=None,
        completed=["visual_forensics"],
        unavailable=[],
        extra_limitations=[],
    )
    assert result.document_content.status == "NO_SIGNIFICANT_MANIPULATION_EVIDENCE"
    assert result.signature_integrity.status == "ELEVATED_MANIPULATION_RISK"
    assert result.reference_comparison is not None
    assert result.reference_comparison.status == "HIGH_REFERENCE_MATCH"
    assert result.overall_status == "ELEVATED_CONCERN"


def test_detect_finds_bottom_region() -> None:
    image = decode_image(certificate_with_signature_png_bytes())
    regions = detect_signature_regions(image)
    assert regions
    assert regions[0].y > 300
