"""
Route computer. Implements link-state routing (OSPF-like) using Dijkstra's
algorithm to compute shortest-path routing tables from topology and link costs.
"""

import heapq
from topology_loader import compute_network_address, prefix_from_mask


def compute_routing_tables(topology: dict, ospf_costs: dict) -> dict:
    """Compute routing tables for all routers using OSPF costs.

    Args:
        topology: The network topology.
        ospf_costs: Dict mapping link_id -> cost as computed by the pipeline.

    Returns:
        Dict mapping router_id -> list of route entries.
    """
    routing_tables = {}
    adjacency = _build_adjacency(topology, ospf_costs)

    for router in topology["routers"]:
        rid = router["id"]
        routes = _dijkstra_routes(rid, adjacency, topology)
        # Add directly connected routes
        connected = _get_connected_routes(router)
        all_routes = connected + routes
        # Perform longest-prefix match deduplication with AD tie-breaking
        routing_tables[rid] = _deduplicate_routes(all_routes)

    return routing_tables


def compute_ospf_cost(reference_bandwidth: int, bandwidth: int) -> int:
    """Compute OSPF cost using reference bandwidth divided by link bandwidth.

    Per RFC 2328, the cost is reference_bandwidth / link_bandwidth using
    integer division with a minimum cost of 1.
    """
    cost = reference_bandwidth // bandwidth
    return max(cost, 1)


def _build_adjacency(topology: dict, ospf_costs: dict) -> dict:
    """Build adjacency list from topology links with costs."""
    adj = {}
    for router in topology["routers"]:
        adj[router["id"]] = []

    for link in topology["links"]:
        if len(link["endpoints"]) != 2:
            continue
        ep_a = link["endpoints"][0]
        ep_b = link["endpoints"][1]
        cost = ospf_costs.get(link["id"], 1)

        adj.setdefault(ep_a["router_id"], []).append({
            "neighbor": ep_b["router_id"],
            "cost": cost,
            "link_id": link["id"],
            "interface": ep_a["interface"],
        })
        adj.setdefault(ep_b["router_id"], []).append({
            "neighbor": ep_a["router_id"],
            "cost": cost,
            "link_id": link["id"],
            "interface": ep_b["interface"],
        })

    return adj


def _dijkstra_routes(source: str, adjacency: dict, topology: dict) -> list:
    """Run Dijkstra from source to compute shortest paths to all destinations."""
    dist = {source: 0}
    prev = {source: None}
    next_hop_iface = {source: None}
    pq = [(0, source)]
    visited = set()

    while pq:
        d, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)

        for neighbor_info in adjacency.get(node, []):
            neighbor = neighbor_info["neighbor"]
            new_dist = d + neighbor_info["cost"]

            if neighbor not in dist or new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                prev[neighbor] = node
                # Track next-hop interface from source
                if node == source:
                    next_hop_iface[neighbor] = neighbor_info["interface"]
                else:
                    next_hop_iface[neighbor] = next_hop_iface.get(node)
                heapq.heappush(pq, (new_dist, neighbor))

    # Build route entries for all reachable destinations
    routes = []
    for router in topology["routers"]:
        rid = router["id"]
        if rid == source or rid not in dist:
            continue
        # Add routes for all networks behind this router
        for iface in router["interfaces"]:
            if iface["status"] == "down":
                continue
            prefix = prefix_from_mask(iface["subnet_mask"])
            network = compute_network_address(iface["ip_address"], prefix)
            routes.append({
                "destination": network,
                "prefix_length": prefix,
                "next_hop": rid,
                "interface": next_hop_iface.get(rid, "unknown"),
                "metric": dist[rid],
                "route_type": "ospf",
                "administrative_distance": 110,
            })

    return routes


def _get_connected_routes(router: dict) -> list:
    """Get directly connected routes for a router."""
    routes = []
    for iface in router["interfaces"]:
        if iface["status"] == "down":
            continue
        prefix = prefix_from_mask(iface["subnet_mask"])
        network = compute_network_address(iface["ip_address"], prefix)
        routes.append({
            "destination": network,
            "prefix_length": prefix,
            "next_hop": "directly_connected",
            "interface": iface["name"],
            "metric": 0,
            "route_type": "connected",
            "administrative_distance": 0,
        })
    return routes


def _deduplicate_routes(routes: list) -> list:
    """Deduplicate routes using longest-prefix match, breaking ties by lower
    administrative distance (lower AD = more trusted route source)."""
    best = {}
    for route in routes:
        key = (route["destination"], route["prefix_length"])
        if key not in best:
            best[key] = route
        else:
            existing = best[key]
            # Longest prefix wins (higher prefix_length = more specific)
            if route["prefix_length"] > existing["prefix_length"]:
                best[key] = route
            elif route["prefix_length"] == existing["prefix_length"]:
                # Tie-break: lower administrative distance wins
                if route["administrative_distance"] < existing["administrative_distance"]:
                    best[key] = route
                elif route["administrative_distance"] == existing["administrative_distance"]:
                    # Same AD: lower metric wins
                    if route["metric"] < existing["metric"]:
                        best[key] = route

    return sorted(best.values(), key=lambda r: (r["destination"], -r["prefix_length"]))
