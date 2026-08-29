from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class CacheStats:
    hits: int = 0
    misses: int = 0
    stores: int = 0
    failures: int = 0


class TtlMemoryCache:
    """Process-local TTL cache. Fail-open: callers should treat errors as misses."""

    def __init__(self, *, max_items: int = 512) -> None:
        self._max_items = max_items
        self._lock = threading.Lock()
        self._items: dict[str, tuple[float, str]] = {}
        self.stats = CacheStats()

    def get(self, key: str) -> str | None:
        now = time.monotonic()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                self.stats.misses += 1
                return None
            expires_at, value = item
            if expires_at <= now:
                self._items.pop(key, None)
                self.stats.misses += 1
                return None
            self.stats.hits += 1
            return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        expires_at = time.monotonic() + ttl_seconds
        with self._lock:
            self._evict_locked()
            self._items[key] = (expires_at, value)
            self.stats.stores += 1

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self.stats = CacheStats()

    def record_failure(self) -> None:
        with self._lock:
            self.stats.failures += 1

    def _evict_locked(self) -> None:
        now = time.monotonic()
        expired = [key for key, (expires_at, _) in self._items.items() if expires_at <= now]
        for key in expired:
            self._items.pop(key, None)
        if len(self._items) < self._max_items:
            return
        oldest = sorted(self._items.items(), key=lambda item: item[1][0])
        for key, _ in oldest[: max(1, len(self._items) - self._max_items + 1)]:
            self._items.pop(key, None)


ask_response_cache = TtlMemoryCache()
