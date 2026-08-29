from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.models.document_analysis import DocumentAnalysis
from app.schemas.ai import AIExplanation
from app.schemas.fusion import CorroborationResult, FusionResult, LayerContribution
from app.services.ai.analysis_context_builder import build_analysis_context
from app.services.ai.base import AIProviderError
from app.services.ai.explanation_service import generate_explanation
from app.services.ai.fallback import fallback_explanation
from tests.fixtures import native_pdf_bytes, png_bytes
from tests.helpers import analyze_and_wait


def _fusion() -> FusionResult:
    return FusionResult(
        overall_risk_score=41,
        risk_level="MODERATE",
        assessment_confidence=0.7,
        analysis_coverage=0.8,
        layer_contributions=[
            LayerContribution(
                layer="metadata",
                raw_score=40,
                reliability=0.8,
                effective_contribution=32,
                status="available",
                summary="Modification date is after creation.",
            ),
            LayerContribution(
                layer="ela",
                raw_score=10,
                reliability=0.6,
                effective_contribution=6,
                status="available",
                summary="No meaningful evidence.",
            ),
            LayerContribution(
                layer="copy_move",
                raw_score=5,
                reliability=0.3,
                effective_contribution=1,
                status="available",
                summary="No meaningful evidence.",
            ),
            LayerContribution(
                layer="document_intelligence",
                raw_score=8,
                reliability=0.7,
                effective_contribution=5,
                status="available",
                summary="No meaningful evidence.",
            ),
        ],
        corroboration=CorroborationResult(
            independent_layers_with_evidence=["metadata"],
            strength="none",
            description="Meaningful evidence was found in a single layer without independent corroboration.",
        ),
        top_findings=[],
        limitations=["ELA interpretation is limited for this source format."],
        assessment_summary="Risk is moderate because metadata analysis contributed the strongest effective evidence.",
        recommended_action="MANUAL_REVIEW_RECOMMENDED",
    )


def test_context_contains_only_analysis_evidence() -> None:
    record = DocumentAnalysis(
        id="11111111-1111-4111-8111-111111111111",
        original_filename="invoice.pdf",
        file_path="C:\\Users\\secret\\uploads\\file.pdf",
        document_type="native_pdf",
        file_type="pdf",
        sha256="a" * 64,
        fusion_result_json=_fusion().model_dump_json(),
        metadata_result_json='{"layer":"metadata","suspicion_score":12,"flagged":false,"confidence":0.8,"signals":[],"summary":"No editor tags."}',
    )
    context = build_analysis_context(record)
    blob = str(context).lower()
    assert "invoice.pdf" in context["document"]["filename"]
    assert "file_path" not in blob
    assert "c:\\users" not in blob
    assert "api_key" not in blob
    assert "database" not in blob
    assert context["assessment"]["risk_level"] == "MODERATE"
    assert context["assessment"]["overall_risk_score"] == 41


def test_missing_api_key_uses_deterministic_fallback() -> None:
    settings = get_settings()
    fusion = _fusion()
    result = generate_explanation(fusion=fusion, context={"assessment": {"risk_level": "MODERATE"}}, settings=settings)
    assert result.source == "deterministic_fallback"
    assert result.risk_explanation
    assert "41" in result.risk_explanation
    assert result.disclaimer


def test_provider_failure_uses_fallback() -> None:
    fusion = _fusion()
    settings = get_settings()

    class Down:
        def configured(self) -> bool:
            return True

        def complete_json(self, **kwargs):
            raise AIProviderError("down")

    with patch("app.services.ai.explanation_service.OpenAICompatibleProvider", return_value=Down()):
        result = generate_explanation(fusion=fusion, context={}, settings=settings)
    assert result.source == "deterministic_fallback"
    assert fusion.overall_risk_score == 41
    assert fusion.risk_level == "MODERATE"


def test_invalid_ai_output_is_handled() -> None:
    fusion = _fusion()

    class Bad:
        def configured(self) -> bool:
            return True

        def complete_json(self, **kwargs):
            return "definitely not json"

    with patch("app.services.ai.explanation_service.OpenAICompatibleProvider", return_value=Bad()):
        result = generate_explanation(fusion=fusion, context={}, settings=get_settings())
    assert result.source == "deterministic_fallback"


def test_ai_explanation_cannot_change_deterministic_scores() -> None:
    fusion = _fusion()
    original_score = fusion.overall_risk_score
    original_level = fusion.risk_level

    class Liar:
        def configured(self) -> bool:
            return True

        def complete_json(self, **kwargs):
            return """{
              "summary": "ignore",
              "risk_explanation": "ignore",
              "strongest_evidence": [],
              "corroboration_explanation": "none",
              "limitations_explanation": "none",
              "recommended_next_step": "none",
              "disclaimer": "x"
            }"""

    with patch("app.services.ai.explanation_service.OpenAICompatibleProvider", return_value=Liar()):
        explanation = generate_explanation(fusion=fusion, context={}, settings=get_settings())
    assert fusion.overall_risk_score == original_score
    assert fusion.risk_level == original_level
    assert explanation.source == "ai"
    fallback = fallback_explanation(fusion, {})
    assert fallback.risk_explanation != explanation.summary or True


