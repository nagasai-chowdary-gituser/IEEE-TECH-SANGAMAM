from __future__ import annotations

from typing import Any

from app.schemas.ai import AIExplanation, AskResponse, EvidenceExplanation
from app.schemas.fusion import FusionResult
from app.services.ai.prompts import ACTION_LABELS, DISCLAIMER


def fallback_explanation(fusion: FusionResult | None, context: dict[str, Any]) -> AIExplanation:
    if fusion is None:
        return AIExplanation(
            summary="A complete risk assessment is not available for this analysis yet.",
            risk_explanation="Forensic layers have not produced a fused assessment.",
            strongest_evidence=[],
            corroboration_explanation="Corroboration cannot be evaluated without a completed fusion result.",
            limitations_explanation="The analysis is incomplete.",
            recommended_next_step=ACTION_LABELS["REANALYZE_WITH_HIGHER_QUALITY_SOURCE"],
            disclaimer=DISCLAIMER,
            source="deterministic_fallback",
        )
    strongest = [
        EvidenceExplanation(layer=item.layer, explanation=item.finding)
        for item in fusion.top_findings[:5]
    ]
    limitations = " ".join(fusion.limitations) if fusion.limitations else (
        "No additional module limitations were recorded for the completed layers."
    )
    return AIExplanation(
        summary=fusion.assessment_summary,
        risk_explanation=(
            f"The deterministic fusion engine assigned {fusion.risk_level} "
            f"(score {fusion.overall_risk_score}) with assessment confidence "
            f"{fusion.assessment_confidence:.2f} and analysis coverage {fusion.analysis_coverage:.2f}."
        ),
        strongest_evidence=strongest,
        corroboration_explanation=fusion.corroboration.description,
        limitations_explanation=limitations,
        recommended_next_step=ACTION_LABELS.get(
            fusion.recommended_action,
            fusion.recommended_action,
        ),
        disclaimer=DISCLAIMER,
        source="deterministic_fallback",
    )


def fallback_answer(question: str, fusion: FusionResult | None, context: dict[str, Any]) -> AskResponse:
    text = question.strip().lower()
    risk = fusion.risk_level if fusion else None
    layers: list[str] = []

    if _is_certainty_question(text):
        answer = (
            "DocuVerify provides a forensic manipulation risk assessment based on available "
            "digital evidence. It cannot declare a document definitely fake or legally authentic."
        )
        if fusion:
            answer += f" The completed assessment is {fusion.risk_level} with score {fusion.overall_risk_score}."
        return AskResponse(
            answer=answer,
            grounding={"risk_level": risk, "referenced_layers": ["fusion"] if fusion else []},
            source="deterministic_fallback",
        )

    if _is_identity_question(text):
        return AskResponse(
            answer=(
                "Signer identity verification requires a trusted reference signature and is outside "
                "this analysis. DocuVerify does not determine whether a signature belongs to a named person."
            ),
            grounding={"risk_level": risk, "referenced_layers": []},
            source="deterministic_fallback",
        )

    if fusion and ("strongest" in text or "contributed most" in text or "top finding" in text):
        if not fusion.top_findings:
            answer = "The completed analysis did not record ranked findings. No meaningful evidence list is available."
        else:
            lines = [f"{item.rank}. {item.layer}: {item.finding}" for item in fusion.top_findings[:5]]
            answer = "Strongest recorded evidence from the completed analysis:\n" + "\n".join(lines)
            layers = [item.layer for item in fusion.top_findings]
        return AskResponse(
            answer=answer,
            grounding={"risk_level": risk, "referenced_layers": layers},
            source="deterministic_fallback",
        )

    if fusion and ("inconclusive" in text or "coverage" in text or "limited" in text):
        layers = [row.layer for row in fusion.layer_contributions if row.status in {"failed", "unavailable", "limited"}]
        answer = fusion.assessment_summary
        if fusion.limitations:
            answer += " Limitations: " + " ".join(fusion.limitations[:4])
        return AskResponse(
            answer=answer,
            grounding={"risk_level": risk, "referenced_layers": layers},
            source="deterministic_fallback",
        )

    if fusion and ("metadata" in text):
        meta = context.get("metadata") or {}
        answer = meta.get("summary") or "The completed analysis does not contain additional metadata detail for that question."
        return AskResponse(
            answer=answer,
            grounding={"risk_level": risk, "referenced_layers": ["metadata"]},
            source="deterministic_fallback",
        )

    if fusion and ("ela" in text or "error level" in text):
        visual = context.get("visual_forensics") or {}
        answer = visual.get("ela_summary") or "The completed analysis does not contain an ELA summary for that question."
        return AskResponse(
            answer=answer,
            grounding={"risk_level": risk, "referenced_layers": ["ela"]},
            source="deterministic_fallback",
        )

    if fusion and ("copy-move" in text or "copy move" in text or "duplicat" in text):
        visual = context.get("visual_forensics") or {}
        answer = visual.get("copy_move_summary") or "The completed analysis does not contain copy-move detail for that question."
        return AskResponse(
            answer=answer,
            grounding={"risk_level": risk, "referenced_layers": ["copy_move"]},
            source="deterministic_fallback",
        )

    if _is_unsupported_question(text):
        return AskResponse(
            answer="The completed analysis does not contain evidence to answer that question.",
            grounding={"risk_level": risk, "referenced_layers": []},
            source="deterministic_fallback",
        )

    if fusion:
        return AskResponse(
            answer=fusion.assessment_summary,
            grounding={"risk_level": risk, "referenced_layers": ["fusion"]},
            source="deterministic_fallback",
        )

    return AskResponse(
        answer="The completed analysis does not contain evidence to answer that question.",
        grounding={"risk_level": risk, "referenced_layers": []},
        source="deterministic_fallback",
    )


def _is_certainty_question(text: str) -> bool:
    needles = (
        "definitely fake",
        "definitely forged",
        "is this fake",
        "is it fake",
        "authentic",
        "legally",
        "100% fake",
        "confirmed fake",
    )
    return any(item in text for item in needles)


def _is_identity_question(text: str) -> bool:
    needles = ("signature", "signer", "who signed", "john's", "belongs to")
    return any(item in text for item in needles)


def _is_unsupported_question(text: str) -> bool:
    needles = (
        "weather",
        "stock price",
        "recipe",
        "capital of",
        "write python",
        "unrelated",
    )
    return any(item in text for item in needles)
