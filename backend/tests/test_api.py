from __future__ import annotations

from fastapi.testclient import TestClient

from tests.fixtures import jpeg_without_exif, native_pdf_bytes, png_bytes
from tests.helpers import analyze_and_wait, wait_for_complete
from app.utils.hashing import sha256_bytes


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "docuverify-api"
    assert body["status"] in {"ok", "degraded"}
    assert "database" in body


def test_invalid_file_rejection(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("notes.txt", b"this is not a document", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_content_mismatch_rejection(client: TestClient) -> None:
    response = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("spoof.pdf", b"not-a-pdf-file", "application/pdf")},
    )
    assert response.status_code == 400
    assert "does not match" in response.json()["detail"]


def test_valid_pdf_acceptance(client: TestClient) -> None:
    pdf = native_pdf_bytes()
    body = analyze_and_wait(client, "contract.pdf", pdf, "application/pdf")
    assert body["status"] == "COMPLETE"
    assert body["document"]["file_type"] == "pdf"
    assert body["document"]["document_type"] == "native_pdf"
    assert body["preprocessing"]["page_count"] >= 1
    assert "path" not in str(body["preprocessing"]["pages"])
    assert body["metadata_forensics"]["layer"] == "metadata"
    analysis_id = body["analysis_id"]

    fetched = client.get(f"/api/v1/documents/{analysis_id}")
    assert fetched.status_code == 200
    assert fetched.json()["analysis_id"] == analysis_id
    assert fetched.json()["status"] == "COMPLETE"
    assert fetched.json()["ela"]["layer"] == "ela"
    assert fetched.json()["copy_move"]["layer"] == "copy_move"
    assert "path" not in str(fetched.json()["ela"])
    assert fetched.json()["pipeline_message"]
    assert fetched.json()["document_intelligence"]["layer"] == "document_intelligence"
    assert fetched.json()["document_intelligence"]["extraction"]["pages"][0]["source"] == "native_pdf"
    assert fetched.json()["layers_completed"]
    fusion = fetched.json()["fusion"]
    assert fusion["layer"] == "fusion"
    assert fusion["risk_level"] in {"LOW", "MODERATE", "ELEVATED", "HIGH", "INCONCLUSIVE"}
    assert 0 <= fusion["overall_risk_score"] <= 100
    assert 0.0 <= fusion["assessment_confidence"] <= 1.0
    assert 0.0 <= fusion["analysis_coverage"] <= 1.0
    assert {row["layer"] for row in fusion["layer_contributions"]} == {
        "metadata",
        "ela",
        "copy_move",
        "document_intelligence",
    }
    assert fetched.json()["metadata_forensics"]["layer"] == "metadata"
    assert fetched.json()["explanation"] is not None
    assert fetched.json()["explanation"]["source"] in {"ai", "deterministic_fallback"}


def test_valid_image_acceptance(client: TestClient) -> None:
    png = png_bytes()
    body = analyze_and_wait(client, "scan.png", png, "image/png")
    assert body["status"] == "COMPLETE"
    assert body["document"]["file_type"] == "png"
    assert body["fusion"]["layer"] == "fusion"
    assert body["fusion"]["risk_level"] in {"LOW", "MODERATE", "ELEVATED", "HIGH", "INCONCLUSIVE"}
    assert body["document"]["document_type"] == "image"
    assert body["preprocessing"]["page_count"] == 1
    assert body["preprocessing"]["pages"][0]["width"] == 128
    assert body["preprocessing"]["pages"][0]["height"] == 96
    assert body["ela"]["analysis_quality"] == "limited"
    heatmap_id = body["ela"]["pages"][0]["evidence"][0]["artifact_id"]
    artifact = client.get(f"/api/v1/documents/{body['analysis_id']}/artifacts/{heatmap_id}")
    assert artifact.status_code == 200
    assert artifact.headers["content-type"].startswith("image/")
    assert len(artifact.content) > 32


def test_artifact_access_is_constrained(client: TestClient) -> None:
    png = png_bytes()
    created = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("scan.png", png, "image/png")},
    )
    analysis_id = created.json()["analysis_id"]
    wait_for_complete(client, analysis_id)
    traversal = client.get(f"/api/v1/documents/{analysis_id}/artifacts/../page_001")
    assert traversal.status_code in {400, 404, 422}
    missing = client.get(f"/api/v1/documents/{analysis_id}/artifacts/does_not_exist")
    assert missing.status_code == 404
    unknown = client.get("/api/v1/documents/00000000-0000-4000-8000-000000000000/artifacts/p001_ela")
    assert unknown.status_code == 404


def test_sha256_generation(client: TestClient) -> None:
    pdf = native_pdf_bytes()
    expected = sha256_bytes(pdf)
    body = analyze_and_wait(client, "hashme.pdf", pdf, "application/pdf")
    assert body["document"]["sha256"] == expected
    jpeg = jpeg_without_exif()
    expected_jpeg = sha256_bytes(jpeg)
    image_body = analyze_and_wait(client, "photo.jpg", jpeg, "image/jpeg")
    assert image_body["document"]["sha256"] == expected_jpeg
    assert image_body["document_intelligence"]["layer"] == "document_intelligence"
    assert image_body["ela"]["layer"] == "ela"
