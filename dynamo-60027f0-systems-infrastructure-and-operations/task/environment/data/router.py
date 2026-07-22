"""Route selection module for packet processing pipeline.

Selects the best next-hop for a packet based on destination IP
matching against configured routes. Uses longest-prefix match
with priority and metric as tiebreakers. Checks TTL expiry
before forwarding.
"""

import ipaddress


def _match_route(destination_ip: str, routes: list) -> dict:
    """Find the best matching route for a destination IP.

    Evaluates all configured routes using longest-prefix match.
    Among routes with equal prefix length, lower priority wins.
    Among equal priority, lower metric wins.

    Args:
        destination_ip: The IP address to route.
        routes: List of route configurations.

    Returns:
        Best matching route dict, or None if no match.
    """
    ip_addr = ipaddress.ip_address(destination_ip)
    candidates = []

    for route in routes:
        network = ipaddress.ip_network(route["network"], strict=False)
        if ip_addr in network:
            candidates.append({
                "route": route,
                "prefix_length": network.prefixlen
            })

    if not candidates:
        return None

    # Sort: longest prefix first, then lowest priority, then lowest metric
    best = max(candidates, key=lambda c: (
        c["prefix_length"],
        -c["route"]["priority"],
        -c["route"]["metric"]
    ))
    return best["route"]


def select_routes(packet: dict, config: dict) -> dict:
    """Select the forwarding route for a packet.

    Checks TTL expiry first (drop expired packets), then performs
    longest-prefix-match route lookup on the packet's destination IP.

    Args:
        packet: Packet with 'destination_ip' and optional 'ttl'.
        config: Pipeline config with 'routes' list.

    Returns:
        Route selection result with next-hop and interface.
    """
    destination_ip = packet.get("destination_ip")
    if not destination_ip:
        return {
            "status": "no_destination",
            "destination": None,
            "next_hop": None,
            "interface": None,
            "network": None
        }

    # Check TTL expiry
    if packet.get("ttl", 64) <= 0:
        return {
            "status": "ttl_expired",
            "destination": destination_ip,
            "next_hop": None,
            "interface": None,
            "network": None
        }

    routes = config.get("routes", [])
    best_route = _match_route(destination_ip, routes)

    if best_route is None:
        return {
            "status": "no_route",
            "destination": destination_ip,
            "next_hop": None,
            "interface": None,
            "network": None
        }

    return {
        "status": "routed",
        "destination": destination_ip,
        "next_hop": best_route["next_hop"],
        "interface": best_route["interface"],
        "network": best_route["network"]
    }
