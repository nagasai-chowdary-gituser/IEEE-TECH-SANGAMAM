from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.schemas.compliance import IdentifierVerification, IntegrityAssessment
from app.schemas.intelligence import ExtractionResult, ExtractedPage
from app.services.compliance.aggregation import aggregate
from app.services.compliance.extraction import extract_udyam_fields, is_valid_gstin, is_valid_pan
from app.services.compliance.providers import verify_gstin, verify_pan
from tests.fixtures import native_pdf_bytes, udyam_certificate_pdf_bytes
from tests.helpers import analyze_and_wait


def _extraction(text: str, quality: str = "high", confidence: float = 0.92) -> ExtractionResult:
    return ExtractionResult(
        overall_quality=quality,  # type: ignore[arg-type]
        overall_confidence=confidence,
        pages=[
            ExtractedPage(
                page_number=1,
                source="native_pdf",
                quality=quality,  # type: ignore[arg-type]
                confidence=confidence,
                text=text,
            )
        ],
    )


def test_valid_pan_and_gstin_extraction() -> None:
    text = "UDYAM REGISTRATION\nPAN: AAPFU0939F\nGSTIN: 27AAPFU0939F1ZV\nName of Enterprise: Sample Precision Works"
    fields = extract_udyam_fields(_extraction(text))
    assert fields.pan.value == "AAPFU0939F"
    assert fields.pan.format_status == "valid"
    assert fields.gstin.value == "27AAPFU0939F1ZV"
    assert fields.gstin.format_status == "valid"
    assert fields.enterprise_name and "Sample" in fields.enterprise_name
    dated = extract_udyam_fields(_extraction("Date of Registration: 12/01/2022\nPAN: AAPFU0939F"))
    assert dated.registration_date == "12/01/2022"


def test_missing_and_invalid_identifiers() -> None:
    missing = extract_udyam_fields(_extraction("A generic letter with no tax identifiers."))
    assert missing.pan.format_status == "not_extracted"
    assert missing.gstin.format_status == "not_extracted"
    invalid = extract_udyam_fields(_extraction("PAN: ABCDEFGHIJ\nGSTIN: 00ABCDEFGHIJKLM"))
    assert invalid.pan.value == "ABCDEFGHIJ"
    assert invalid.pan.format_status == "invalid"
    assert invalid.gstin.value == "00ABCDEFGHIJKLM"
    assert invalid.gstin.format_status == "invalid"
    assert is_valid_pan("12345") is False
    assert is_valid_gstin("GST") is False
    assert is_valid_pan("AAPFU0939F") is True


def test_low_confidence_extraction_is_ignored() -> None:
    fields = extract_udyam_fields(_extraction("PAN: AAPFU0939F", quality="failed", confidence=0.1))
    assert fields.pan.format_status == "not_extracted"


def _settings(**kwargs) -> Settings:
    values = {
        "pan_api_key": "key_test_example",
        "pan_api_secret": "secret_test_example",
        "pan_sandbox_env": "test",
        "gst_in_check": "gstincheck-test-key",
    }
    values.update(kwargs)
    return Settings(**values)


def _mock_client(post_payloads: list[dict] | None = None, get_payload: dict | None = None, get_error=None):
    client = MagicMock()
    client.__enter__.return_value = client
    client.__exit__.return_value = False
    if post_payloads is not None:
        posts = []
        for payload in post_payloads:
            response = MagicMock()
            response.status_code = payload.get("status_code", 200)
            response.json.return_value = payload.get("json", {})
            posts.append(response)
        client.post.side_effect = posts
    if get_error is not None:
        client.get.side_effect = get_error
    elif get_payload is not None:
        response = MagicMock()
        response.status_code = get_payload.get("status_code", 200)
        response.json.return_value = get_payload.get("json", {})
        client.get.return_value = response
    return client


def test_pan_success_failure_unavailable_and_no_secret_leak() -> None:
    settings = _settings()
    with patch("app.services.compliance.providers.httpx.Client") as client_cls:
        client_cls.return_value = _mock_client(
            [
                {"json": {"code": 200, "data": {"access_token": "jwt-should-not-leak"}}},
                {
                    "json": {
                        "code": 200,
                        "data": {
                            "pan": "AAPFU0939F",
                            "status": "valid",
                            "category": "firm",
                            "aadhaar_seeding_status": "na",
                            "access_token": "drop-me",
                        },
                    }
                },
            ]
        )
        result = verify_pan("AAPFU0939F", "valid", settings, "Sample Precision Works", "12/01/2022")
    assert result.outcome == "passed"
    assert "jwt-should-not-leak" not in str(result.model_dump())
    assert "access_token" not in result.details

    with patch("app.services.compliance.providers.httpx.Client") as client_cls:
        client_cls.return_value = _mock_client(
            [
                {"json": {"code": 200, "data": {"access_token": "jwt"}}},
                {"json": {"code": 200, "data": {"pan": "AAPFU0939F", "status": "invalid"}}},
            ]
        )
        failed = verify_pan("AAPFU0939F", "valid", settings, "Sample Precision Works", "12/01/2022")
    assert failed.outcome == "failed"

    unavailable = verify_pan("AAPFU0939F", "valid", _settings(pan_api_key="", pan_api_secret=""))
    assert unavailable.outcome == "unavailable"
    assert "invalid" not in (unavailable.limitation or "").lower() or "not set" in (unavailable.limitation or "").lower()


