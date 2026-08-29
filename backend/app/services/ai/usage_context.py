from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0


_token_usage: ContextVar[TokenUsage | None] = ContextVar("ai_token_usage", default=None)
_provider_failed: ContextVar[bool] = ContextVar("ai_provider_failed", default=False)


def reset_ai_call_stats() -> None:
    _token_usage.set(TokenUsage())
    _provider_failed.set(False)


def add_token_usage(*, input_tokens: int, output_tokens: int) -> None:
    current = _token_usage.get() or TokenUsage()
    _token_usage.set(
        TokenUsage(
            input_tokens=current.input_tokens + max(0, input_tokens),
            output_tokens=current.output_tokens + max(0, output_tokens),
        )
    )


def consume_token_usage() -> TokenUsage:
    usage = _token_usage.get() or TokenUsage()
    _token_usage.set(TokenUsage())
    return usage


def mark_provider_failed() -> None:
    _provider_failed.set(True)


def consume_provider_failed() -> bool:
    failed = _provider_failed.get()
    _provider_failed.set(False)
    return failed
