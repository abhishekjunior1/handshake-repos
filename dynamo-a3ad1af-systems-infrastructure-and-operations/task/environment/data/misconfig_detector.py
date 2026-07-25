"""
Misconfiguration detector. Identifies common network configuration issues
including asymmetric routes, routing black holes, and MTU mismatches along paths.
"""

from topology_loader import get_link_between, get_router_by_id


def detect_misconfigurations(topology: dict, routing_tables: dict) -> dict:
    """Run all misconfiguration detection checks.

    Args:
        topology: Network topology.
        routing_tables: Pre-computed routing tables for all routers.

    Returns:
        Dict with detected misconfigurations categorized by type.
    """
    results = {
        "asymmetric_routes": detect_asymmetric_routes(topology, routing_tables),
        "black_holes": detect_black_holes(topology, routing_tables),
        "mtu_mismatches": detect_mtu_mismatches(topology, routing_tables),
        "total_issues": 0,
    }
    results["total_issues"] = (
        len(results["asymmetric_routes"])
        + len(results["black_holes"])
        + len(results["mtu_mismatches"])
    )
    return results


def detect_asymmetric_routes(topology: dict, routing_tables: dict) -> list:
    """Detect routes where the forward and return paths differ in cost.

    An asymmetric route exists when the cost from A to B differs from B to A
    by more than the asymmetry threshold.
    """
    issues = []
    checked_pairs = set()
    asymmetry_threshold = 10  # cost difference threshold

    for router in topology["routers"]:
        src_id = router["id"]
        src_routes = routing_tables.get(src_id, [])

        for route in src_routes:
            if route["route_type"] == "connected":
                continue
            dest_id = route["next_hop"]
            pair = tuple(sorted([src_id, dest_id]))
            if pair in checked_pairs:
                continue
            checked_pairs.add(pair)

            # Find return path cost
            dest_routes = routing_tables.get(dest_id, [])
            return_cost = _find_route_cost(dest_routes, src_id, topology)

            if return_cost is not None and route["metric"] > 0:
                forward_cost = route["metric"]
                diff = abs(forward_cost - return_cost)
                if diff > asymmetry_threshold:
                    issues.append({
                        "type": "asymmetric_route",
                        "router_a": src_id,
                        "router_b": dest_id,
                        "forward_cost": forward_cost,
                        "return_cost": return_cost,
                        "difference": diff,
                    })

    return issues


def detect_black_holes(topology: dict, routing_tables: dict) -> list:
    """Detect routing black holes - destinations that are unreachable from some routers.

    A black hole exists when a router has no route (connected or learned)
    to a network that other routers can reach.
    """
    issues = []
    # Collect all known networks
    all_networks = set()
    for rid, routes in routing_tables.items():
        for route in routes:
            all_networks.add((route["destination"], route["prefix_length"]))

    # Check each router for missing routes
    for router in topology["routers"]:
        rid = router["id"]
        router_routes = routing_tables.get(rid, [])
        reachable = set()
        for route in router_routes:
            reachable.add((route["destination"], route["prefix_length"]))

        missing = all_networks - reachable
        for network, prefix in missing:
            # Verify it's reachable from at least one other router
            reachable_from_others = False
            for other_id, other_routes in routing_tables.items():
                if other_id == rid:
                    continue
                for r in other_routes:
                    if r["destination"] == network and r["prefix_length"] == prefix:
                        reachable_from_others = True
                        break
                if reachable_from_others:
                    break

            if reachable_from_others:
                issues.append({
                    "type": "black_hole",
                    "router": rid,
                    "unreachable_network": f"{network}/{prefix}",
                })

    return issues


def detect_mtu_mismatches(topology: dict, routing_tables: dict) -> list:
    """Detect MTU mismatches along routing paths.

    A mismatch exists when two connected interfaces on a link have
    different MTU values, potentially causing fragmentation or drops.
    """
    issues = []
    checked_links = set()

    for link in topology["links"]:
        if link["id"] in checked_links:
            continue
        checked_links.add(link["id"])

        if len(link["endpoints"]) != 2:
            continue

        ep_a = link["endpoints"][0]
        ep_b = link["endpoints"][1]

        router_a = get_router_by_id(topology, ep_a["router_id"])
        router_b = get_router_by_id(topology, ep_b["router_id"])

        if router_a is None or router_b is None:
            continue

        iface_a = _get_interface(router_a, ep_a["interface"])
        iface_b = _get_interface(router_b, ep_b["interface"])

        if iface_a is None or iface_b is None:
            continue

        if iface_a["mtu"] != iface_b["mtu"]:
            issues.append({
                "type": "mtu_mismatch",
                "link": link["id"],
                "router_a": ep_a["router_id"],
                "interface_a": ep_a["interface"],
                "mtu_a": iface_a["mtu"],
                "router_b": ep_b["router_id"],
                "interface_b": ep_b["interface"],
                "mtu_b": iface_b["mtu"],
                "difference": abs(iface_a["mtu"] - iface_b["mtu"]),
            })

    return issues


def _find_route_cost(routes: list, target_router: str, topology: dict) -> int | None:
    """Find the cost to reach a target router from a route table."""
    for route in routes:
        if route["next_hop"] == target_router:
            return route["metric"]
    return None


def _get_interface(router: dict, iface_name: str) -> dict | None:
    """Get interface from router by name."""
    for iface in router["interfaces"]:
        if iface["name"] == iface_name:
            return iface
    return None
