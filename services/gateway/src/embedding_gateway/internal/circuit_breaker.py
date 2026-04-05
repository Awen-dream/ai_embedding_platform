from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from time import monotonic

from embedding_platform_common.errors import PlatformError


@dataclass
class BreakerState:
    """State snapshot for one downstream dependency breaker."""

    consecutive_failures: int = 0
    opened_until: float = 0.0


class CircuitBreakerRegistry:
    """Tracks downstream failures and temporarily blocks requests to unstable dependencies."""

    def __init__(self, *, failure_threshold: int, recovery_seconds: float) -> None:
        self._failure_threshold = failure_threshold
        self._recovery_seconds = recovery_seconds
        self._lock = Lock()
        self._states: dict[str, BreakerState] = {}

    def before_request(self, name: str) -> None:
        """Reject requests while the breaker is open for the named downstream service."""
        with self._lock:
            state = self._states.get(name)
            if state is None:
                return
            if state.opened_until > monotonic():
                raise PlatformError(
                    code="SYS-DEP-503002",
                    message=f"downstream circuit is open for {name}",
                    error_type="dependency_error",
                    status_code=503,
                    retryable=True,
                )

    def record_success(self, name: str) -> None:
        """Reset breaker state after a successful downstream call."""
        with self._lock:
            self._states[name] = BreakerState()

    def record_failure(self, name: str) -> None:
        """Increment failure count and open the breaker when the threshold is reached."""
        with self._lock:
            state = self._states.get(name) or BreakerState()
            state.consecutive_failures += 1
            if state.consecutive_failures >= self._failure_threshold:
                state.opened_until = monotonic() + self._recovery_seconds
                state.consecutive_failures = 0
            self._states[name] = state
