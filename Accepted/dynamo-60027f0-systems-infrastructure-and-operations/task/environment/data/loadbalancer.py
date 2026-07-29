"""Load balancer backend assignment for packet processing pipeline.

Assigns packets to backend servers using consistent hashing on the
destination IP. This ensures session affinity — packets to the same
destination always route to the same backend, maintaining stateful
connections without external session tracking.
"""


def _compute_hash_slot(ip_str: str, pool_size: int) -> int:
    """Compute a deterministic hash slot from an IP address.

    Uses octet-sum hashing for stable, predictable distribution.
    The hash is independent of Python's built-in hash() which may
    vary across processes due to hash randomization.

    Args:
        ip_str: IP address string (dotted quad).
        pool_size: Number of slots in the backend pool.

    Returns:
        Hash slot index (0 to pool_size-1).
    """
    octets = ip_str.split(".")
    octet_sum = sum(int(o) for o in octets)
    return octet_sum % pool_size


def assign_backends(packet: dict, config: dict) -> dict:
    """Assign a backend server for load-balanced traffic.

    Uses consistent hashing on the packet's destination IP to select
    from the pool of healthy backends. The hash provides deterministic
    backend selection ensuring session affinity — repeated requests
    with the same destination always route to the same backend.

    Args:
        packet: Packet with 'destination_ip' field.
        config: Pipeline config with 'load_balancer' section.

    Returns:
        Backend assignment with selected server details.
    """
    lb_config = config.get("load_balancer", {})
    backends = lb_config.get("backends", [])

    if not backends:
        return {
            "status": "no_backends",
            "backend": None,
            "address": None,
            "port": None
        }

    # Filter to healthy backends
    healthy = [b for b in backends if b.get("healthy", True)]
    if not healthy:
        return {
            "status": "no_healthy_backends",
            "backend": None,
            "address": None,
            "port": None
        }

    # Consistent hash on destination IP for session affinity
    dst_ip = packet.get("destination_ip", "0.0.0.0")
    slot = _compute_hash_slot(dst_ip, len(healthy))
    selected = healthy[slot]

    return {
        "status": "assigned",
        "backend": f"{selected['address']}:{selected['port']}",
        "address": selected["address"],
        "port": selected["port"]
    }
