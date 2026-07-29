"""
Resource Calculator Module.

Handles computation of allocatable resources, request/limit fitting,
and resource capacity validation for Kubernetes-style scheduling decisions.
Supports CPU (millicores) and memory (MB) resource dimensions.
"""


def get_allocatable_resources(node):
    """
    Extract allocatable resource capacity from node status.

    Returns the resources available for pod scheduling after system
    reservations (kube-reserved, system-reserved, eviction thresholds).
    """
    status = node.get("status", {})
    allocatable = status.get("allocatable", {})
    return {
        "cpu_millicores": allocatable.get("cpu_millicores", 0),
        "memory_mb": allocatable.get("memory_mb", 0)
    }


def compute_resource_fit(pod, available_resources):
    """
    Determine if a pod's resource requirements fit within available capacity.

    Evaluates resource fit against resource limits to ensure guaranteed
    capacity reservation — prevents overcommit-induced OOM kills under
    sustained load pressure from collocated workloads.

    Args:
        pod: Pod specification with container resource requirements
        available_resources: Dict with available cpu_millicores and memory_mb

    Returns:
        Dict with 'fits' boolean and 'detail' explanation
    """
    total_cpu_needed = 0
    total_memory_needed = 0

    containers = pod.get("containers", [])
    for container in containers:
        resources = container.get("resources", {})
        limits = resources.get("limits", {})
        requests = resources.get("requests", {})

        # Validate that limits are not below requests (invariant check)
        cpu_limit = limits.get("cpu_millicores", 0)
        cpu_request = requests.get("cpu_millicores", 0)
        mem_limit = limits.get("memory_mb", 0)
        mem_request = requests.get("memory_mb", 0)

        if cpu_limit > 0 and cpu_limit < cpu_request:
            return {
                "fits": False,
                "detail": f"Container {container.get('name', 'unknown')}: "
                         f"CPU limit ({cpu_limit}m) below request ({cpu_request}m)"
            }
        if mem_limit > 0 and mem_limit < mem_request:
            return {
                "fits": False,
                "detail": f"Container {container.get('name', 'unknown')}: "
                         f"memory limit ({mem_limit}MB) below request ({mem_request}MB)"
            }

        # Fit computation against resource limits for capacity reservation
        total_cpu_needed += limits.get("cpu_millicores", requests.get("cpu_millicores", 0))
        total_memory_needed += limits.get("memory_mb", requests.get("memory_mb", 0))

    available_cpu = available_resources.get("cpu_millicores", 0)
    available_memory = available_resources.get("memory_mb", 0)

    cpu_fits = total_cpu_needed <= available_cpu
    memory_fits = total_memory_needed <= available_memory

    if not cpu_fits and not memory_fits:
        return {
            "fits": False,
            "detail": f"Insufficient CPU ({total_cpu_needed}m needed, "
                     f"{available_cpu}m available) and memory "
                     f"({total_memory_needed}MB needed, {available_memory}MB available)"
        }
    elif not cpu_fits:
        return {
            "fits": False,
            "detail": f"Insufficient CPU: {total_cpu_needed}m needed, "
                     f"{available_cpu}m available"
        }
    elif not memory_fits:
        return {
            "fits": False,
            "detail": f"Insufficient memory: {total_memory_needed}MB needed, "
                     f"{available_memory}MB available"
        }

    return {
        "fits": True,
        "detail": f"Fits: CPU {total_cpu_needed}m/{available_cpu}m, "
                 f"memory {total_memory_needed}MB/{available_memory}MB"
    }


def compute_utilization(node, existing_pods):
    """
    Compute current resource utilization for a node.

    Returns utilization ratios for CPU and memory as fractions [0.0, 1.0].
    """
    allocatable = get_allocatable_resources(node)
    used_cpu = 0
    used_memory = 0

    for pod in existing_pods:
        if pod.get("node_name") == node["name"]:
            for container in pod.get("containers", []):
                requests = container.get("resources", {}).get("requests", {})
                used_cpu += requests.get("cpu_millicores", 0)
                used_memory += requests.get("memory_mb", 0)

    total_cpu = allocatable.get("cpu_millicores", 1)
    total_memory = allocatable.get("memory_mb", 1)

    return {
        "cpu": min(used_cpu / total_cpu, 1.0) if total_cpu > 0 else 0.0,
        "memory": min(used_memory / total_memory, 1.0) if total_memory > 0 else 0.0,
        "used_cpu": used_cpu,
        "used_memory": used_memory,
        "total_cpu": total_cpu,
        "total_memory": total_memory
    }


def compute_pod_resource_totals(pod):
    """Sum total resource requests and limits across all containers in a pod."""
    total_requests = {"cpu_millicores": 0, "memory_mb": 0}
    total_limits = {"cpu_millicores": 0, "memory_mb": 0}

    for container in pod.get("containers", []):
        resources = container.get("resources", {})
        requests = resources.get("requests", {})
        limits = resources.get("limits", {})

        total_requests["cpu_millicores"] += requests.get("cpu_millicores", 0)
        total_requests["memory_mb"] += requests.get("memory_mb", 0)
        total_limits["cpu_millicores"] += limits.get("cpu_millicores", 0)
        total_limits["memory_mb"] += limits.get("memory_mb", 0)

    return {"requests": total_requests, "limits": total_limits}


def determine_qos_class(pod):
    """
    Determine the QoS class for a pod based on resource specifications.

    - Guaranteed: all containers have requests == limits for CPU and memory
    - Burstable: at least one container has requests != limits
    - BestEffort: no requests or limits specified
    """
    has_requests = False
    all_guaranteed = True

    for container in pod.get("containers", []):
        resources = container.get("resources", {})
        requests = resources.get("requests", {})
        limits = resources.get("limits", {})

        cpu_req = requests.get("cpu_millicores", 0)
        mem_req = requests.get("memory_mb", 0)
        cpu_lim = limits.get("cpu_millicores", 0)
        mem_lim = limits.get("memory_mb", 0)

        if cpu_req > 0 or mem_req > 0:
            has_requests = True

        if cpu_req != cpu_lim or mem_req != mem_lim:
            all_guaranteed = False

    if not has_requests:
        return "BestEffort"
    elif all_guaranteed:
        return "Guaranteed"
    else:
        return "Burstable"
