from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass
class BucketState:
    """Current token bucket state for a single logical rate-limit key."""

    tokens: float
    updated_at: float


class TokenBucketRateLimiter:
    """Simple in-memory token bucket limiter used at the gateway edge."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._buckets: dict[str, BucketState] = {}

    def allow(self, key: str, limit_per_minute: int) -> bool:
        """Consume one token from the bucket and report whether the request is allowed."""
        if limit_per_minute <= 0:
            return False
        capacity = float(limit_per_minute)
        refill_rate = capacity / 60.0
        now = monotonic()
        with self._lock:
            state = self._buckets.get(key)
            if state is None:
                state = BucketState(tokens=capacity, updated_at=now)
            else:
                elapsed = now - state.updated_at
                state.tokens = min(capacity, state.tokens + elapsed * refill_rate)
                state.updated_at = now

            if state.tokens < 1.0:
                self._buckets[key] = state
                return False

            state.tokens -= 1.0
            self._buckets[key] = state
            return True
