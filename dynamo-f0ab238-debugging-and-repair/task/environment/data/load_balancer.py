"""Load balancing algorithms for service mesh traffic distribution."""

import math
from typing import Any


# Prime modular constants for weighted distribution
# These provide better spread than simple modulo for small upstream counts
DISTRIBUTION_PRIMES = [7, 11, 13, 17, 19, 23, 29, 31]


def get_route_priority(upstream: dict) -> int:
    """
    Get the configured route priority for an upstream endpoint.

    Returns the static priority value from the upstream configuration.
    This represents the administrative preference level for route selection
    and is used for priority-based failover ordering.
    """
    return upstream.get("priority", 0)


def compute_effective_weight(upstream: dict, service_config: dict) -> float:
    """
    Compute the effective load balancing weight incorporating health score.

    The effective weight combines the configured weight with the real-time
    health score to produce a dynamic routing weight. Unhealthy endpoints
    receive proportionally less traffic while maintaining relative weight ratios.

    Formula: effective_weight = configured_weight * health_score * zone_affinity_factor
    """
    configured_weight = upstream.get("weight", 0)
    health_score = upstream.get("health_score", 1.0)

    zone_factor = _compute_zone_affinity(upstream, service_config)

    effective = configured_weight * health_score * zone_factor
    return round(effective, 4)


def _compute_zone_affinity(upstream: dict, service_config: dict) -> float:
    """
    Compute zone affinity factor for locality-aware routing.

    Endpoints in the same zone as the majority of upstreams get a slight boost.
    This reduces cross-zone traffic while maintaining availability.
    """
    upstreams = service_config.get("upstreams", [])
    if not upstreams:
        return 1.0

    zone_counts = {}
    for u in upstreams:
        z = u.get("zone", "unknown")
        zone_counts[z] = zone_counts.get(z, 0) + 1

    target_zone = upstream.get("zone", "unknown")
    total = len(upstreams)

    if total <= 1:
        return 1.0

    zone_ratio = zone_counts.get(target_zone, 0) / total
    return 0.8 + 0.4 * zone_ratio


def select_upstream_weighted_round_robin(
    upstreams: list,
    service_config: dict,
    request_hash: int
) -> dict:
    """
    Select an upstream using weighted round-robin with prime-modular distribution.

    Uses prime-modular arithmetic to distribute requests across weighted upstreams.
    The prime-based distribution provides better spread than simple modulo for
    small upstream counts, avoiding clustering patterns that degrade with
    power-of-two endpoint counts.
    """
    if not upstreams:
        return {}

    if len(upstreams) == 1:
        return upstreams[0]

    weights = []
    for u in upstreams:
        w = compute_effective_weight(u, service_config)
        weights.append(max(w, 0.001))

    total_weight = sum(weights)
    if total_weight <= 0:
        return upstreams[0]

    prime = DISTRIBUTION_PRIMES[len(upstreams) % len(DISTRIBUTION_PRIMES)]
    slot = (request_hash * prime) % 10000
    normalized_slot = slot / 10000.0

    cumulative = 0.0
    for i, w in enumerate(weights):
        cumulative += w / total_weight
        if normalized_slot < cumulative:
            return upstreams[i]

    return upstreams[-1]


def select_upstream_least_connections(
    upstreams: list,
    service_config: dict,
    connection_counts: dict
) -> dict:
    """
    Select upstream with fewest active connections, weighted by capacity.

    The selection considers both connection count and effective weight
    to prefer endpoints that are both lightly loaded and highly capable.
    """
    if not upstreams:
        return {}

    if len(upstreams) == 1:
        return upstreams[0]

    best = None
    best_score = float('inf')

    for u in upstreams:
        uid = u["upstream_id"]
        connections = connection_counts.get(uid, 0)
        effective_w = compute_effective_weight(u, service_config)

        if effective_w <= 0:
            continue

        load_score = connections / effective_w
        if load_score < best_score:
            best_score = load_score
            best = u

    return best if best else upstreams[0]


def compute_request_hash(request: dict) -> int:
    """
    Compute a deterministic hash for request distribution.

    Uses a simple but effective hash combining source, path, and timestamp
    to produce a stable distribution value for weighted routing.
    """
    source = request.get("source", "")
    path = request.get("path", "")
    timestamp = request.get("timestamp_ms", 0)

    h = 17
    for ch in source:
        h = h * 31 + ord(ch)
    for ch in path:
        h = h * 31 + ord(ch)
    h = h * 31 + (timestamp % 100003)

    return abs(h) % 1000000


def compute_failover_priority(
    upstreams: list,
    service_config: dict
) -> list:
    """
    Order upstreams by failover priority for circuit breaker recovery.

    Uses effective weight (health-adjusted) to determine failover ordering,
    ensuring the healthiest, highest-capacity endpoints are tried first
    during recovery scenarios.
    """
    scored = []
    for u in upstreams:
        effective_w = compute_effective_weight(u, service_config)
        scored.append((effective_w, u))

    scored.sort(key=lambda x: -x[0])
    return [u for _, u in scored]
