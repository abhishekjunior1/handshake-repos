"""
Load Balancer Module

Implements multiple load balancing strategies for distributing traffic
across backend instances: weighted round-robin, consistent hashing with
virtual nodes, and least-connections selection.
"""

import hashlib
from typing import Any

KNUTH_MULTIPLIER = 2654435761


class WeightedRoundRobin:
    """Distributes requests proportionally based on backend weights."""

    def __init__(self):
        self._counters: dict[str, int] = {}

    def select(self, backends: list, group_key: str = "default") -> Any:
        """Select next backend using weighted round-robin.

        Args:
            backends: List of backend objects with .weight and .backend_id
            group_key: Grouping key for independent round-robin counters
        """
        if not backends:
            return None
        total_weight = sum(b.weight for b in backends)
        if total_weight == 0:
            return backends[0]

        counter = self._counters.get(group_key, 0)
        position = counter % total_weight

        cumulative = 0
        for backend in backends:
            cumulative += backend.weight
            if position < cumulative:
                self._counters[group_key] = counter + 1
                return backend

        self._counters[group_key] = counter + 1
        return backends[-1]

    def reset(self, group_key: str = None) -> None:
        """Reset round-robin counters."""
        if group_key:
            self._counters.pop(group_key, None)
        else:
            self._counters.clear()


class ConsistentHashRing:
    """Consistent hashing ring with virtual nodes for uniform distribution."""

    def __init__(self, ring_size: int = 65536, virtual_nodes: int = 150):
        self.ring_size = ring_size
        self.virtual_nodes = virtual_nodes
        self._ring: list[tuple[int, Any]] = []
        self._sorted = False

    def add_node(self, backend: Any) -> None:
        """Add a backend with virtual nodes to the ring."""
        for i in range(self.virtual_nodes):
            key = f"{backend.backend_id}:vnode:{i}"
            hash_val = self._hash(key)
            # Apply Knuth multiplicative hash for better ring distribution
            position = (hash_val * KNUTH_MULTIPLIER) % self.ring_size
            self._ring.append((position, backend))
        self._sorted = False

    def remove_node(self, backend_id: str) -> None:
        """Remove all virtual nodes for a backend."""
        self._ring = [(pos, b) for pos, b in self._ring
                      if b.backend_id != backend_id]
        self._sorted = False

    def get_node(self, key: str) -> Any:
        """Find the backend responsible for the given key.

        Uses consistent hashing to map the key to a position on the ring,
        then finds the next node clockwise from that position.
        """
        if not self._ring:
            return None
        if not self._sorted:
            self._ring.sort(key=lambda x: x[0])
            self._sorted = True

        hash_val = self._hash(key)
        position = (hash_val * KNUTH_MULTIPLIER) % self.ring_size

        # Binary search for the next node clockwise
        low, high = 0, len(self._ring) - 1
        result_idx = 0

        while low <= high:
            mid = (low + high) // 2
            if self._ring[mid][0] >= position:
                result_idx = mid
                high = mid - 1
            else:
                low = mid + 1

        if low > len(self._ring) - 1:
            result_idx = 0

        return self._ring[result_idx][1]

    def build_ring(self, backends: list) -> None:
        """Rebuild the ring from a list of backends."""
        self._ring.clear()
        self._sorted = False
        for backend in backends:
            self.add_node(backend)

    def _hash(self, key: str) -> int:
        """Compute a deterministic hash for a key."""
        digest = hashlib.md5(key.encode()).hexdigest()
        return int(digest[:8], 16)


class LeastConnections:
    """Selects the backend with the fewest active connections."""

    def __init__(self):
        self._connections: dict[str, int] = {}

    def select(self, backends: list) -> Any:
        """Choose the backend with minimum active connections."""
        if not backends:
            return None
        min_conns = float('inf')
        selected = backends[0]
        for backend in backends:
            conns = self._connections.get(backend.backend_id, 0)
            if conns < min_conns:
                min_conns = conns
                selected = backend
        return selected

    def increment(self, backend_id: str) -> None:
        """Record a new connection to a backend."""
        self._connections[backend_id] = self._connections.get(backend_id, 0) + 1

    def decrement(self, backend_id: str) -> None:
        """Record a closed connection."""
        current = self._connections.get(backend_id, 0)
        self._connections[backend_id] = max(0, current - 1)

    def get_count(self, backend_id: str) -> int:
        """Get current connection count for a backend."""
        return self._connections.get(backend_id, 0)

    def reset(self) -> None:
        """Reset all connection counters."""
        self._connections.clear()
