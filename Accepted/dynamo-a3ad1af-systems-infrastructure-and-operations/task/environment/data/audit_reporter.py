"""
Audit reporter. Generates a comprehensive network configuration audit report
combining addressing validation, routing analysis, ACL evaluation, and
misconfiguration detection results.
"""

import json


def generate_audit_report(topology: dict, addressing: dict, routing_tables: dict,
                          acl_results: dict, misconfigs: dict,
                          ospf_costs: dict) -> dict:
    """Generate the full audit report.

    Args:
        topology: Network topology.
        addressing: Address validation results.
        routing_tables: Computed routing tables.
        acl_results: ACL evaluation results.
        misconfigs: Misconfiguration detection results.
        ospf_costs: OSPF cost computations.

    Returns:
        Complete audit report dict ready for JSON serialization.
    """
    report = {
        "summary": _build_summary(topology, addressing, routing_tables,
                                  acl_results, misconfigs),
        "addressing_validation": addressing,
        "routing_analysis": _build_routing_analysis(routing_tables, ospf_costs, topology),
        "acl_evaluation": acl_results,
        "misconfiguration_report": misconfigs,
        "topology_overview": _build_topology_overview(topology),
    }
    return report


def _build_summary(topology: dict, addressing: dict, routing_tables: dict,
                   acl_results: dict, misconfigs: dict) -> dict:
    """Build the executive summary section."""
    total_routes = sum(len(routes) for routes in routing_tables.values())
    total_routers = len(topology["routers"])
    total_links = len(topology["links"])

    severity = "healthy"
    if misconfigs["total_issues"] > 0:
        severity = "warning"
    if not addressing["is_valid"] or len(misconfigs["black_holes"]) > 0:
        severity = "critical"

    return {
        "overall_status": severity,
        "total_routers": total_routers,
        "total_links": total_links,
        "total_routes_computed": total_routes,
        "addressing_valid": addressing["is_valid"],
        "total_misconfigurations": misconfigs["total_issues"],
        "flows_evaluated": len(acl_results["flow_decisions"]),
        "flows_permitted": acl_results["flows_permitted"],
        "flows_denied": acl_results["flows_denied"],
    }


def _build_routing_analysis(routing_tables: dict, ospf_costs: dict,
                            topology: dict) -> dict:
    """Build the routing analysis section."""
    analysis = {
        "ospf_link_costs": ospf_costs,
        "routing_tables": {},
        "route_statistics": {},
    }

    for router_id, routes in routing_tables.items():
        analysis["routing_tables"][router_id] = routes
        connected = sum(1 for r in routes if r["route_type"] == "connected")
        learned = sum(1 for r in routes if r["route_type"] == "ospf")
        analysis["route_statistics"][router_id] = {
            "total_routes": len(routes),
            "connected_routes": connected,
            "learned_routes": learned,
            "avg_metric": _avg_metric(routes),
        }

    return analysis


def _build_topology_overview(topology: dict) -> dict:
    """Build topology overview section."""
    router_summary = []
    for router in topology["routers"]:
        active_ifaces = [i for i in router["interfaces"] if i["status"] != "down"]
        router_summary.append({
            "id": router["id"],
            "hostname": router["hostname"],
            "active_interfaces": len(active_ifaces),
            "ospf_area": router["ospf_area"],
        })

    return {
        "routers": router_summary,
        "total_links": len(topology["links"]),
        "total_subnets": len(topology["subnets"]),
        "reference_bandwidth": topology["reference_bandwidth"],
    }


def _avg_metric(routes: list) -> float:
    """Compute average metric for learned routes."""
    learned = [r for r in routes if r["route_type"] == "ospf"]
    if not learned:
        return 0.0
    return sum(r["metric"] for r in learned) / len(learned)


def write_report(report: dict, output_path: str) -> None:
    """Write the audit report to a JSON file."""
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)


def format_severity(misconfigs: dict) -> str:
    """Format severity level based on misconfiguration findings."""
    if misconfigs["total_issues"] == 0:
        return "PASS - No misconfigurations detected"
    black_holes = len(misconfigs["black_holes"])
    asymmetric = len(misconfigs["asymmetric_routes"])
    mtu = len(misconfigs["mtu_mismatches"])
    parts = []
    if black_holes > 0:
        parts.append(f"{black_holes} black hole(s)")
    if asymmetric > 0:
        parts.append(f"{asymmetric} asymmetric route(s)")
    if mtu > 0:
        parts.append(f"{mtu} MTU mismatch(es)")
    return f"WARN - {', '.join(parts)}"
