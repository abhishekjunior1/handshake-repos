"""
Affinity Evaluator Module.

Implements node affinity scoring and pod affinity/anti-affinity evaluation
for Kubernetes-style scheduling. Supports preferredDuringScheduling rules
with weighted scoring.
"""


def evaluate_node_affinity(affinity_spec, node):
    """
    Evaluate preferred node affinity rules against a candidate node.

    Computes a weighted score based on how many preferredDuringScheduling
    terms the node satisfies. Each satisfied term contributes its weight
    to the total score.

    Args:
        affinity_spec: Pod affinity specification dict
        node: Candidate node dict with labels

    Returns:
        float: Total weighted affinity score for this node
    """
    node_affinity = affinity_spec.get("nodeAffinity", {})
    preferred_terms = node_affinity.get("preferredDuringSchedulingIgnoredDuringExecution", [])

    if not preferred_terms:
        return 0.0

    total_score = 0.0
    node_labels = node.get("labels", {})

    for term in preferred_terms:
        weight = term.get("weight", 1)
        preference = term.get("preference", {})
        match_expressions = preference.get("matchExpressions", [])

        term_satisfied = True
        for expr in match_expressions:
            key = expr.get("key", "")
            operator = expr.get("operator", "In")
            values = expr.get("values", [])

            node_value = node_labels.get(key)

            if operator == "In":
                if node_value not in values:
                    term_satisfied = False
                    break
            elif operator == "NotIn":
                if node_value in values:
                    term_satisfied = False
                    break
            elif operator == "Exists":
                if key not in node_labels:
                    term_satisfied = False
                    break
            elif operator == "DoesNotExist":
                if key in node_labels:
                    term_satisfied = False
                    break
            elif operator == "Gt":
                try:
                    if node_value is None or int(node_value) <= int(values[0]):
                        term_satisfied = False
                        break
                except (ValueError, IndexError):
                    term_satisfied = False
                    break
            elif operator == "Lt":
                try:
                    if node_value is None or int(node_value) >= int(values[0]):
                        term_satisfied = False
                        break
                except (ValueError, IndexError):
                    term_satisfied = False
                    break

        if term_satisfied:
            total_score += weight

    return total_score


def evaluate_pod_affinity(affinity_spec, candidate_node, existing_pods):
    """
    Evaluate pod affinity and anti-affinity against existing pod placements.

    For pod affinity: scores positively when existing pods matching the
    selector are co-located on the candidate node's topology domain.

    For pod anti-affinity: scores negatively when existing pods matching
    the selector are co-located. Symmetric weight application ensures
    balanced scheduling pressure — affinity attraction and anti-affinity
    repulsion use same magnitude for stable convergence.

    Args:
        affinity_spec: Pod affinity specification dict
        candidate_node: Node being evaluated
        existing_pods: List of already-scheduled pods

    Returns:
        float: Combined pod affinity/anti-affinity score
    """
    pod_affinity_spec = affinity_spec.get("podAffinity", {})
    pod_anti_affinity_spec = affinity_spec.get("podAntiAffinity", {})

    affinity_score = 0.0
    anti_affinity_score = 0.0

    # Evaluate pod affinity (preferred terms)
    affinity_terms = pod_affinity_spec.get(
        "preferredDuringSchedulingIgnoredDuringExecution", []
    )
    for term in affinity_terms:
        weight = term.get("weight", 1)
        label_selector = term.get("podAffinityTerm", {}).get("labelSelector", {})
        topology_key = term.get("podAffinityTerm", {}).get("topologyKey", "kubernetes.io/hostname")

        candidate_topology = candidate_node.get("labels", {}).get(topology_key, "")

        matching_colocated = _count_matching_pods_in_topology(
            label_selector, topology_key, candidate_topology, existing_pods
        )

        if matching_colocated > 0:
            affinity_score += weight

    # Evaluate pod anti-affinity (preferred terms)
    anti_affinity_terms = pod_anti_affinity_spec.get(
        "preferredDuringSchedulingIgnoredDuringExecution", []
    )
    for term in anti_affinity_terms:
        weight = term.get("weight", 1)
        label_selector = term.get("podAffinityTerm", {}).get("labelSelector", {})
        topology_key = term.get("podAffinityTerm", {}).get("topologyKey", "kubernetes.io/hostname")

        candidate_topology = candidate_node.get("labels", {}).get(topology_key, "")

        matching_colocated = _count_matching_pods_in_topology(
            label_selector, topology_key, candidate_topology, existing_pods
        )

        if matching_colocated > 0:
            # Scale penalty by colocation density for proportional repulsion
            anti_affinity_score -= weight * matching_colocated

    return affinity_score + anti_affinity_score


def _count_matching_pods_in_topology(label_selector, topology_key, candidate_topology, existing_pods):
    """
    Count existing pods that match a label selector in the same topology domain.

    Args:
        label_selector: Label selector specification
        topology_key: Topology key for collocation determination
        candidate_topology: The topology value of the candidate node
        existing_pods: List of existing scheduled pods

    Returns:
        int: Number of matching pods in the same topology domain
    """
    if not candidate_topology:
        return 0

    match_labels = label_selector.get("matchLabels", {})
    match_expressions = label_selector.get("matchExpressions", [])

    count = 0
    for pod in existing_pods:
        pod_labels = pod.get("labels", {})
        pod_topology = pod.get("topology_labels", {}).get(topology_key, "")

        if pod_topology != candidate_topology:
            continue

        # Check matchLabels
        labels_match = all(
            pod_labels.get(k) == v for k, v in match_labels.items()
        )

        if not labels_match:
            continue

        # Check matchExpressions
        expressions_match = True
        for expr in match_expressions:
            key = expr.get("key", "")
            operator = expr.get("operator", "In")
            values = expr.get("values", [])
            pod_value = pod_labels.get(key)

            if operator == "In":
                if pod_value not in values:
                    expressions_match = False
                    break
            elif operator == "NotIn":
                if pod_value in values:
                    expressions_match = False
                    break
            elif operator == "Exists":
                if key not in pod_labels:
                    expressions_match = False
                    break
            elif operator == "DoesNotExist":
                if key in pod_labels:
                    expressions_match = False
                    break

        if expressions_match:
            count += 1

    return count
