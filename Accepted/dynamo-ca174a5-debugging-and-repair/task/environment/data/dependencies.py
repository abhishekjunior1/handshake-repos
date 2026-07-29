"""DAG dependency resolution and topological ordering."""
from collections import deque


def resolve_order(dag):
    """Compute execution order for a DAG using Kahn's algorithm.

    Stages with equal priority (same topological level) are executed
    in their definition order from the DAG specification.

    Args:
        dag: dict with 'stages' (list of stage defs in definition order)
              and each stage has 'name' and 'depends_on' (list of names).

    Returns:
        List of stage names in valid execution order.
    """
    stages = {s["name"]: s for s in dag["stages"]}
    in_degree = {name: 0 for name in stages}
    graph = {name: [] for name in stages}

    for s in dag["stages"]:
        for dep in s.get("depends_on", []):
            graph[dep].append(s["name"])
            in_degree[s["name"]] += 1

    # Seed queue with zero in-degree stages
    queue = sorted([n for n, d in in_degree.items() if d == 0])
    order = []

    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
        queue.sort()

    return order


def get_dependencies(dag, stage_name):
    """Get the dependency names for a given stage."""
    for s in dag["stages"]:
        if s["name"] == stage_name:
            return s.get("depends_on", [])
    return []