def test_gst_success_and_unavailable() -> None:
    settings = _settings()
    with patch("app.services.compliance.providers.httpx.Client") as client_cls:
        client_cls.return_value = _mock_client(
            get_payload={
                "json": {
                    "flag": True,
                    "message": "GSTIN found",
                    "data": {"lgnm": "SAMPLE", "tradeNam": "SAMPLE", "sts": "Active", "token": "drop-me"},
                }
            }
        )
        result = verify_gstin("27AAPFU0939F1ZV", "valid", settings)
    request = client_cls.return_value.get.call_args
    assert request is not None
    requested_url = request.args[0] if request.args else request.kwargs.get("url", "")
    assert "gstincheck-test-key" not in requested_url
    assert requested_url.endswith("/27AAPFU0939F1ZV")
    assert request.kwargs["headers"]["x-api-key"] == "gstincheck-test-key"
    assert result.outcome == "passed"
    assert result.details.get("legal_name") == "SAMPLE"
    assert "token" not in result.details
    missing = verify_gstin("27AAPFU0939F1ZV", "valid", _settings(gst_in_check=""))
    assert missing.outcome == "unavailable"


def test_invalid_format_does_not_call_api() -> None:
    with patch("app.services.compliance.providers.httpx.Client") as client_cls:
        result = verify_gstin("NOT-A-GSTIN", "invalid", _settings())
        client_cls.assert_not_called()
    assert result.outcome == "format_invalid"


def test_network_failure_is_unavailable_not_invalid() -> None:
    import httpx

    with patch("app.services.compliance.providers.httpx.Client") as client_cls:
        client_cls.return_value = _mock_client(get_error=httpx.ConnectError("down"))
        result = verify_gstin("27AAPFU0939F1ZV", "valid", _settings())
    assert result.outcome == "unavailable"
    assert "invalid" not in result.outcome


def _ident(kind: str, outcome: str, fmt: str = "valid") -> IdentifierVerification:
    return IdentifierVerification(
        kind=kind,  # type: ignore[arg-type]
        extracted_value="AAPFU0939F" if kind == "pan" else "27AAPFU0939F1ZV",
        format_status=fmt,  # type: ignore[arg-type]
        outcome=outcome,  # type: ignore[arg-type]
    )


def _integrity(level: str, coverage: float = 0.9) -> IntegrityAssessment:
    return IntegrityAssessment(level=level, analysis_coverage=coverage, summary="Integrity summary.")  # type: ignore[arg-type]


def test_aggregation_rules_are_deterministic() -> None:
    clean = aggregate(_ident("pan", "passed"), _ident("gstin", "passed"), _integrity("NO_MEANINGFUL_TAMPER_EVIDENCE"))
    assert clean.overall_status == "COMPLIANT"
    pan_fail = aggregate(_ident("pan", "failed"), _ident("gstin", "passed"), _integrity("NO_MEANINGFUL_TAMPER_EVIDENCE"))
    assert pan_fail.overall_status == "REVIEW_REQUIRED"
    elevated = aggregate(_ident("pan", "passed"), _ident("gstin", "passed"), _integrity("ELEVATED_MANIPULATION_RISK"))
    assert elevated.overall_status == "REVIEW_REQUIRED"
    high = aggregate(_ident("pan", "passed"), _ident("gstin", "passed"), _integrity("HIGH_MANIPULATION_RISK"))
    assert high.overall_status == "HIGH_RISK"
    unavailable = aggregate(_ident("pan", "unavailable"), _ident("gstin", "unavailable"), _integrity("NO_MEANINGFUL_TAMPER_EVIDENCE"))
    assert unavailable.overall_status == "INCONCLUSIVE"
    missing = aggregate(
        IdentifierVerification(kind="pan", format_status="not_extracted", outcome="not_extracted"),
        _ident("gstin", "passed"),
        _integrity("NO_MEANINGFUL_TAMPER_EVIDENCE"),
    )
    assert missing.overall_status == "INCONCLUSIVE"
    coverage = aggregate(_ident("pan", "passed"), _ident("gstin", "passed"), _integrity("LOW_MANIPULATION_RISK", 0.2))
    assert coverage.overall_status == "INCONCLUSIVE"
    both_fail = aggregate(_ident("pan", "failed"), _ident("gstin", "failed"), _integrity("LOW_MANIPULATION_RISK"))
    assert both_fail.overall_status == "HIGH_RISK"
    first = aggregate(_ident("pan", "passed"), _ident("gstin", "passed"), _integrity("NO_MEANINGFUL_TAMPER_EVIDENCE"))
    second = aggregate(_ident("pan", "passed"), _ident("gstin", "passed"), _integrity("NO_MEANINGFUL_TAMPER_EVIDENCE"))
    assert first.model_dump() == second.model_dump()
    assert 0 <= clean.compliance_risk_score <= 100