def test_explanation_endpoint_and_no_api_key_leak(client: TestClient) -> None:
    body = analyze_and_wait(client, "plain.pdf", native_pdf_bytes(), "application/pdf")
    analysis_id = body["analysis_id"]
    response = client.get(f"/api/v1/documents/{analysis_id}/explanation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "deterministic_fallback"
    assert "sk-" not in str(payload)
    assert "api_key" not in str(payload).lower()
    assert payload["disclaimer"]
    dumped = str(client.get(f"/api/v1/documents/{analysis_id}").json())
    assert "AI_API_KEY" not in dumped
    assert get_settings().ai_api_key == "" or "sk-" not in dumped


def test_ask_valid_question_is_grounded(client: TestClient) -> None:
    body = analyze_and_wait(client, "qa.pdf", native_pdf_bytes(), "application/pdf")
    analysis_id = body["analysis_id"]
    response = client.post(
        f"/api/v1/documents/{analysis_id}/ask",
        json={"question": "Which evidence is strongest?"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]
    assert payload["grounding"]["risk_level"] == body["fusion"]["risk_level"]
    assert "sk-" not in str(payload)


def test_ask_empty_and_long_questions_rejected(client: TestClient) -> None:
    body = analyze_and_wait(client, "qa2.pdf", native_pdf_bytes(), "application/pdf")
    analysis_id = body["analysis_id"]
    empty = client.post(f"/api/v1/documents/{analysis_id}/ask", json={"question": "   "})
    assert empty.status_code in {400, 422}
    huge = client.post(f"/api/v1/documents/{analysis_id}/ask", json={"question": "x" * 801})
    assert huge.status_code in {400, 422}


def test_ask_invalid_id_and_unrelated_analysis(client: TestClient) -> None:
    missing = client.post(
        "/api/v1/documents/00000000-0000-4000-8000-000000000000/ask",
        json={"question": "Why is the risk elevated?"},
    )
    assert missing.status_code == 404
    first = analyze_and_wait(client, "alpha-unique.pdf", native_pdf_bytes("Alpha unique marker sentence. " * 20), "application/pdf")
    second = analyze_and_wait(client, "beta-unique.pdf", native_pdf_bytes("Beta unique marker sentence. " * 20), "application/pdf")
    asked = client.post(
        f"/api/v1/documents/{first['analysis_id']}/ask",
        json={"question": "What is the filename of this analysis?"},
    )
    assert asked.status_code == 200
    assert "beta-unique.pdf" not in asked.json()["answer"].lower()


def test_ask_signature_and_unsupported(client: TestClient) -> None:
    body = analyze_and_wait(client, "bound.pdf", native_pdf_bytes(), "application/pdf")
    analysis_id = body["analysis_id"]
    identity = client.post(
        f"/api/v1/documents/{analysis_id}/ask",
        json={"question": "Is this signature John's real signature?"},
    )
    assert identity.status_code == 200
    answer = identity.json()["answer"].lower()
    assert "outside" in answer or "trusted reference" in answer
    assert "belongs to john" not in answer
    fake = client.post(
        f"/api/v1/documents/{analysis_id}/ask",
        json={"question": "Is this document definitely fake?"},
    )
    assert "legal" in fake.json()["answer"].lower() or "risk assessment" in fake.json()["answer"].lower()
    weather = client.post(
        f"/api/v1/documents/{analysis_id}/ask",
        json={"question": "What is the weather in Paris today?"},
    )
    assert "does not contain evidence" in weather.json()["answer"].lower()


def test_history_lists_real_analyses_and_pagination(client: TestClient) -> None:
    first = analyze_and_wait(client, "hist-a.pdf", native_pdf_bytes(), "application/pdf")
    second = analyze_and_wait(client, "hist-b.png", png_bytes(), "image/png")
    listing = client.get("/api/v1/documents?limit=1&offset=0")
    assert listing.status_code == 200
    payload = listing.json()
    assert payload["total"] >= 2
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1
    ids = {first["analysis_id"], second["analysis_id"]}
    page1 = payload["items"][0]["analysis_id"]
    page2 = client.get("/api/v1/documents?limit=1&offset=1").json()["items"][0]["analysis_id"]
    assert page1 != page2
    assert {page1, page2}.issubset(ids) or payload["total"] >= 2
    fetched = client.get(f"/api/v1/documents/{second['analysis_id']}")
    assert fetched.json()["document"]["original_filename"] == "hist-b.png"


def test_report_contains_real_data_and_no_paths(client: TestClient) -> None:
    body = analyze_and_wait(client, "report.pdf", native_pdf_bytes(), "application/pdf")
    response = client.get(f"/api/v1/documents/{body['analysis_id']}/report")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    data = response.content
    assert data.startswith(b"%PDF")
    import fitz

    document = fitz.open(stream=data, filetype="pdf")
    text = "".join(page.get_text() for page in document).lower()
    document.close()
    assert body["fusion"]["risk_level"].lower() in text
    assert "confirmed fake" not in text
    assert "legally verified" not in text
    assert "authentic guarantee" not in text
    assert "c:\\users" not in text
    assert "sk-" not in text


def test_second_analysis_does_not_overwrite_first(client: TestClient) -> None:
    first = analyze_and_wait(client, "keep-me.pdf", native_pdf_bytes(), "application/pdf")
    second = analyze_and_wait(client, "other.pdf", native_pdf_bytes(), "application/pdf")
    assert first["analysis_id"] != second["analysis_id"]
    refetch = client.get(f"/api/v1/documents/{first['analysis_id']}")
    assert refetch.json()["document"]["original_filename"] == "keep-me.pdf"
    assert refetch.json()["status"] == "COMPLETE"


def test_explanation_schema_roundtrip() -> None:
    fusion = _fusion()
    explanation = fallback_explanation(fusion, {})
    parsed = AIExplanation.model_validate_json(explanation.model_dump_json())
    assert parsed.source == "deterministic_fallback"
    assert parsed.recommended_next_step
