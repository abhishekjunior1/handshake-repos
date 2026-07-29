"""
Dependency Resolver Module
==========================
Resolves inter-flag dependency constraints for the evaluation pipeline.
Handles enable/disable cascades where one flag's state depends on another.

Dependency types supported:
- "requires": Flag A requires Flag B to be enabled. If B is disabled, A is disabled.
- "excludes": Flag A excludes Flag B. If A is enabled, B must be disabled.

Dependencies are processed iteratively until a stable state is reached
(no more cascading changes), preventing infinite loops with a max iteration limit.
"""

from typing import Dict, List, Tuple


def resolve_dependencies(flags: list, evaluations: dict) -> dict:
    """
    Resolve flag dependencies and cascade enable/disable decisions.

    Processes all dependency declarations and ensures that dependent flags
    respect their parent flag states. Returns updated evaluations with
    dependency overrides applied.

    Args:
        flags: List of flag definition dictionaries.
        evaluations: Current evaluation state mapping flag_name -> {enabled, reason}.

    Returns:
        Dictionary with:
        - 'evaluations': Updated evaluation mapping with dependency overrides.
        - 'overrides': List of override records describing what changed.
        - 'chains_resolved': Number of dependency chains processed.
    """
    # Build dependency graph
    dependency_graph = _build_dependency_graph(flags)

    if not dependency_graph:
        return {
            "evaluations": evaluations,
            "overrides": [],
            "chains_resolved": 0,
        }

    # Iteratively resolve until stable (max 10 iterations to prevent loops)
    overrides = []
    max_iterations = 10
    chains_resolved = 0

    for iteration in range(max_iterations):
        changes_made = False

        for flag_name, deps in dependency_graph.items():
            if flag_name not in evaluations:
                continue

            for dep in deps:
                dep_type = dep["type"]
                dep_target = dep["target"]

                if dep_target not in evaluations:
                    continue

                override = _apply_dependency_rule(
                    flag_name, dep_type, dep_target, evaluations
                )

                if override is not None:
                    evaluations[override["flag"]]["enabled"] = override["new_state"]
                    evaluations[override["flag"]]["reason"] = "dependency"
                    overrides.append(override)
                    changes_made = True
                    chains_resolved += 1

        if not changes_made:
            break

    return {
        "evaluations": evaluations,
        "overrides": overrides,
        "chains_resolved": chains_resolved,
    }


def _build_dependency_graph(flags: list) -> Dict[str, List[dict]]:
    """
    Build a dependency graph from flag definitions.

    Returns a mapping of flag_name -> list of dependency declarations.
    """
    graph = {}

    for flag in flags:
        flag_name = flag["name"]
        dependencies = flag.get("dependencies", [])

        if dependencies:
            graph[flag_name] = []
            for dep in dependencies:
                graph[flag_name].append({
                    "type": dep.get("type", "requires"),
                    "target": dep.get("flag", dep.get("target", "")),
                })

    return graph


def _apply_dependency_rule(flag_name: str, dep_type: str, dep_target: str,
                           evaluations: dict) -> dict:
    """
    Apply a single dependency rule and determine if an override is needed.

    Returns an override record if state change is needed, None otherwise.
    """
    if dep_type == "requires":
        # If the required flag is disabled, this flag must also be disabled
        target_enabled = evaluations[dep_target]["enabled"]
        current_enabled = evaluations[flag_name]["enabled"]

        if not target_enabled and current_enabled:
            return {
                "flag": flag_name,
                "dep_type": dep_type,
                "dep_target": dep_target,
                "old_state": True,
                "new_state": False,
                "reason": f"requires:{dep_target}:disabled",
            }

    elif dep_type == "excludes":
        # If this flag is enabled, the excluded flag must be disabled
        current_enabled = evaluations[flag_name]["enabled"]
        target_enabled = evaluations[dep_target]["enabled"]

        if current_enabled and target_enabled:
            return {
                "flag": dep_target,
                "dep_type": dep_type,
                "dep_target": flag_name,
                "old_state": True,
                "new_state": False,
                "reason": f"excluded_by:{flag_name}",
            }

    return None


def get_dependency_chains(flags: list) -> List[List[str]]:
    """
    Identify all dependency chains in the flag definitions.

    Returns a list of chains, where each chain is an ordered list of flag names.
    """
    graph = _build_dependency_graph(flags)
    visited = set()
    chains = []

    for flag_name in graph:
        if flag_name not in visited:
            chain = _trace_chain(flag_name, graph, visited)
            if len(chain) > 1:
                chains.append(chain)

    return chains


def _trace_chain(start: str, graph: Dict[str, List[dict]], visited: set) -> List[str]:
    """Trace a dependency chain from a starting flag."""
    chain = []
    current = start
    seen_in_chain = set()

    while current and current not in seen_in_chain:
        seen_in_chain.add(current)
        visited.add(current)
        chain.append(current)

        # Follow first 'requires' dependency
        deps = graph.get(current, [])
        next_flag = None
        for dep in deps:
            if dep["type"] == "requires":
                next_flag = dep["target"]
                break
        current = next_flag

    return chain
