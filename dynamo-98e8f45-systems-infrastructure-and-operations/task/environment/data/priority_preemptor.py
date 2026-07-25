"""
Priority-Based Preemption Module.

Implements Kubernetes-style priority preemption for pod scheduling.
When a high-priority pod cannot be scheduled, lower-priority pods
may be evicted to make room. Selects victims minimizing disruption
while freeing sufficient resources.
"""

from resource_calculator import compute_pod_resource_totals, get_allocatable_resources


def evaluate_preemption_candidates(pod, nodes, existing_pods, priority_classes):
    """
    Evaluate preemption candidates for an unschedulable pod.

    Finds nodes where evicting lower-priority pods would free enough
    resources for the incoming pod. Minimizes the number of victims
    and prefers evicting lowest-priority pods first.

    Args:
        pod: The pending pod that needs scheduling
        nodes: All cluster nodes
        existing_pods: Currently scheduled pods
        priority_classes: Priority class definitions

    Returns:
        Dict with 'success' bool, 'target_node', 'victims' list, and 'reason'
    """
    pod_priority = _get_pod_priority(pod, priority_classes)
    pod_resources = compute_pod_resource_totals(pod)
    pod_requests = pod_resources["requests"]

    best_candidate = None
    best_victims = []
    min_victims_count = float('inf')

    for node in nodes:
        allocatable = get_allocatable_resources(node)
        node_pods = [p for p in existing_pods if p.get("node_name") == node["name"]]

        # Find lower-priority pods that could be evicted
        evictable = []
        for existing in node_pods:
            existing_priority = _get_pod_priority(existing, priority_classes)
            if existing_priority < pod_priority:
                evictable.append({
                    "pod": existing,
                    "priority": existing_priority,
                    "resources": compute_pod_resource_totals(existing)
                })

        if not evictable:
            continue

        # Sort by priority ascending (evict lowest priority first)
        evictable.sort(key=lambda x: x["priority"])

        # Calculate current used resources on this node
        used_cpu = sum(
            compute_pod_resource_totals(p)["requests"]["cpu_millicores"]
            for p in node_pods
        )
        used_memory = sum(
            compute_pod_resource_totals(p)["requests"]["memory_mb"]
            for p in node_pods
        )

        available_cpu = allocatable["cpu_millicores"] - used_cpu
        available_memory = allocatable["memory_mb"] - used_memory

        # Greedily evict until enough resources are freed
        victims = []
        freed_cpu = available_cpu
        freed_memory = available_memory

        for candidate in evictable:
            if freed_cpu >= pod_requests["cpu_millicores"] and \
               freed_memory >= pod_requests["memory_mb"]:
                break

            victim_requests = candidate["resources"]["requests"]
            freed_cpu += victim_requests["cpu_millicores"]
            freed_memory += victim_requests["memory_mb"]
            victims.append(candidate["pod"]["name"])

        # Check if enough resources were freed
        if freed_cpu >= pod_requests["cpu_millicores"] and \
           freed_memory >= pod_requests["memory_mb"]:
            if len(victims) < min_victims_count:
                min_victims_count = len(victims)
                best_candidate = node["name"]
                best_victims = victims

    if best_candidate:
        return {
            "success": True,
            "target_node": best_candidate,
            "victims": best_victims,
            "freed_resources": {
                "cpu_millicores": freed_cpu,
                "memory_mb": freed_memory
            }
        }
    else:
        return {
            "success": False,
            "target_node": None,
            "victims": [],
            "reason": "no_lower_priority_pods_to_evict"
        }


def _get_pod_priority(pod, priority_classes):
    """
    Get the priority value for a pod.

    Looks up the priority class name in the priority_classes mapping.
    Defaults to 0 if no priority class is specified.
    """
    priority_class_name = pod.get("priority_class", "")
    if priority_class_name and priority_class_name in priority_classes:
        return priority_classes[priority_class_name].get("value", 0)
    return pod.get("priority", 0)


def compute_disruption_score(victims, priority_classes):
    """
    Compute a disruption score for a set of preemption victims.

    Higher scores indicate more disruptive preemption decisions.
    Considers number of victims, their priorities, and resource usage.
    """
    if not victims:
        return 0.0

    score = 0.0
    for victim in victims:
        priority = _get_pod_priority(victim, priority_classes)
        resources = compute_pod_resource_totals(victim)
        resource_weight = (resources["requests"]["cpu_millicores"] +
                          resources["requests"]["memory_mb"]) / 1000.0
        score += (priority + 1) * resource_weight

    return round(score, 4)
