from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.core.config import Settings


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int
    reason: str


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {}

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> RateLimitDecision:
        if limit <= 0:
            return RateLimitDecision(True, 0, "disabled")
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            stamps = [stamp for stamp in self._hits.get(key, []) if stamp > cutoff]
            if len(stamps) >= limit:
                retry = max(1, int(window_seconds - (now - stamps[0])) + 1)
                self._hits[key] = stamps
                return RateLimitDecision(False, retry, "per_minute")
            stamps.append(now)
            self._hits[key] = stamps
            return RateLimitDecision(True, 0, "ok")

    def recent_count(self, key: str, *, window_seconds: int = 60) -> int:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            stamps = [stamp for stamp in self._hits.get(key, []) if stamp > cutoff]
            self._hits[key] = stamps
            return len(stamps)


minute_limiter = SlidingWindowLimiter()


def raise_too_many_requests(retry_after: int, *, daily: bool = False) -> None:
    detail = (
        "Daily AI request quota exceeded. Try again tomorrow."
        if daily
        else "Too many AI requests. Try again shortly."
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(max(1, retry_after))},
    )


def enforce_minute_limit(*, subject: str, ip: str, authenticated: bool, settings: Settings) -> None:
    if authenticated:
        decision = minute_limiter.check(f"user:{subject}", limit=settings.ai_rate_limit_per_minute)
    else:
        decision = minute_limiter.check(f"ip:{ip}", limit=settings.ai_rate_limit_ip_per_minute)
    if not decision.allowed:
        raise_too_many_requests(decision.retry_after_seconds)
