"""
Scheduler Reporter Module.

Generates structured scheduling decision reports from pipeline results.
Produces deterministic JSON output suitable for verification against
expected scheduling outcomes.
"""


def generate_scheduling_report(scheduling_results, config):
    """
    Generate a comprehensive scheduling report from pipeline results.

    Produces a structured report including per-pod scheduling decisions,
    cluster utilization summary, and scheduling statistics.

    Args:
        scheduling_results: List of per-pod scheduling decision dicts
        config: Original cluster configuration

    Returns:
        Dict: Complete scheduling report
    """
    nodes = config["cluster"]["nodes"]
    total_nodes = len(nodes)

    # Scheduling statistics
    scheduled_count = sum(
        1 for r in scheduling_results if r["phase"] == "Scheduled"
    )
    preempting_count = sum(
        1 for r in scheduling_results if r["phase"] == "Preempting"
    )
    unschedulable_count = sum(
        1 for r in scheduling_results if r["phase"] == "Unschedulable"
    )
    total_pods = len(scheduling_results)

    # Per-node placement summary
    node_placements = {}
    for node in nodes:
        node_placements[node["name"]] = {
            "scheduled_pods": [],
            "preempted_pods": []
        }

    for result in scheduling_results:
        if result["selected_node"] and result["selected_node"] in node_placements:
            if result["phase"] == "Scheduled":
                node_placements[result["selected_node"]]["scheduled_pods"].append(
                    result["pod_name"]
                )
            elif result["phase"] == "Preempting":
                node_placements[result["selected_node"]]["preempted_pods"].append(
                    result["pod_name"]
                )

    # Build report
    report = {
        "scheduling_summary": {
            "total_pods": total_pods,
            "scheduled": scheduled_count,
            "preempting": preempting_count,
            "unschedulable": unschedulable_count,
            "scheduling_rate": round(
                (scheduled_count + preempting_count) / total_pods, 4
            ) if total_pods > 0 else 0.0
        },
        "pod_decisions": [],
        "node_placements": node_placements,
        "cluster_info": {
            "total_nodes": total_nodes,
            "scoring_strategy": config.get("scheduling_profile", {}).get(
                "scoring_strategy", "LeastAllocated"
            )
        }
    }

    # Pod decision details
    for result in scheduling_results:
        decision = {
            "pod_name": result["pod_name"],
            "namespace": result["namespace"],
            "phase": result["phase"],
            "selected_node": result["selected_node"],
            "score_breakdown": result.get("score_breakdown", {}),
            "filtered_nodes": result.get("filtered_nodes", []),
            "preemption_attempted": result.get("preemption_attempted", False),
            "preemption_victims": result.get("preemption_victims", [])
        }
        report["pod_decisions"].append(decision)

    return report
