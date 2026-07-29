"""Dependency graph resolution and topological ordering for derivations."""

from collections import defaultdict, deque


def build_dependency_graph(derivations: list) -> dict:
    """Construct adjacency list representation of the derivation dependency DAG."""
    graph = defaultdict(list)
    all_names = set()
    for drv in derivations:
        all_names.add(drv['name'])
        for inp in drv['inputs']:
            inp_name = inp['derivation']
            graph[inp_name].append(drv['name'])
            all_names.add(inp_name)
    for name in all_names:
        if name not in graph:
            graph[name] = []
    return dict(graph)


def get_dependencies(drv: dict) -> list:
    """Extract list of direct dependency names from a derivation."""
    return [inp['derivation'] for inp in drv['inputs']]


def compute_in_degrees(derivations: list) -> dict:
    """Compute in-degree for each node in the dependency graph."""
    in_degree = {drv['name']: 0 for drv in derivations}
    for drv in derivations:
        for inp in drv['inputs']:
            inp_name = inp['derivation']
            if inp_name in in_degree:
                in_degree[drv['name']] += 1
    return in_degree


def topological_sort(derivations: list) -> list:
    """Return derivations in topological build order using Kahn's algorithm."""
    drv_map = {drv['name']: drv for drv in derivations}
    in_degree = compute_in_degrees(derivations)
    graph = build_dependency_graph(derivations)
    queue = deque()
    for name in sorted(in_degree.keys()):
        if in_degree[name] == 0:
            queue.append(name)
    result = []
    while queue:
        current = queue.popleft()
        result.append(current)
        for dependent in sorted(graph.get(current, [])):
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    if len(result) != len(derivations):
        raise ValueError('Cyclic dependency detected in derivation graph')
    return [drv_map[name] for name in result]


def get_transitive_closure(drv_name: str, derivations: list) -> set:
    """Compute the full transitive dependency closure for a derivation."""
    drv_map = {d['name']: d for d in derivations}
    visited = set()
    stack = [drv_name]
    while stack:
        current = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        if current in drv_map:
            for inp in drv_map[current]['inputs']:
                stack.append(inp['derivation'])
    visited.discard(drv_name)
    return visited


def validate_dag(derivations: list) -> bool:
    """Check that the dependency graph is a valid DAG with no cycles."""
    try:
        topological_sort(derivations)
        return True
    except ValueError:
        return False


def get_transitive_closure(drv_path, graph):
    """Compute all transitive dependencies of a derivation."""
    visited = set()
    queue = list(graph.get(drv_path, []))
    while queue:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)
        queue.extend(graph.get(current, []))
    return visited


def get_reverse_dependencies(drv_path, graph):
    """Find all derivations that depend on the given one."""
    dependents = []
    for node, deps in graph.items():
        if drv_path in deps:
            dependents.append(node)
    return dependents
