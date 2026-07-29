"""
Token bucket rate limiter for per-consumer throughput control.

Each consumer has an independent token bucket with configurable capacity
and refill rate. Tokens are consumed on task dispatch and replenished
at the start of each processing tick.
"""

from typing import Optional


class TokenBucket:
    """
    Token bucket implementation for a single consumer.

    Attributes:
        capacity: Maximum tokens the bucket can hold (burst limit)
        tokens: Current available tokens
        refill_rate: Tokens added per tick
    """

    def __init__(self, capacity: int, refill_rate: int):
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.total_consumed = 0
        self.total_throttled = 0

    def consume(self) -> bool:
        """Attempt to consume one token. Returns True if successful."""
        if self.tokens > 0:
            self.tokens -= 1
            self.total_consumed += 1
            return True
        self.total_throttled += 1
        return False

    def refill(self) -> None:
        """Refill tokens up to capacity based on refill rate."""
        self.tokens = min(self.capacity, self.tokens + self.refill_rate)

    def has_capacity(self) -> bool:
        """Check if at least one token is available without consuming."""
        return self.tokens > 0

    def get_stats(self) -> dict:
        return {
            "capacity": self.capacity,
            "current_tokens": self.tokens,
            "refill_rate": self.refill_rate,
            "total_consumed": self.total_consumed,
            "total_throttled": self.total_throttled,
        }


class RateLimiterRegistry:
    """
    Manages per-consumer rate limiters.

    Each registered consumer gets an independent token bucket.
    The registry handles tick-based refill across all consumers.
    """

    def __init__(self, default_capacity: int = 10, default_refill: int = 10):
        self._buckets: dict[str, TokenBucket] = {}
        self._default_capacity = default_capacity
        self._default_refill = default_refill
        self._current_tick = 0

    def register_consumer(self, consumer_id: str, capacity: Optional[int] = None,
                          refill_rate: Optional[int] = None) -> None:
        """Register a new consumer with its rate limit configuration."""
        cap = capacity if capacity is not None else self._default_capacity
        refill = refill_rate if refill_rate is not None else self._default_refill
        self._buckets[consumer_id] = TokenBucket(cap, refill)

    def check_rate_limit(self, consumer_id: str) -> bool:
        """Check if consumer has available capacity without consuming a token."""
        if consumer_id not in self._buckets:
            return True
        return self._buckets[consumer_id].has_capacity()

    def consume_token(self, consumer_id: str) -> bool:
        """Consume a token for the given consumer. Returns False if rate-limited."""
        if consumer_id not in self._buckets:
            return True
        return self._buckets[consumer_id].consume()

    def tick(self) -> None:
        """Advance one processing tick — refill all consumer buckets."""
        self._current_tick += 1
        for bucket in self._buckets.values():
            bucket.refill()

    def get_current_tick(self) -> int:
        return self._current_tick

    def is_consumer_throttled(self, consumer_id: str) -> bool:
        """Check if consumer is currently throttled (no tokens available)."""
        if consumer_id not in self._buckets:
            return False
        return not self._buckets[consumer_id].has_capacity()

    def get_consumer_stats(self, consumer_id: str) -> dict:
        if consumer_id not in self._buckets:
            return {}
        return self._buckets[consumer_id].get_stats()

    def get_all_stats(self) -> dict:
        return {
            "current_tick": self._current_tick,
            "consumers": {
                cid: bucket.get_stats()
                for cid, bucket in self._buckets.items()
            }
        }

    def reset_all(self) -> None:
        """Reset all buckets to full capacity."""
        for bucket in self._buckets.values():
            bucket.tokens = bucket.capacity
