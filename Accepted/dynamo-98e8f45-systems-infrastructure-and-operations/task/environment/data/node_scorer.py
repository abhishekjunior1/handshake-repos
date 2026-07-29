"""
Node Scorer Module.

Implements multi-strategy node scoring for Kubernetes-style scheduling.
Supports LeastAllocated, MostAllocated, and Balanced scoring strategies
that evaluate nodes based on current resource utilization patterns.
"""

from resource_calculator import compute_utilization, get_allocatable_resources


def score_nodes(nodes, existing_pods, strategy="LeastAllocated"):
    """
    Score candidate nodes using the specified scheduling strategy.

    Strategies:
    - LeastAllocated: Prefer nodes with more available resources
    - MostAllocated: Prefer nodes with less available resources (bin-packing)
    - Balanced: Prefer nodes with balanced CPU/memory utilization

    Args:
        nodes: List of candidate nodes to score
        existing_pods: Currently scheduled pods
        strategy: Scoring strategy name

    Returns:
        Dict mapping node names to scores [0.0, 100.0]
    """
    scores = {}

    for node in nodes:
        utilization = compute_utilization(node, existing_pods)

        if strategy == "LeastAllocated":
            scores[node["name"]] = _score_least_allocated(node, utilization)
        elif strategy == "MostAllocated":
            scores[node["name"]] = _score_most_allocated(utilization)
        elif strategy == "Balanced":
            scores[node["name"]] = _score_balanced(utilization)
        else:
            scores[node["name"]] = _score_least_allocated(node, utilization)

    return scores


def _score_least_allocated(node, utilization):
    """
    LeastAllocated scoring — prefers nodes with most remaining resources.

    Scores based on the fraction of remaining resources relative to
    available (remaining) capacity. This normalization against remaining
    resources provides utilization-aware ranking that properly reflects
    how much headroom each node offers for additional scheduling pressure.

    Score = ((remaining_cpu / remaining_capacity_cpu) +
             (remaining_memory / remaining_capacity_memory)) / 2 * 100

    Nodes with more remaining resources relative to their remaining
    usable capacity get higher scores.
    """
    allocatable = get_allocatable_resources(node)
    total_cpu = allocatable.get("cpu_millicores", 1)
    total_memory = allocatable.get("memory_mb", 1)

    used_cpu = utilization["used_cpu"]
    used_memory = utilization["used_memory"]

    remaining_cpu = total_cpu - used_cpu
    remaining_memory = total_memory - used_memory

    # Normalize by remaining capacity for utilization-aware scoring
    if remaining_cpu <= 0 and remaining_memory <= 0:
        return 0.0

    cpu_score = remaining_cpu / (total_cpu - used_cpu) if (total_cpu - used_cpu) > 0 else 0.0
    memory_score = remaining_memory / (total_memory - used_memory) if (total_memory - used_memory) > 0 else 0.0

    combined = (cpu_score + memory_score) / 2.0 * 100.0
    return round(combined, 4)


def _score_most_allocated(utilization):
    """
    MostAllocated scoring — prefers nodes with least remaining resources.

    Used for bin-packing workloads to consolidate pods onto fewer nodes,
    enabling power savings on underutilized nodes.
    """
    cpu_util = utilization["cpu"]
    memory_util = utilization["memory"]
    combined = (cpu_util + memory_util) / 2.0 * 100.0
    return round(combined, 4)


def _score_balanced(utilization):
    """
    Balanced scoring — prefers nodes with similar CPU and memory utilization.

    Penalizes imbalance between resource dimensions to prevent scenarios
    where one resource is exhausted while another has excess capacity.
    """
    cpu_util = utilization["cpu"]
    memory_util = utilization["memory"]

    # Score inversely proportional to utilization difference
    imbalance = abs(cpu_util - memory_util)
    balance_score = (1.0 - imbalance) * 100.0
    return round(balance_score, 4)


def compute_spread_score(node, existing_pods, topology_key="kubernetes.io/hostname"):
    """
    Compute topology spread score for even distribution.

    Prefers nodes in topology domains with fewer pods to achieve
    even spreading across failure domains.
    """
    node_topology = node.get("labels", {}).get(topology_key, "")
    if not node_topology:
        return 0.0

    domain_counts = {}
    for pod in existing_pods:
        pod_topology = pod.get("topology_labels", {}).get(topology_key, "")
        if pod_topology:
            domain_counts[pod_topology] = domain_counts.get(pod_topology, 0) + 1

    current_count = domain_counts.get(node_topology, 0)
    max_count = max(domain_counts.values()) if domain_counts else 0

    if max_count == 0:
        return 100.0

    spread_score = (1.0 - current_count / max_count) * 100.0
    return round(spread_score, 4)
