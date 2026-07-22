"""
Circuit Breaker Module

Implements the circuit breaker pattern with three states: CLOSED, OPEN,
and HALF_OPEN. Monitors failure rates and prevents cascading failures
by short-circuiting requests to unhealthy backends.
"""

from enum import Enum
from typing import Any


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Per-backend circuit breaker with configurable thresholds."""

    def __init__(self, backend_id: str, failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 half_open_max_requests: int = 1,
                 success_threshold: int = 3):
        self.backend_id = backend_id
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_requests = half_open_max_requests
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_requests = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state

    @property
    def failure_count(self) -> int:
        """Current consecutive failure count."""
        return self._failure_count

    def evaluate_state(self, current_time: float) -> CircuitState:
        """Evaluate and potentially transition the circuit state.

        State transitions:
            CLOSED -> OPEN: when failure_count >= failure_threshold
            OPEN -> HALF_OPEN: when recovery_timeout has elapsed
            HALF_OPEN -> CLOSED: when success_threshold met
            HALF_OPEN -> OPEN: on any failure
        """
        if self._state == CircuitState.OPEN:
            if current_time - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_requests = 0
                self._success_count = 0
        return self._state

    def allow_request(self, current_time: float) -> bool:
        """Determine if a request should be allowed through.

        Returns True if the circuit is CLOSED or HALF_OPEN with capacity.
        """
        state = self.evaluate_state(current_time)
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.HALF_OPEN:
            return self._half_open_requests < self.half_open_max_requests
        return False

    def record_success(self) -> None:
        """Record a successful request."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self, current_time: float) -> None:
        """Record a failed request and potentially open the circuit."""
        self._failure_count += 1
        self._last_failure_time = current_time
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._half_open_requests = 0
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def record_half_open_attempt(self) -> None:
        """Track requests made during HALF_OPEN state."""
        self._half_open_requests += 1

    def reset(self) -> None:
        """Reset circuit breaker to initial CLOSED state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_requests = 0

    def to_dict(self) -> dict:
        """Serialize circuit breaker state."""
        return {
            "backend_id": self.backend_id,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "last_failure_time": self._last_failure_time
        }


class CircuitBreakerRegistry:
    """Manages circuit breakers for all backends."""

    def __init__(self, failure_threshold: int = 5,
                 recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_breaker(self, backend_id: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a backend."""
        if backend_id not in self._breakers:
            self._breakers[backend_id] = CircuitBreaker(
                backend_id=backend_id,
                failure_threshold=self.failure_threshold,
                recovery_timeout=self.recovery_timeout
            )
        return self._breakers[backend_id]

    def initialize_from_backends(self, backends: list,
                                 failure_counts: dict = None) -> None:
        """Pre-populate breakers from a list of backends with known failures."""
        failure_counts = failure_counts or {}
        for backend in backends:
            breaker = self.get_breaker(backend.backend_id)
            count = failure_counts.get(backend.backend_id,
                                       backend.failure_count)
            for _ in range(count):
                breaker.record_failure(0.0)

    def allow_request(self, backend_id: str, current_time: float) -> bool:
        """Check if the circuit allows a request to the given backend."""
        return self.get_breaker(backend_id).allow_request(current_time)

    def get_all_states(self) -> dict[str, str]:
        """Return current state of all circuit breakers."""
        return {bid: b.state.value for bid, b in self._breakers.items()}

    def to_dict(self) -> dict:
        """Serialize all circuit breaker states."""
        return {
            "breakers": {bid: b.to_dict() for bid, b in self._breakers.items()}
        }