def test_compliance_api_extracts_and_does_not_leak_secrets(client: TestClient) -> None:
    pdf = udyam_certificate_pdf_bytes()
    created = client.post("/api/v1/compliance/analyze", files={"file": ("udyam.pdf", pdf, "application/pdf")})
    assert created.status_code == 200
    compliance_id = created.json()["compliance_id"]
    body = created.json()
    assert body["status"] in {"PROCESSING", "COMPLETE"}
    deadline_body = body
    import time

    for _ in range(80):
        fetched = client.get(f"/api/v1/compliance/{compliance_id}")
        deadline_body = fetched.json()
        if deadline_body["status"] in {"COMPLETE", "FAILED"}:
            break
        time.sleep(0.25)
    assert deadline_body["status"] == "COMPLETE", deadline_body.get("error_message")
    assert deadline_body["certificate_fields"]["pan"]["value"] == "AAPFU0939F"
    assert deadline_body["certificate_fields"]["gstin"]["value"] == "27AAPFU0939F1ZV"
    assert deadline_body["pan"]["outcome"] in {"passed", "failed", "unavailable", "error"}
    assert "sk-" not in str(deadline_body).lower()
    assert "api_key" not in str(deadline_body).lower() or deadline_body["pan"]["details"] == {}
    listing = client.get("/api/v1/compliance")
    assert listing.status_code == 200
    assert any(item["compliance_id"] == compliance_id for item in listing.json()["items"])
    report = client.get(f"/api/v1/compliance/{compliance_id}/report")
    assert report.status_code == 200
    assert report.content.startswith(b"%PDF")
    forensic = analyze_and_wait(client, "still-works.pdf", native_pdf_bytes(), "application/pdf")
    assert forensic["fusion"]["layer"] == "fusion"


def test_parallel_jobs_include_pan_gst_and_forensics(client: TestClient) -> None:
    from concurrent.futures import ThreadPoolExecutor as RealExecutor

    submitted: list[str] = []

    class TrackingExecutor(RealExecutor):
        def submit(self, fn, *args, **kwargs):  # type: ignore[no-untyped-def]
            submitted.append(getattr(fn, "__name__", str(fn)))
            return super().submit(fn, *args, **kwargs)

    pdf = udyam_certificate_pdf_bytes()
    with patch("app.services.compliance.orchestrator.ThreadPoolExecutor", TrackingExecutor):
        created = client.post("/api/v1/compliance/analyze", files={"file": ("udyam.pdf", pdf, "application/pdf")})
        assert created.status_code == 200
        compliance_id = created.json()["compliance_id"]
        import time

        for _ in range(80):
            fetched = client.get(f"/api/v1/compliance/{compliance_id}")
            if fetched.json()["status"] in {"COMPLETE", "FAILED"}:
                break
            time.sleep(0.25)
    assert {"verify_pan", "verify_gstin", "execute_pipeline"} <= set(submitted)


def test_pan_internal_error_does_not_cancel_gst_or_forensics(client: TestClient) -> None:
    def boom(*_args, **_kwargs):
        raise RuntimeError("pan adapter exploded")

    pdf = udyam_certificate_pdf_bytes()
    with patch("app.services.compliance.orchestrator.verify_pan", boom):
        created = client.post("/api/v1/compliance/analyze", files={"file": ("udyam.pdf", pdf, "application/pdf")})
        compliance_id = created.json()["compliance_id"]
        import time

        body = created.json()
        for _ in range(80):
            body = client.get(f"/api/v1/compliance/{compliance_id}").json()
            if body["status"] in {"COMPLETE", "FAILED"}:
                break
            time.sleep(0.25)
    assert body["status"] == "COMPLETE", body.get("error_message")
    assert body["pan"]["outcome"] == "error"
    assert body["gstin"]["outcome"] in {"passed", "failed", "unavailable", "error"}
    assert body["integrity"] is not None
    assert body["overall_status"] != "COMPLIANT"
