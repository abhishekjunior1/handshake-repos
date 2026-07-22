"""Inheritance engine for CIS compliance rule hierarchy.

Resolves effective rule configurations through parent-child inheritance.
Controls inherit properties from their parent sections and profiles
unless explicitly overridden at a lower level.

Inheritance follows the CIS benchmark convention:
- Profile defines base applicability and scoring methodology
- Sections define grouping and can override severity levels
- Controls are the leaf evaluation units

The engine supports two evaluation modes:
- full_chain: walks complete ancestor chain for inherited properties
- leaf_only: uses only the leaf control definition (no inheritance)
"""

from typing import Any


def resolve_inheritance(controls: list[dict[str, Any]],
                        mode: str = "full_chain") -> list[dict[str, Any]]:
    """Resolve inherited properties for a set of controls.

    Args:
        controls: List of control definitions (may include ancestor data)
        mode: Either "full_chain" (walk ancestors) or "leaf_only" (direct only)

    Returns:
        Controls with resolved effective properties.
    """
    resolved = []
    for control in controls:
        if mode == "full_chain":
            resolved_control = _resolve_full_chain(control)
        else:
            resolved_control = _resolve_leaf_only(control)
        resolved.append(resolved_control)
    return resolved


def _resolve_full_chain(control: dict[str, Any]) -> dict[str, Any]:
    """Resolve control properties by walking the full ancestor chain.

    When a control is nested in a section hierarchy, properties cascade:
    - effective_severity: use section override if present, else control's own
    - applicability_constraints: union of all ancestor constraints
    - scoring_weight: product of all ancestor weights
    """
    resolved = dict(control)

    # Resolve effective severity (section override > control default)
    if "effective_severity" not in resolved:
        resolved["effective_severity"] = resolved.get("severity", "medium")

    # Resolve scoring weight through ancestor chain
    base_weight = resolved.get("weight", 1.0)
    ancestor_weight = _compute_ancestor_weight(control)
    resolved["effective_weight"] = base_weight * ancestor_weight

    # Resolve applicability constraints
    constraints = control.get("applicability_constraints", [])
    resolved["effective_applicability"] = _merge_constraints(constraints)

    # Mark as fully resolved
    resolved["inheritance_resolved"] = True
    resolved["resolution_mode"] = "full_chain"

    return resolved


def _resolve_leaf_only(control: dict[str, Any]) -> dict[str, Any]:
    """Resolve control using only its own leaf-level properties.

    Ignores any inherited properties from ancestor sections/profiles.
    Uses the control's direct definition only.
    """
    resolved = dict(control)

    # Use only the control's own severity
    resolved["effective_severity"] = resolved.get("severity", "medium")

    # No ancestor weight multiplication
    resolved["effective_weight"] = resolved.get("weight", 1.0)

    # No inherited constraints
    resolved["effective_applicability"] = {}

    # Mark resolution mode
    resolved["inheritance_resolved"] = True
    resolved["resolution_mode"] = "leaf_only"

    return resolved


def _compute_ancestor_weight(control: dict[str, Any]) -> float:
    """Compute the cumulative weight factor from ancestor nodes.

    Each ancestor section can define a weight multiplier that affects
    all descendant controls. The effective weight is the product of
    all ancestor weights in the chain.
    """
    constraints = control.get("applicability_constraints", [])
    weight = 1.0
    for constraint in constraints:
        if isinstance(constraint, dict) and "weight" in constraint:
            weight *= constraint["weight"]
    return weight


def _merge_constraints(constraints: list[Any]) -> dict[str, Any]:
    """Merge applicability constraints from multiple ancestor levels.

    Constraints from deeper levels (closer to the control) take
    precedence over shallower constraints for the same key.
    """
    merged: dict[str, Any] = {}
    for constraint in constraints:
        if isinstance(constraint, dict):
            for key, value in constraint.items():
                if key == "platforms":
                    # Platforms use intersection (all ancestors must agree)
                    if "platforms" in merged:
                        existing = set(merged["platforms"])
                        new = set(value) if isinstance(value, list) else {value}
                        merged["platforms"] = list(existing & new)
                    else:
                        merged["platforms"] = value if isinstance(value, list) else [value]
                elif key == "environments":
                    # Environments use union (any ancestor can add)
                    if "environments" in merged:
                        existing = set(merged["environments"])
                        new = set(value) if isinstance(value, list) else {value}
                        merged["environments"] = list(existing | new)
                    else:
                        merged["environments"] = value if isinstance(value, list) else [value]
                else:
                    # Other keys: deeper level wins (last in list)
                    merged[key] = value
    return merged


def filter_applicable_controls(controls: list[dict[str, Any]],
                               resource: dict[str, Any]) -> list[dict[str, Any]]:
    """Filter controls based on applicability to a specific resource.

    A control applies to a resource if:
    1. No applicability constraints exist (applies to all), OR
    2. The resource matches the platform/environment constraints
    """
    applicable = []
    for control in controls:
        constraints = control.get("effective_applicability", {})
        if not constraints:
            applicable.append(control)
            continue

        if _resource_matches_constraints(resource, constraints):
            applicable.append(control)

    return applicable


def _resource_matches_constraints(resource: dict[str, Any],
                                  constraints: dict[str, Any]) -> bool:
    """Check if a resource satisfies the applicability constraints."""
    resource_platform = resource.get("platform", "")
    resource_env = resource.get("environment", "")

    # Check platform constraint
    if "platforms" in constraints:
        if resource_platform not in constraints["platforms"]:
            return False

    # Check environment constraint
    if "environments" in constraints:
        if resource_env not in constraints["environments"]:
            return False

    return True
