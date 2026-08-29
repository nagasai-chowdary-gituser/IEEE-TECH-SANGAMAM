from __future__ import annotations

import httpx

from app.core.config import Settings
from app.core.logging import get_logger
from app.services.ai.base import AIProviderError
from app.services.ai.usage_context import add_token_usage

logger = get_logger(__name__)


class OpenAICompatibleProvider:
    """OpenAI Chat Completions compatible JSON responder. API key stays server-side."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def configured(self) -> bool:
        provider = (self._settings.ai_provider or "openai").strip().lower()
        if provider in {"none", "off", "disabled"}:
            return False
        return bool(self._settings.ai_api_key.strip())

    def complete_json(self, *, system: str, user: str) -> str:
        if not self.configured():
            raise AIProviderError("AI provider is not configured.")
        url = self._settings.ai_base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.ai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._settings.ai_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            with httpx.Client(timeout=self._settings.ai_timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.warning("ai_provider_network_error")
            raise AIProviderError("The explanation service is temporarily unavailable.") from exc
        if response.status_code >= 400:
            logger.warning("ai_provider_http_error status=%s", response.status_code)
            raise AIProviderError("The explanation service is temporarily unavailable.")
        try:
            body = response.json()
            content = body["choices"][0]["message"]["content"]
            usage = body.get("usage") if isinstance(body, dict) else None
            if isinstance(usage, dict):
                add_token_usage(
                    input_tokens=int(usage.get("prompt_tokens") or 0),
                    output_tokens=int(usage.get("completion_tokens") or 0),
                )
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIProviderError("The explanation service returned an unusable response.") from exc
        if not isinstance(content, str) or not content.strip():
            raise AIProviderError("The explanation service returned an empty response.")
        return content
