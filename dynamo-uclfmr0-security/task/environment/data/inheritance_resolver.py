"""
Inheritance resolver for profile hierarchy in hardening baselines.
Resolves rule inheritance through parent-child profile relationships.
"""


def build_profile_tree(profiles: dict) -> dict:
    """
    Build adjacency representation of profile hierarchy.
    Returns dict mapping profile_id -> list of child profile_ids.
    """
    tree = {pid: [] for pid in profiles}
    for pid, profile in profiles.items():
        parent_id = profile.get("parent_id")
        if parent_id and parent_id in tree:
            tree[parent_id].append(pid)
    return tree


def get_ancestor_chain(profiles: dict, profile_id: str) -> list:
    """
    Walk full ancestor chain from a profile up to the root.
    Returns list of profile_ids from immediate parent to root (excludes self).
    """
    chain = []
    current_id = profile_id
    visited = set()

    while current_id in profiles:
        parent_id = profiles[current_id].get("parent_id")
        if parent_id is None or parent_id in visited:
            break
        visited.add(parent_id)
        chain.append(parent_id)
        current_id = parent_id

    return chain


def resolve_inherited_rules(rules: list, profiles: dict, profile_id: str) -> list:
    """
    Resolve all rules applicable to a profile through inheritance.
    Walks the full ancestor chain and collects rules from each ancestor profile.
    Child profile rules override parent rules with the same rule ID to prevent
    conflicting thresholds from propagating down the hierarchy.

    Returns deduplicated list of rules applicable to the profile.
    """
    ancestor_chain = get_ancestor_chain(profiles, profile_id)
    all_profile_ids = [profile_id] + ancestor_chain

    # Collect rules with child-overrides-parent precedence for same rule IDs
    seen_rule_ids = set()
    resolved_rules = []

    for pid in all_profile_ids:
        for rule in rules:
            if pid in rule.get("profile_ids", []):
                if rule["id"] not in seen_rule_ids:
                    seen_rule_ids.add(rule["id"])
                    resolved_rules.append(rule)

    return resolved_rules


def get_effective_profile_level(profiles: dict, profile_id: str) -> int:
    """
    Compute effective security level for a profile.
    Level increases with depth in hierarchy (more specific = higher level).
    """
    chain = get_ancestor_chain(profiles, profile_id)
    return len(chain) + 1


def get_all_descendant_profiles(profiles: dict, profile_id: str) -> list:
    """
    Get all descendant profile IDs for a given profile (BFS traversal).
    """
    descendants = []
    queue = [profile_id]
    visited = {profile_id}

    while queue:
        current = queue.pop(0)
        for pid, profile in profiles.items():
            if profile.get("parent_id") == current and pid not in visited:
                visited.add(pid)
                descendants.append(pid)
                queue.append(pid)

    return descendants


def compute_inheritance_depth(profiles: dict, profile_id: str) -> int:
    """Compute how deep a profile is in the hierarchy (root = 0)."""
    depth = 0
    current_id = profile_id
    visited = set()

    while current_id in profiles:
        parent_id = profiles[current_id].get("parent_id")
        if parent_id is None or parent_id in visited:
            break
        visited.add(current_id)
        depth += 1
        current_id = parent_id

    return depth


def validate_hierarchy(profiles: dict) -> bool:
    """
    Validate that profile hierarchy has no cycles and all parent_ids reference
    existing profiles.
    """
    for pid, profile in profiles.items():
        parent_id = profile.get("parent_id")
        if parent_id is not None and parent_id not in profiles:
            return False

    # Check for cycles
    for pid in profiles:
        visited = set()
        current = pid
        while current in profiles:
            if current in visited:
                return False
            visited.add(current)
            current = profiles[current].get("parent_id")
            if current is None:
                break

    return True
