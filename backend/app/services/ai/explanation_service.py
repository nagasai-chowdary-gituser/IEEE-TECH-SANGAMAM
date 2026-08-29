from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.core.logging import get_logger
from app.schemas.ai import AIExplanation, AskGrounding, AskResponse, EvidenceExplanation
from app.schemas.fusion import FusionResult
from app.services.ai.base import AIProviderError
from app.services.ai.fallback import fallback_answer, fallback_explanation
from app.services.ai.prompts import (
    DISCLAIMER,
    EXPLANATION_JSON_INSTRUCTIONS,
    QA_JSON_INSTRUCTIONS,
    SYSTEM_PROMPT,
)
from app.services.ai.provider import OpenAICompatibleProvider
from app.services.ai.usage_context import mark_provider_failed

logger = get_logger(__name__)

_JSON_FENCE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


class QAModel(BaseModel):
    answer: str
    referenced_layers: list[str] = Field(default_factory=list)


def generate_explanation(
    *,
    fusion: FusionResult | None,
    context: dict[str, Any],
    settings: Settings,
) -> AIExplanation:
    fallback = fallback_explanation(fusion, context)
    provider = OpenAICompatibleProvider(settings)
    if not provider.configured():
        return fallback
    user = EXPLANATION_JSON_INSTRUCTIONS + "\n\nAnalysis context:\n" + json.dumps(context, default=str)
    parsed = _complete_validated(provider, user, AIExplanation, attempts=2)
    if parsed is None:
        return fallback
    parsed.source = "ai"
    parsed.disclaimer = DISCLAIMER
    parsed.strongest_evidence = _ground_evidence(parsed.strongest_evidence, fusion)
    if not parsed.recommended_next_step.strip() and fusion:
        parsed.recommended_next_step = fallback.recommended_next_step
    return parsed


def answer_question(
    *,
    question: str,
    fusion: FusionResult | None,
    context: dict[str, Any],
    settings: Settings,
) -> AskResponse:
    fallback = fallback_answer(question, fusion, context)
    provider = OpenAICompatibleProvider(settings)
    if not provider.configured():
        return fallback
    user = (
        QA_JSON_INSTRUCTIONS
        + f"\n\nUser question:\n{question.strip()}\n\nAnalysis context:\n"
        + json.dumps(context, default=str)
    )
    parsed = _complete_validated(provider, user, QAModel, attempts=2)
    if parsed is None:
        return fallback
    return AskResponse(
        answer=parsed.answer,
        grounding=AskGrounding(
            risk_level=fusion.risk_level if fusion else None,
            referenced_layers=list(parsed.referenced_layers),
        ),
        source="ai",
    )


def _complete_validated(provider: OpenAICompatibleProvider, user: str, model: type[BaseModel], attempts: int):
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            text = provider.complete_json(system=SYSTEM_PROMPT, user=user)
            data = _parse_json_object(text)
            return model.model_validate(data)
        except (AIProviderError, ValidationError, ValueError) as exc:
            last_error = exc
            logger.info("ai_output_retry reason=%s", type(exc).__name__)
    if last_error:
        mark_provider_failed()
        logger.warning("ai_output_fallback reason=%s", type(last_error).__name__)
    return None


def _parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    fenced = _JSON_FENCE.search(stripped)
    if fenced:
        stripped = fenced.group(1)
    data = json.loads(stripped)
    if not isinstance(data, dict):
        raise ValueError("AI output was not a JSON object.")
    return data


def _ground_evidence(
    items: list[EvidenceExplanation],
    fusion: FusionResult | None,
) -> list[EvidenceExplanation]:
    if fusion is None:
        return []
    if not fusion.top_findings:
        return []
    allowed_layers = {item.layer for item in fusion.top_findings}
    grounded = [item for item in items if item.layer in allowed_layers]
    if grounded:
        return grounded[:5]
    return [EvidenceExplanation(layer=item.layer, explanation=item.finding) for item in fusion.top_findings[:5]]
