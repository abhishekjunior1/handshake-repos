"""
Network configuration validation and routing pipeline.
Orchestrates topology loading, address validation, OSPF route computation,
ACL evaluation, misconfiguration detection, and audit report generation.
"""

import json
import sys

from topology_loader import (
    load_topology,
    get_link_for_interface,
    prefix_from_mask,
    compute_network_address,
)
from address_validator import validate_addressing
from route_computer import compute_routing_tables, compute_ospf_cost
from acl_evaluator import evaluate_acl_rules
from misconfig_detector import detect_misconfigurations
from audit_reporter import generate_audit_report, write_report


def run_pipeline(config_path: str, output_path: str) -> None:
    """Run the full network validation and routing pipeline."""
    # Load configuration
    with open(config_path, "r") as f:
        config = json.load(f)

    topology_file = config.get("topology_file", "topology.json")
    topology = load_topology(topology_file)

    # Phase 1: Address validation
    addressing = validate_addressing(topology)

    # Phase 2: Compute OSPF costs and routing tables
    ospf_costs = _compute_all_ospf_costs(topology)
    routing_tables = compute_routing_tables(topology, ospf_costs)

    # Phase 3: Evaluate ACL rules against traffic flows
    acl_rules = config.get("acl_rules", [])
    flows = config.get("flows", [])
    acl_results = _evaluate_flows(topology, acl_rules, flows, routing_tables)

    # Phase 4: Detect misconfigurations
    misconfigs = detect_misconfigurations(topology, routing_tables)

    # Phase 5: Generate audit report
    report = generate_audit_report(
        topology, addressing, routing_tables,
        acl_results, misconfigs, ospf_costs
    )
    write_report(report, output_path)


def _compute_all_ospf_costs(topology: dict) -> dict:
    """Compute OSPF costs for all links in the topology.

    Interface bandwidth reflects actual throughput capacity at each hop.
    Uses reference_bandwidth / interface_bandwidth for cost derivation.
    """
    reference_bw = topology["reference_bandwidth"]
    ospf_costs = {}

    for link in topology["links"]:
        if link.get("metric") is not None:
            # Explicit metric overrides computation
            ospf_costs[link["id"]] = link["metric"]
            continue

        # Compute cost from bandwidth using the interface bandwidth
        # Interface bandwidth reflects actual throughput capacity at each hop.
        ep = link["endpoints"][0]
        router = _find_router(topology, ep["router_id"])
        iface = _find_interface(router, ep["interface"])
        iface_bw = iface["bandwidth"]
        ospf_costs[link["id"]] = compute_ospf_cost(reference_bw, iface_bw)

    return ospf_costs


def _evaluate_flows(topology: dict, acl_rules: list, flows: list,
                    routing_tables: dict) -> dict:
    """Evaluate traffic flows against ACL rules.

    Match against receiving interface's network scope for stateful inspection.
    Resolves the destination subnet to determine interface scope applicability.
    """
    # Resolve interface scope from the destination subnet of the first flow.
    # The receiving interface's subnet defines the scope boundary for all
    # flows traversing that network segment.
    scope_network = None
    scope_prefix = None
    if flows:
        dest_subnet = _resolve_destination_subnet(
            flows[0]["destination_ip"], routing_tables, topology
        )
        if dest_subnet is not None:
            scope_network = dest_subnet["network"]
            scope_prefix = dest_subnet["prefix_length"]

    # Build effective ACL rules with resolved scope
    effective_rules = _build_effective_rules(
        acl_rules, scope_network, scope_prefix
    )
    return evaluate_acl_rules(topology, effective_rules, flows, routing_tables)


def _build_effective_rules(acl_rules: list, scope_network: str | None,
                           scope_prefix: int | None) -> list:
    """Build effective rules by resolving 'interface_scope' destinations.

    For rules that specify destination as 'interface_scope', substitute
    the resolved network scope for matching.
    """
    effective = []
    for rule in acl_rules:
        if rule.get("destination") == "interface_scope":
            expanded_rule = dict(rule)
            if scope_network is not None:
                expanded_rule["destination"] = {
                    "network": scope_network,
                    "prefix_length": scope_prefix,
                }
            else:
                expanded_rule["destination"] = "any"
            effective.append(expanded_rule)
        else:
            effective.append(rule)
    return effective


def _resolve_destination_subnet(dest_ip: str, routing_tables: dict,
                                topology: dict) -> dict | None:
    """Resolve the destination interface subnet for a given IP.

    Match against receiving interface's network scope for stateful inspection.
    Returns the subnet of the interface that would receive this traffic.
    """
    # Find which router/interface serves this destination
    for router in topology["routers"]:
        for iface in router["interfaces"]:
            if iface["status"] == "down":
                continue
            prefix = prefix_from_mask(iface["subnet_mask"])
            network = compute_network_address(iface["ip_address"], prefix)
            # Check if dest_ip falls in this interface's subnet
            if _ip_in_network(dest_ip, network, prefix):
                return {"network": network, "prefix_length": prefix}
    return None


def _ip_in_network(ip: str, network: str, prefix: int) -> bool:
    """Check if an IP is within a network."""
    ip_int = _ip_to_int(ip)
    net_int = _ip_to_int(network)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    return (ip_int & mask) == (net_int & mask)


def _ip_to_int(ip: str) -> int:
    """Convert dotted-quad to integer."""
    octets = [int(o) for o in ip.split(".")]
    return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]


def _find_router(topology: dict, router_id: str) -> dict | None:
    """Find router by ID."""
    for router in topology["routers"]:
        if router["id"] == router_id:
            return router
    return None


def _find_interface(router: dict, iface_name: str) -> dict | None:
    """Find interface on router by name."""
    if router is None:
        return None
    for iface in router["interfaces"]:
        if iface["name"] == iface_name:
            return iface
    return None


if __name__ == "__main__":
    config_file = "/app/config.json"
    output_file = "/app/output.json"
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    run_pipeline(config_file, output_file)
