"""
Targeting Engine Module
=======================
Evaluates whether a device matches a flag's targeting rules.
Supports multiple rule operators: equals, not_equals, in_list,
not_in_list, contains, version_gte, version_lte, and regex matching.

A device passes targeting if ALL rules match (AND logic).
If no targeting rules are defined, the device passes by default.
"""

import re
from typing import Any


def evaluate_targeting(device: dict, flag: dict) -> dict:
    """
    Evaluate whether a device matches a flag's targeting rules.

    Args:
        device: Device record dictionary with attributes.
        flag: Flag definition dictionary with targeting_rules.

    Returns:
        Dictionary with 'passes' (bool) and 'reason' (str) fields.
    """
    rules = flag.get("targeting_rules", [])

    # No targeting rules means flag applies to all devices
    if not rules:
        return {"passes": True, "reason": "no_targeting_rules"}

    # All rules must pass (AND logic)
    for rule in rules:
        result = _evaluate_single_rule(device, rule)
        if not result["matches"]:
            return {
                "passes": False,
                "reason": f"failed_rule:{rule.get('attribute', 'unknown')}",
            }

    return {"passes": True, "reason": "all_rules_matched"}


def _evaluate_single_rule(device: dict, rule: dict) -> dict:
    """Evaluate a single targeting rule against a device."""
    attribute = rule.get("attribute", "")
    operator = rule.get("operator", "equals")
    value = rule.get("value")

    device_value = _get_device_attribute(device, attribute)

    if device_value is None:
        return {"matches": False, "reason": "attribute_not_found"}

    matcher = _get_operator_function(operator)
    matches = matcher(device_value, value)

    return {"matches": matches, "reason": operator}


def _get_device_attribute(device: dict, attribute: str) -> Any:
    """Extract an attribute value from a device record."""
    # Check top-level fields first
    top_level_fields = ["device_id", "region", "firmware_version", "device_type", "last_seen"]
    if attribute in top_level_fields:
        return device.get(attribute)

    # Then check nested attributes
    attributes = device.get("attributes", {})
    return attributes.get(attribute)


def _get_operator_function(operator: str):
    """Return the comparison function for the given operator."""
    operators = {
        "equals": _op_equals,
        "not_equals": _op_not_equals,
        "in_list": _op_in_list,
        "not_in_list": _op_not_in_list,
        "contains": _op_contains,
        "version_gte": _op_version_gte,
        "version_lte": _op_version_lte,
        "regex": _op_regex,
        "greater_than": _op_greater_than,
        "less_than": _op_less_than,
    }
    return operators.get(operator, _op_equals)


def _op_equals(device_value: Any, rule_value: Any) -> bool:
    """Exact equality check."""
    return str(device_value) == str(rule_value)


def _op_not_equals(device_value: Any, rule_value: Any) -> bool:
    """Inequality check."""
    return str(device_value) != str(rule_value)


def _op_in_list(device_value: Any, rule_value: Any) -> bool:
    """Check if device value is in the specified list."""
    if not isinstance(rule_value, list):
        return False
    return str(device_value) in [str(v) for v in rule_value]


def _op_not_in_list(device_value: Any, rule_value: Any) -> bool:
    """Check if device value is NOT in the specified list."""
    if not isinstance(rule_value, list):
        return True
    return str(device_value) not in [str(v) for v in rule_value]


def _op_contains(device_value: Any, rule_value: Any) -> bool:
    """Check if device value contains the substring."""
    return str(rule_value) in str(device_value)


def _op_version_gte(device_value: Any, rule_value: Any) -> bool:
    """Version comparison: device >= rule value."""
    device_parts = _parse_version(str(device_value))
    rule_parts = _parse_version(str(rule_value))
    return device_parts >= rule_parts


def _op_version_lte(device_value: Any, rule_value: Any) -> bool:
    """Version comparison: device <= rule value."""
    device_parts = _parse_version(str(device_value))
    rule_parts = _parse_version(str(rule_value))
    return device_parts <= rule_parts


def _op_regex(device_value: Any, rule_value: Any) -> bool:
    """Regex pattern matching."""
    try:
        return bool(re.match(str(rule_value), str(device_value)))
    except re.error:
        return False


def _op_greater_than(device_value: Any, rule_value: Any) -> bool:
    """Numeric greater than comparison."""
    try:
        return float(device_value) > float(rule_value)
    except (ValueError, TypeError):
        return False


def _op_less_than(device_value: Any, rule_value: Any) -> bool:
    """Numeric less than comparison."""
    try:
        return float(device_value) < float(rule_value)
    except (ValueError, TypeError):
        return False


def _parse_version(version_str: str) -> tuple:
    """Parse a version string into comparable tuple."""
    parts = []
    for part in version_str.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            parts.append(0)
    # Pad to 3 components
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)
