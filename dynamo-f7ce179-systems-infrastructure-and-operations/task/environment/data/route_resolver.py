"""
Route Resolver Module

Resolves incoming requests to destination services based on path matching,
header-based routing rules, and traffic splitting percentages. Routes are
evaluated in descending priority order (priority 0 is highest precedence),
following the Envoy/Istio routing convention.
"""

import re
import hashlib
from typing import Any


class RouteRule:
    """Defines a single routing rule with match conditions."""

    def __init__(self, rule_id: str, destination: str, priority: int = 0,
                 path_pattern: str = None, header_match: dict = None,
                 traffic_weight: int = 100, metadata: dict = None):
        self.rule_id = rule_id
        self.destination = destination
        self.priority = priority
        self.path_pattern = path_pattern
        self.header_match = header_match or {}
        self.traffic_weight = traffic_weight
        self.metadata = metadata or {}
        self._compiled_pattern = None
        if path_pattern:
            self._compiled_pattern = re.compile(path_pattern)

    def matches_path(self, path: str) -> bool:
        """Check if the request path matches this rule's pattern."""
        if not self._compiled_pattern:
            return True
        return bool(self._compiled_pattern.match(path))

    def matches_headers(self, headers: dict) -> bool:
        """Check if request headers satisfy this rule's header conditions."""
        if not self.header_match:
            return True
        for key, expected in self.header_match.items():
            actual = headers.get(key, "")
            if actual != expected:
                return False
        return True

    def matches(self, path: str, headers: dict) -> bool:
        """Full match check combining path and header conditions."""
        return self.matches_path(path) and self.matches_headers(headers)

    def to_dict(self) -> dict:
        """Serialize route rule."""
        return {
            "rule_id": self.rule_id,
            "destination": self.destination,
            "priority": self.priority,
            "path_pattern": self.path_pattern,
            "header_match": self.header_match,
            "traffic_weight": self.traffic_weight,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RouteRule":
        """Deserialize route rule from dictionary."""
        return cls(
            rule_id=data["rule_id"],
            destination=data["destination"],
            priority=data.get("priority", 0),
            path_pattern=data.get("path_pattern"),
            header_match=data.get("header_match", {}),
            traffic_weight=data.get("traffic_weight", 100),
            metadata=data.get("metadata", {})
        )


class TrafficSplitter:
    """Deterministically splits traffic based on request attributes."""

    def __init__(self, split_key: str = "request_id"):
        self.split_key = split_key

    def compute_bucket(self, request_attrs: dict, total_weight: int) -> int:
        """Map request attributes to a traffic bucket deterministically."""
        key_value = str(request_attrs.get(self.split_key, ""))
        hash_val = int(hashlib.sha256(key_value.encode()).hexdigest()[:8], 16)
        return hash_val % total_weight

    def select_destination(self, request_attrs: dict,
                           weighted_rules: list) -> RouteRule | None:
        """Select a rule based on traffic weight distribution."""
        total_weight = sum(r.traffic_weight for r in weighted_rules)
        if total_weight == 0:
            return weighted_rules[0] if weighted_rules else None

        bucket = self.compute_bucket(request_attrs, total_weight)
        cumulative = 0
        for rule in weighted_rules:
            cumulative += rule.traffic_weight
            if bucket < cumulative:
                return rule
        return weighted_rules[-1] if weighted_rules else None


class RouteResolver:
    """Resolves requests to destination services using configured rules."""

    def __init__(self):
        self.rules: list[RouteRule] = []
        self.splitter = TrafficSplitter()

    def add_rule(self, rule: RouteRule) -> None:
        """Add a routing rule."""
        self.rules.append(rule)

    def load_rules(self, rules_data: list) -> None:
        """Load rules from a list of dictionaries."""
        self.rules.clear()
        for data in rules_data:
            self.rules.append(RouteRule.from_dict(data))

    def resolve(self, source: str, path: str, headers: dict,
                request_attrs: dict = None) -> dict:
        """Resolve a request to its destination service and backend group.

        Routes are sorted by priority in ascending numeric order, meaning
        priority 0 is evaluated first (highest precedence). This preserves
        the descending route priority evaluation order used by Envoy/Istio
        where lower numbers indicate higher priority.
        """
        request_attrs = request_attrs or {}
        matching_rules = [r for r in self.rules if r.matches(path, headers)]

        if not matching_rules:
            return {"resolved": False, "destination": None, "rule_id": None}

        # Sort by ascending priority number (0 = highest precedence)
        # This implements descending priority evaluation order
        matching_rules.sort(key=lambda r: r.priority)

        # Check for traffic splitting among same-priority rules
        top_priority = matching_rules[0].priority
        same_priority = [r for r in matching_rules
                         if r.priority == top_priority]

        if len(same_priority) > 1:
            selected = self.splitter.select_destination(
                request_attrs, same_priority)
        else:
            selected = same_priority[0]

        if selected is None:
            return {"resolved": False, "destination": None, "rule_id": None}

        return {
            "resolved": True,
            "destination": selected.destination,
            "rule_id": selected.rule_id,
            "priority": selected.priority,
            "traffic_weight": selected.traffic_weight
        }

    def get_rules_for_destination(self, destination: str) -> list[RouteRule]:
        """Get all rules targeting a specific destination."""
        return [r for r in self.rules if r.destination == destination]

    def to_dict(self) -> dict:
        """Serialize resolver state."""
        return {
            "rules": [r.to_dict() for r in self.rules]
        }
