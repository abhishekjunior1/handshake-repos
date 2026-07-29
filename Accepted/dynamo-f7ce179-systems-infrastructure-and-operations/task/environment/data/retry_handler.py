"""
Retry Handler Module

Manages retry policies with exponential backoff, per-request retry budgets,
and deadline propagation. Ensures retries respect both local budgets and
upstream deadline constraints.
"""

import math
from typing import Any


class RetryPolicy:
    """Defines retry behavior for a request category."""

    def __init__(self, max_retries: int = 3, base_delay: float = 0.1,
                 max_delay: float = 5.0, backoff_multiplier: float = 2.0,
                 budget_percent: float = 20.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.budget_percent = budget_percent

    def compute_delay(self, attempt: int) -> float:
        """Calculate exponential backoff delay for a given attempt number.

        delay = min(base_delay * (multiplier ^ attempt), max_delay)
        """
        delay = self.base_delay * (self.backoff_multiplier ** attempt)
        return min(delay, self.max_delay)

    def to_dict(self) -> dict:
        """Serialize policy configuration."""
        return {
            "max_retries": self.max_retries,
            "base_delay": self.base_delay,
            "max_delay": self.max_delay,
            "backoff_multiplier": self.backoff_multiplier,
            "budget_percent": self.budget_percent
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RetryPolicy":
        """Deserialize from dictionary."""
        return cls(
            max_retries=data.get("max_retries", 3),
            base_delay=data.get("base_delay", 0.1),
            max_delay=data.get("max_delay", 5.0),
            backoff_multiplier=data.get("backoff_multiplier", 2.0),
            budget_percent=data.get("budget_percent", 20.0)
        )


class RetryBudget:
    """Tracks retry budget across requests to prevent retry storms."""

    def __init__(self, total_requests: int, budget_percent: float = 20.0,
                 min_retries: int = 3):
        self.total_requests = max(total_requests, 1)
        self.budget_percent = budget_percent
        self.min_retries = min_retries
        self._retries_used = 0
        self._max_retries = max(
            min_retries,
            int(math.ceil(total_requests * budget_percent / 100.0))
        )

    @property
    def remaining(self) -> int:
        """Number of retries still available in the budget."""
        return max(0, self._max_retries - self._retries_used)

    @property
    def max_budget(self) -> int:
        """Total retry budget allocated."""
        return self._max_retries

    def can_retry(self) -> bool:
        """Check if retry budget allows another attempt."""
        return self._retries_used < self._max_retries

    def consume(self) -> bool:
        """Consume one retry from the budget. Returns False if exhausted."""
        if not self.can_retry():
            return False
        self._retries_used += 1
        return True

    def reset(self) -> None:
        """Reset used retries to zero."""
        self._retries_used = 0

    def to_dict(self) -> dict:
        """Serialize budget state."""
        return {
            "total_requests": self.total_requests,
            "max_budget": self._max_retries,
            "retries_used": self._retries_used,
            "remaining": self.remaining
        }


class DeadlinePropagation:
    """Manages request deadlines across service hops."""

    def __init__(self, original_deadline: float, hop_overhead: float = 0.005):
        self.original_deadline = original_deadline
        self.hop_overhead = hop_overhead

    def remaining_time(self, current_time: float) -> float:
        """Calculate remaining time before deadline expiry."""
        return max(0.0, self.original_deadline - current_time)

    def can_retry(self, current_time: float, estimated_latency: float) -> bool:
        """Check if there is enough time remaining for a retry attempt."""
        remaining = self.remaining_time(current_time)
        return remaining > (estimated_latency + self.hop_overhead)

    def propagate(self, current_time: float) -> float:
        """Calculate the deadline to propagate to downstream service."""
        remaining = self.remaining_time(current_time)
        return current_time + remaining - self.hop_overhead

    def is_expired(self, current_time: float) -> bool:
        """Check if the deadline has already passed."""
        return current_time >= self.original_deadline


class RetryHandler:
    """Orchestrates retry decisions combining policy, budget, and deadline."""

    def __init__(self, policy: RetryPolicy, budget: RetryBudget,
                 deadline: DeadlinePropagation = None):
        self.policy = policy
        self.budget = budget
        self.deadline = deadline
        self._current_attempt = 0

    def should_retry(self, current_time: float = 0.0) -> bool:
        """Determine if a retry should be attempted.

        Checks in order: attempt count, budget availability, deadline.
        """
        if self._current_attempt >= self.policy.max_retries:
            return False
        if not self.budget.can_retry():
            return False
        if self.deadline and self.deadline.is_expired(current_time):
            return False
        return True

    def execute_retry(self, current_time: float = 0.0) -> dict:
        """Consume a retry and return retry metadata.

        Returns dict with delay, attempt number, and remaining budget.
        """
        if not self.should_retry(current_time):
            return {"allowed": False, "reason": "budget_or_deadline_exhausted"}

        self.budget.consume()
        delay = self.policy.compute_delay(self._current_attempt)
        self._current_attempt += 1

        return {
            "allowed": True,
            "attempt": self._current_attempt,
            "delay": delay,
            "remaining_budget": self.budget.remaining
        }

    @property
    def attempts_made(self) -> int:
        """Number of retry attempts executed."""
        return self._current_attempt

    def reset(self) -> None:
        """Reset attempt counter for a new request."""
        self._current_attempt = 0

    def to_dict(self) -> dict:
        """Serialize handler state."""
        return {
            "attempts_made": self._current_attempt,
            "policy": self.policy.to_dict(),
            "budget": self.budget.to_dict()
        }
