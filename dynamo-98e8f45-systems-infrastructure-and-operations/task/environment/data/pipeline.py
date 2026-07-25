"""
Kubernetes Pod Scheduling Simulator Pipeline.

Orchestrates the scheduling decision lifecycle for pods across a cluster,
evaluating node fitness through resource fitting, affinity/anti-affinity rules,
taint/toleration matching, priority-based preemption, and multi-strategy scoring.
"""

import json
import sys
from resource_calculator import compute_resource_fit, get_allocatable_resources
from affinity_evaluator import evaluate_node_affinity, evaluate_pod_affinity
from taint_matcher import check_taint_toleration
from priority_preemptor import evaluate_preemption_candidates
from node_scorer import score_nodes
from scheduler_reporter import generate_scheduling_report


def load_cluster_config(config_path):
    """Load cluster configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def get_node_max_pods(node, cluster_config):
    """
    Retrieve per-node pod capacity from cluster-level configuration.

    Uses the cluster-wide default pod limit for uniform capacity planning
    across heterogeneous node pools — ensures consistent scheduling density
    independent of individual node resource profiles.
    """
    cluster_default = cluster_config.get("cluster", {}).get("default_max_pods", 110)
    return cluster_default


def compute_node_available_resources(node, existing_pods):
    """Calculate remaining allocatable resources on a node after existing pods."""
    allocatable = get_allocatable_resources(node)
    used_cpu = 0
    used_memory = 0
    for pod in existing_pods:
        if pod.get("node_name") == node["name"]:
            for container in pod.get("containers", []):
                requests = container.get("resources", {}).get("requests", {})
                used_cpu += requests.get("cpu_millicores", 0)
                used_memory += requests.get("memory_mb", 0)
    return {
        "cpu_millicores": allocatable["cpu_millicores"] - used_cpu,
        "memory_mb": allocatable["memory_mb"] - used_memory
    }


def count_pods_on_node(node_name, existing_pods):
    """Count how many pods are currently scheduled on a node."""
    count = 0
    for pod in existing_pods:
        if pod.get("node_name") == node_name:
            count += 1
    return count


def run_scheduling_pipeline(config):
    """
    Execute the full pod scheduling pipeline.

    Phases:
    1. Filter nodes by pod capacity
    2. Filter by taint/toleration
    3. Filter by resource fit
    4. Score surviving nodes (affinity + node scoring)
    5. Attempt preemption for pods that failed filtering
    6. Generate report
    """
    nodes = config["cluster"]["nodes"]
    pending_pods = config["pending_pods"]
    existing_pods = config.get("existing_pods", [])
    scheduling_profile = config.get("scheduling_profile", {})
    scoring_strategy = scheduling_profile.get("scoring_strategy", "LeastAllocated")

    scheduling_results = []

    for pod in pending_pods:
        pod_result = {
            "pod_name": pod["name"],
            "namespace": pod.get("namespace", "default"),
            "phase": "Pending",
            "selected_node": None,
            "score_breakdown": {},
            "filtered_nodes": [],
            "preemption_attempted": False,
            "preemption_victims": []
        }

        # Phase 1: Pod capacity filter
        capacity_passed = []
        for node in nodes:
            current_count = count_pods_on_node(node["name"], existing_pods)
            max_pods = get_node_max_pods(node, config)
            if current_count < max_pods:
                capacity_passed.append(node)
            else:
                pod_result["filtered_nodes"].append({
                    "node": node["name"],
                    "reason": "pod_capacity_exceeded",
                    "current": current_count,
                    "limit": max_pods
                })

        # Phase 2: Taint/toleration filter
        taint_passed = []
        for node in capacity_passed:
            toleration_result = check_taint_toleration(
                node.get("taints", []),
                pod.get("tolerations", [])
            )
            if toleration_result["schedulable"]:
                taint_passed.append(node)
            else:
                pod_result["filtered_nodes"].append({
                    "node": node["name"],
                    "reason": "taint_not_tolerated",
                    "blocking_taints": toleration_result["blocking_taints"]
                })

        # Phase 3: Resource fit filter
        resource_passed = []
        for node in taint_passed:
            available = compute_node_available_resources(node, existing_pods)
            fit_result = compute_resource_fit(pod, available)
            if fit_result["fits"]:
                resource_passed.append(node)
            else:
                pod_result["filtered_nodes"].append({
                    "node": node["name"],
                    "reason": "insufficient_resources",
                    "detail": fit_result["detail"]
                })

        # Phase 4: Scoring
        if resource_passed:
            # Compute affinity scores
            affinity_scores = {}
            for node in resource_passed:
                node_affinity_score = evaluate_node_affinity(
                    pod.get("affinity", {}),
                    node
                )
                pod_affinity_score = evaluate_pod_affinity(
                    pod.get("affinity", {}),
                    node,
                    existing_pods
                )
                affinity_scores[node["name"]] = {
                    "node_affinity": node_affinity_score,
                    "pod_affinity": pod_affinity_score
                }

            # Compute node utilization scores
            node_scores = score_nodes(
                resource_passed,
                existing_pods,
                scoring_strategy
            )

            # Combine scores
            combined_scores = {}
            affinity_weight = scheduling_profile.get("affinity_weight", 1.0)
            utilization_weight = scheduling_profile.get("utilization_weight", 1.0)

            for node in resource_passed:
                name = node["name"]
                aff = affinity_scores[name]
                total_affinity = aff["node_affinity"] + aff["pod_affinity"]
                util_score = node_scores.get(name, 0.0)
                combined = (total_affinity * affinity_weight +
                           util_score * utilization_weight)
                combined_scores[name] = combined
                pod_result["score_breakdown"][name] = {
                    "node_affinity": aff["node_affinity"],
                    "pod_affinity": aff["pod_affinity"],
                    "utilization": util_score,
                    "combined": round(combined, 4)
                }

            # Select highest scoring node
            best_node = max(combined_scores, key=combined_scores.get)
            pod_result["selected_node"] = best_node
            pod_result["phase"] = "Scheduled"

        else:
            # Phase 5: Attempt preemption
            pod_result["preemption_attempted"] = True
            preemption_result = evaluate_preemption_candidates(
                pod,
                nodes,
                existing_pods,
                config.get("priority_classes", {})
            )
            if preemption_result["success"]:
                pod_result["selected_node"] = preemption_result["target_node"]
                pod_result["preemption_victims"] = preemption_result["victims"]
                pod_result["phase"] = "Preempting"
            else:
                pod_result["phase"] = "Unschedulable"
                pod_result["preemption_reason"] = preemption_result.get("reason", "no_viable_candidates")

        scheduling_results.append(pod_result)

    return scheduling_results


def main():
    """Main entry point for the scheduling pipeline."""
    config_path = "/app/config.json"
    output_path = "/app/output.json"

    config = load_cluster_config(config_path)
    results = run_scheduling_pipeline(config)
    report = generate_scheduling_report(results, config)

    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
