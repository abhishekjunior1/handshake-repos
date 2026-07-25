"""
ACL evaluator. Evaluates firewall and access control list rules against
traffic flows to determine permit/deny decisions for each flow.
"""

from topology_loader import compute_network_address, prefix_from_mask


def evaluate_acl_rules(topology: dict, acl_rules: list, flows: list,
                       routing_tables: dict) -> dict:
    """Evaluate ACL rules against a set of traffic flows.

    Args:
        topology: Network topology.
        acl_rules: List of ACL rule definitions.
        flows: List of traffic flows to evaluate.
        routing_tables: Pre-computed routing tables.

    Returns:
        Dict with flow evaluation results.
    """
    results = {
        "flow_decisions": [],
        "rules_matched": 0,
        "flows_permitted": 0,
        "flows_denied": 0,
    }

    for flow in flows:
        decision = _evaluate_single_flow(flow, acl_rules, topology, routing_tables)
        results["flow_decisions"].append(decision)
        if decision["action"] == "permit":
            results["flows_permitted"] += 1
        else:
            results["flows_denied"] += 1
        if decision["matched_rule"] is not None:
            results["rules_matched"] += 1

    return results


def _evaluate_single_flow(flow: dict, acl_rules: list, topology: dict,
                          routing_tables: dict) -> dict:
    """Evaluate a single flow against the ACL rule set."""
    source_ip = flow["source_ip"]
    dest_ip = flow["destination_ip"]
    protocol = flow.get("protocol", "any")
    dest_port = flow.get("destination_port", None)

    decision = {
        "flow_id": flow.get("id", "unknown"),
        "source_ip": source_ip,
        "destination_ip": dest_ip,
        "action": "deny",  # default deny
        "matched_rule": None,
        "evaluation_path": [],
    }

    # Evaluate rules in order (first match wins)
    for rule in acl_rules:
        match_result = _match_rule(rule, source_ip, dest_ip, protocol, dest_port)
        if match_result["matched"]:
            decision["action"] = rule["action"]
            decision["matched_rule"] = rule["id"]
            decision["evaluation_path"].append({
                "rule_id": rule["id"],
                "matched": True,
                "reason": match_result["reason"],
            })
            break
        else:
            decision["evaluation_path"].append({
                "rule_id": rule["id"],
                "matched": False,
                "reason": match_result["reason"],
            })

    return decision


def _match_rule(rule: dict, source_ip: str, dest_ip: str,
                protocol: str, dest_port: int | None) -> dict:
    """Check if a flow matches an ACL rule.

    Matching logic:
    - Source: match source IP against rule's source network/prefix
    - Destination: match destination IP against rule's destination network/prefix
    - Protocol: match if rule specifies 'any' or matches flow protocol
    - Port: match if rule specifies no port or matches flow destination port
    """
    # Check protocol
    rule_protocol = rule.get("protocol", "any")
    if rule_protocol != "any" and rule_protocol != protocol:
        return {"matched": False, "reason": f"protocol mismatch: rule={rule_protocol}, flow={protocol}"}

    # Check source
    rule_source = rule.get("source", "any")
    if rule_source != "any":
        if not _ip_matches_network(source_ip, rule_source["network"], rule_source["prefix_length"]):
            return {"matched": False, "reason": "source IP not in rule source network"}

    # Check destination against rule's destination network
    rule_dest = rule.get("destination", "any")
    if rule_dest != "any":
        if not _ip_matches_network(dest_ip, rule_dest["network"], rule_dest["prefix_length"]):
            return {"matched": False, "reason": "destination IP not in rule destination network"}

    # Check port
    rule_port = rule.get("destination_port", None)
    if rule_port is not None and dest_port is not None:
        if isinstance(rule_port, dict):
            # Port range
            if not (rule_port["start"] <= dest_port <= rule_port["end"]):
                return {"matched": False, "reason": f"port {dest_port} not in range {rule_port['start']}-{rule_port['end']}"}
        elif rule_port != dest_port:
            return {"matched": False, "reason": f"port mismatch: rule={rule_port}, flow={dest_port}"}

    return {"matched": True, "reason": "all criteria matched"}


def _ip_matches_network(ip: str, network: str, prefix_length: int) -> bool:
    """Check if an IP address falls within a network/prefix."""
    ip_int = _ip_to_int(ip)
    net_int = _ip_to_int(network)
    mask = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
    return (ip_int & mask) == (net_int & mask)


def _ip_to_int(ip: str) -> int:
    """Convert dotted-quad IP to integer."""
    octets = [int(o) for o in ip.split(".")]
    return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]


def get_acl_summary(acl_results: dict) -> dict:
    """Generate a summary of ACL evaluation results."""
    total_flows = len(acl_results["flow_decisions"])
    return {
        "total_flows_evaluated": total_flows,
        "permitted": acl_results["flows_permitted"],
        "denied": acl_results["flows_denied"],
        "permit_rate": acl_results["flows_permitted"] / total_flows if total_flows > 0 else 0.0,
        "rules_hit": acl_results["rules_matched"],
    }
