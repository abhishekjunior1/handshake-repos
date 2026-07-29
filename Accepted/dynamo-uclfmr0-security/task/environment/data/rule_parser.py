"""
Rule parser for CIS-style hardening baseline configurations.
Parses rule definitions, profiles, and resource inventories from JSON config.
"""

import json
from typing import Any


def load_baseline_config(config_path: str) -> dict:
    """Load and validate baseline configuration from JSON file."""
    with open(config_path, 'r') as f:
        config = json.load(f)

    required_keys = ["profiles", "rules", "resources", "waivers"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config key: {key}")

    return config


def parse_rules(config: dict) -> list:
    """
    Parse hardening rules from configuration.
    Each rule has: id, category, severity, check_type, threshold, description.
    """
    rules = []
    for rule_def in config.get("rules", []):
        rule = {
            "id": rule_def["id"],
            "category": rule_def["category"],
            "severity": rule_def["severity"],
            "check_type": rule_def.get("check_type", "boolean"),
            "threshold": rule_def.get("threshold"),
            "description": rule_def.get("description", ""),
            "remediation": rule_def.get("remediation", ""),
            "profile_ids": rule_def.get("profile_ids", []),
        }
        rules.append(rule)
    return rules


def parse_profiles(config: dict) -> dict:
    """
    Parse profile hierarchy from configuration.
    Returns dict mapping profile_id -> profile definition including parent reference.
    """
    profiles = {}
    for profile_def in config.get("profiles", []):
        profile = {
            "id": profile_def["id"],
            "name": profile_def["name"],
            "parent_id": profile_def.get("parent_id"),
            "level": profile_def.get("level", 1),
            "description": profile_def.get("description", ""),
        }
        profiles[profile["id"]] = profile
    return profiles


def parse_resources(config: dict) -> list:
    """
    Parse resource inventory from configuration.
    Each resource has: id, type, status, tags, profile_id.
    """
    resources = []
    for res_def in config.get("resources", []):
        resource = {
            "id": res_def["id"],
            "type": res_def["type"],
            "status": res_def.get("status", "running"),
            "tags": res_def.get("tags", {}),
            "profile_id": res_def.get("profile_id"),
            "region": res_def.get("region", "us-east-1"),
            "metadata": res_def.get("metadata", {}),
        }
        resources.append(resource)
    return resources


def parse_waivers(config: dict) -> list:
    """
    Parse exception waivers from configuration.
    Each waiver has: id, rule_id, resource_pattern, reason, expiry.
    """
    waivers = []
    for waiver_def in config.get("waivers", []):
        waiver = {
            "id": waiver_def["id"],
            "rule_id": waiver_def["rule_id"],
            "resource_pattern": waiver_def["resource_pattern"],
            "reason": waiver_def.get("reason", ""),
            "expiry": waiver_def.get("expiry"),
            "approved_by": waiver_def.get("approved_by", ""),
        }
        waivers.append(waiver)
    return waivers


def get_rules_for_profile(rules: list, profile_id: str) -> list:
    """
    Get rules directly assigned to a specific profile.
    Returns rules whose profile_ids list includes the given profile_id.
    """
    profile_rules = []
    for rule in rules:
        if profile_id in rule.get("profile_ids", []):
            profile_rules.append(rule)
    return profile_rules


def validate_rule_schema(rule: dict) -> bool:
    """Validate that a rule has all required fields with correct types."""
    required_fields = {"id": str, "category": str, "severity": (int, float)}
    for field, field_type in required_fields.items():
        if field not in rule:
            return False
        if not isinstance(rule[field], field_type):
            return False
    if rule["severity"] < 1 or rule["severity"] > 10:
        return False
    return True


def categorize_rules(rules: list) -> dict:
    """Group rules by their category field."""
    categories = {}
    for rule in rules:
        cat = rule["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(rule)
    return categories


def get_rule_by_id(rules: list, rule_id: str) -> dict:
    """Find a rule by its ID. Returns empty dict if not found."""
    for rule in rules:
        if rule["id"] == rule_id:
            return rule
    return {}
