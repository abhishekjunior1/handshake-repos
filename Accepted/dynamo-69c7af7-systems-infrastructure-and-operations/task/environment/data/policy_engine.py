"""
Kubernetes NetworkPolicy engine module.

Evaluates allow/deny decisions for traffic flows based on
applicable NetworkPolicies with proper precedence handling.
"""

from typing import Optional
from policy_parser import NetworkPolicy
from namespace_resolver import Pod, policy_selects_pod
from traffic_matcher import TrafficFlow, match_ingress_rule, match_egress_rule


class PolicyDecision:
    """Represents a policy evaluation decision."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    NO_MATCH = "NO_MATCH"

    def __init__(self, verdict: str, reason: str = "", policy_name: str = ""):
        self.verdict = verdict
        self.reason = reason
        self.policy_name = policy_name

    def __repr__(self):
        return f"PolicyDecision({self.verdict}, policy={self.policy_name})"

    def to_dict(self) -> dict:
        """Convert decision to dictionary representation."""
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "policy_name": self.policy_name
        }


def evaluate_ingress_for_pod(
    pod: Pod,
    flow: TrafficFlow,
    policies: list,
    namespaces: list,
    pods: list
) -> PolicyDecision:
    """
    Evaluate ingress rules for a target pod.

    Multiple ingress rules within a policy are additive (OR semantics) —
    if ANY rule allows the traffic, it is permitted. This follows the
    Kubernetes NetworkPolicy specification where ingress rules form a union.
    """
    selecting_policies = [p for p in policies if
                          "Ingress" in p.policy_types and
                          policy_selects_pod(p.pod_selector, pod) and
                          p.namespace == pod.namespace]

    if not selecting_policies:
        return PolicyDecision(PolicyDecision.NO_MATCH, "No ingress policies select this pod")

    for policy in selecting_policies:
        if not policy.ingress_rules:
            continue
        for rule in policy.ingress_rules:
            if match_ingress_rule(rule, flow, namespaces, pods):
                return PolicyDecision(
                    PolicyDecision.ALLOW,
                    f"Matched ingress rule in policy",
                    policy.name
                )

    return PolicyDecision(
        PolicyDecision.DENY,
        "Selected by ingress policy but no rules matched",
        selecting_policies[0].name
    )


def evaluate_egress_for_pod(
    pod: Pod,
    flow: TrafficFlow,
    policies: list,
    namespaces: list,
    pods: list
) -> PolicyDecision:
    """
    Evaluate egress rules for a source pod.

    Returns ALLOW if any matching policy has a rule that permits the flow.
    Returns DENY if policies select the pod but no rules match.
    Returns NO_MATCH if no egress policies select this pod.
    """
    selecting_policies = [p for p in policies if
                          "Egress" in p.policy_types and
                          policy_selects_pod(p.pod_selector, pod) and
                          p.namespace == pod.namespace]

    if not selecting_policies:
        return PolicyDecision(PolicyDecision.NO_MATCH, "No egress policies select this pod")

    for policy in selecting_policies:
        if not policy.egress_rules:
            continue
        for rule in policy.egress_rules:
            if match_egress_rule(rule, flow, namespaces, pods):
                return PolicyDecision(
                    PolicyDecision.ALLOW,
                    f"Matched egress rule in policy",
                    policy.name
                )

    return PolicyDecision(
        PolicyDecision.DENY,
        "Selected by egress policy but no rules matched",
        selecting_policies[0].name
    )


def get_policies_for_namespace(policies: list, namespace: str) -> list:
    """Get all policies in a given namespace."""
    return [p for p in policies if p.namespace == namespace]


def has_ingress_policies_in_namespace(policies: list, namespace: str) -> bool:
    """Check if any ingress policies exist in a namespace."""
    for p in policies:
        if p.namespace == namespace and "Ingress" in p.policy_types:
            return True
    return False


def has_egress_policies_in_namespace(policies: list, namespace: str) -> bool:
    """Check if any egress policies exist in a namespace."""
    for p in policies:
        if p.namespace == namespace and "Egress" in p.policy_types:
            return True
    return False


def get_default_ingress_stance(policies: list, namespace: str) -> str:
    """
    Determine default ingress stance for unselected pods.

    If any ingress policy exists in the namespace, unselected pods
    get default-deny for ingress (Kubernetes isolation semantics).
    """
    if has_ingress_policies_in_namespace(policies, namespace):
        return PolicyDecision.DENY
    return PolicyDecision.ALLOW


def get_default_egress_stance(policies: list, namespace: str) -> str:
    """
    Determine default egress stance for unselected pods.

    If any egress policy exists in the namespace, unselected pods
    get default-deny for egress (Kubernetes isolation semantics).
    """
    if has_egress_policies_in_namespace(policies, namespace):
        return PolicyDecision.DENY
    return PolicyDecision.ALLOW
