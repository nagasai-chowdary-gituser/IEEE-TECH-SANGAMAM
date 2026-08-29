from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    def complete_json(self, *, system: str, user: str) -> str:
        """Return a JSON object as text. Raise AIProviderError on failure."""
        ...


class AIProviderError(Exception):
    """Provider is unavailable, misconfigured, or returned an unusable response."""
