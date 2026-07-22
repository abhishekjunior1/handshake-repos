"""Policy resolver for CIS compliance evaluation.

Evaluates system resources against resolved control definitions.
Determines pass/fail status for each control-resource pair based
on the control's evaluation criteria and resource properties.
"""

from typing import Any
import re


def evaluate_controls(controls: list[dict[str, Any]],
                      resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evaluate all controls against all applicable resources.

    For each control, evaluates every resource that falls within the
    control's applicability scope. Returns a list of evaluation results
    with pass/fail status and evidence.
    """
    results = []
    for control in controls:
        control_results = _evaluate_single_control(control, resources)
        results.extend(control_results)
    return results


def _evaluate_single_control(control: dict[str, Any],
                             resources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Evaluate a single control against all applicable resources."""
    results = []
    control_id = control["id"]
    criteria = control.get("criteria", {})

    for resource in resources:
        if not _is_resource_in_scope(control, resource):
            continue

        result = {
            "control_id": control_id,
            "resource_id": resource["id"],
            "control_type": control.get("type", "scored"),
            "severity": control.get("effective_severity", control.get("severity", "medium")),
            "cvss_score": control.get("cvss_score", 5.0),
            "status": "not_evaluated",
            "evidence": [],
            "full_path": control.get("full_path", control_id),
        }

        if criteria:
            status, evidence = _check_criteria(criteria, resource)
            result["status"] = status
            result["evidence"] = evidence
        else:
            # Controls without explicit criteria default to manual review
            result["status"] = "manual_review"
            result["evidence"] = ["No automated criteria defined"]

        results.append(result)

    return results


def _is_resource_in_scope(control: dict[str, Any],
                          resource: dict[str, Any]) -> bool:
    """Determine if a resource is in scope for a control.

    Uses the control's scope definition to match against resource
    type and tags.
    """
    scope = control.get("scope", {})
    if not scope:
        return True

    # Check resource type match
    target_types = scope.get("resource_types", [])
    if target_types and resource.get("type") not in target_types:
        return False

    # Check tag requirements
    required_tags = scope.get("required_tags", {})
    resource_tags = resource.get("tags", {})
    for tag_key, tag_value in required_tags.items():
        if tag_key not in resource_tags:
            return False
        if tag_value != "*" and resource_tags[tag_key] != tag_value:
            return False

    return True


def _check_criteria(criteria: dict[str, Any],
                    resource: dict[str, Any]) -> tuple[str, list[str]]:
    """Check evaluation criteria against resource properties.

    Returns (status, evidence) tuple where status is 'pass' or 'fail'.
    """
    check_type = criteria.get("type", "property_check")
    evidence = []

    if check_type == "property_check":
        return _check_property(criteria, resource, evidence)
    elif check_type == "regex_match":
        return _check_regex(criteria, resource, evidence)
    elif check_type == "threshold":
        return _check_threshold(criteria, resource, evidence)
    elif check_type == "presence":
        return _check_presence(criteria, resource, evidence)
    elif check_type == "composite":
        return _check_composite(criteria, resource, evidence)
    else:
        evidence.append(f"Unknown criteria type: {check_type}")
        return "not_evaluated", evidence


def _check_property(criteria: dict[str, Any], resource: dict[str, Any],
                    evidence: list[str]) -> tuple[str, list[str]]:
    """Check if a resource property matches expected value."""
    property_path = criteria.get("property", "")
    expected = criteria.get("expected_value")
    operator = criteria.get("operator", "eq")

    actual = _get_nested_property(resource.get("properties", {}), property_path)

    if actual is None:
        evidence.append(f"Property '{property_path}' not found on resource")
        return "fail", evidence

    passed = _compare_values(actual, expected, operator)
    if passed:
        evidence.append(f"Property '{property_path}' = {actual} (expected: {expected})")
        return "pass", evidence
    else:
        evidence.append(f"Property '{property_path}' = {actual} (expected: {expected}, operator: {operator})")
        return "fail", evidence


def _check_regex(criteria: dict[str, Any], resource: dict[str, Any],
                 evidence: list[str]) -> tuple[str, list[str]]:
    """Check if a resource property matches a regex pattern."""
    property_path = criteria.get("property", "")
    pattern = criteria.get("pattern", "")
    should_match = criteria.get("should_match", True)

    actual = _get_nested_property(resource.get("properties", {}), property_path)
    if actual is None:
        evidence.append(f"Property '{property_path}' not found")
        return "fail", evidence

    actual_str = str(actual)
    matches = bool(re.search(pattern, actual_str))

    if matches == should_match:
        evidence.append(f"Property '{property_path}' regex {'matches' if matches else 'no match'} as expected")
        return "pass", evidence
    else:
        evidence.append(f"Property '{property_path}' = '{actual_str}' {'matches' if matches else 'does not match'} pattern '{pattern}'")
        return "fail", evidence


def _check_threshold(criteria: dict[str, Any], resource: dict[str, Any],
                     evidence: list[str]) -> tuple[str, list[str]]:
    """Check if a numeric property meets a threshold."""
    property_path = criteria.get("property", "")
    threshold = criteria.get("threshold", 0)
    direction = criteria.get("direction", "gte")

    actual = _get_nested_property(resource.get("properties", {}), property_path)
    if actual is None:
        evidence.append(f"Property '{property_path}' not found")
        return "fail", evidence

    try:
        actual_num = float(actual)
    except (ValueError, TypeError):
        evidence.append(f"Property '{property_path}' = '{actual}' is not numeric")
        return "fail", evidence

    passed = _threshold_check(actual_num, threshold, direction)
    if passed:
        evidence.append(f"Property '{property_path}' = {actual_num} meets threshold {direction} {threshold}")
        return "pass", evidence
    else:
        evidence.append(f"Property '{property_path}' = {actual_num} fails threshold {direction} {threshold}")
        return "fail", evidence


def _check_presence(criteria: dict[str, Any], resource: dict[str, Any],
                    evidence: list[str]) -> tuple[str, list[str]]:
    """Check if a property exists (or doesn't exist) on the resource."""
    property_path = criteria.get("property", "")
    should_exist = criteria.get("should_exist", True)

    actual = _get_nested_property(resource.get("properties", {}), property_path)
    exists = actual is not None

    if exists == should_exist:
        evidence.append(f"Property '{property_path}' {'exists' if exists else 'absent'} as expected")
        return "pass", evidence
    else:
        evidence.append(f"Property '{property_path}' {'exists' if exists else 'absent'} (expected {'present' if should_exist else 'absent'})")
        return "fail", evidence


def _check_composite(criteria: dict[str, Any], resource: dict[str, Any],
                     evidence: list[str]) -> tuple[str, list[str]]:
    """Evaluate a composite criteria (AND/OR of sub-criteria)."""
    logic = criteria.get("logic", "and")
    sub_criteria = criteria.get("checks", [])

    sub_results = []
    for sub in sub_criteria:
        status, sub_evidence = _check_criteria(sub, resource)
        sub_results.append(status == "pass")
        evidence.extend(sub_evidence)

    if logic == "and":
        passed = all(sub_results)
    else:
        passed = any(sub_results)

    return "pass" if passed else "fail", evidence


def _get_nested_property(properties: dict[str, Any], path: str) -> Any:
    """Navigate nested dictionaries using dot-notation path."""
    parts = path.split(".")
    current = properties
    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def _compare_values(actual: Any, expected: Any, operator: str) -> bool:
    """Compare two values using the specified operator."""
    if operator == "eq":
        return actual == expected
    elif operator == "ne":
        return actual != expected
    elif operator == "gt":
        return float(actual) > float(expected)
    elif operator == "gte":
        return float(actual) >= float(expected)
    elif operator == "lt":
        return float(actual) < float(expected)
    elif operator == "lte":
        return float(actual) <= float(expected)
    elif operator == "in":
        return actual in expected
    elif operator == "contains":
        return expected in actual
    return False


def _threshold_check(value: float, threshold: float, direction: str) -> bool:
    """Perform a directional threshold check."""
    if direction == "gte":
        return value >= threshold
    elif direction == "gt":
        return value > threshold
    elif direction == "lte":
        return value <= threshold
    elif direction == "lt":
        return value < threshold
    elif direction == "eq":
        return abs(value - threshold) < 1e-9
    return False
