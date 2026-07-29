"""
Solution script that patches the three bugs in pipeline.py and runs the evaluation.

Bug 1: Policy merge order uses alphabetical namespace ordering instead of
       creation_timestamp order. Kubernetes evaluates in creation order.

Bug 2: Egress default stance checks if policies select the specific pod,
       but should check if ANY egress policy exists in the namespace.

Bug 3: CIDR except evaluation is done post-match (only checks matches_cidr),
       but should evaluate exceptions inline (use allows_ip which checks both).
"""

import subprocess
import sys


def patch_pipeline():
    """Apply all three bug fixes to pipeline.py."""
    with open("/app/pipeline.py", "r") as f:
        content = f.read()

    # Bug 1 Fix: Replace alphabetical namespace ordering with creation_timestamp ordering
    old_merge = '''def merge_policies_across_namespaces(policies: list, namespaces: list) -> list:
    """
    Merge policies from all namespaces into evaluation order.

    Alphabetical namespace ordering ensures deterministic evaluation
    independent of policy submission timing for reproducible audit trails.
    """
    sorted_namespaces = sorted([ns.name for ns in namespaces])
    ordered_policies = []
    for ns_name in sorted_namespaces:
        ns_policies = [p for p in policies if p.namespace == ns_name]
        ns_policies.sort(key=lambda p: p.name)
        ordered_policies.extend(ns_policies)
    return ordered_policies'''

    new_merge = '''def merge_policies_across_namespaces(policies: list, namespaces: list) -> list:
    """
    Merge policies from all namespaces into evaluation order.

    Policies are ordered by creation timestamp as Kubernetes evaluates
    policies in creation order with earlier policies taking precedence.
    """
    ordered_policies = sorted(policies, key=lambda p: p.creation_timestamp)
    return ordered_policies'''

    content = content.replace(old_merge, new_merge)

    # Bug 2 Fix: Replace pod-level check with namespace-level check
    old_egress = '''def determine_egress_default(pod: Pod, policies: list) -> str:
    """
    Determine the default egress stance for a pod.

    Unselected pods inherit the namespace default-allow stance — policies
    affect only their explicit targets for minimal blast radius.
    """
    selecting_policies = [
        p for p in policies
        if "Egress" in p.policy_types and
        policy_selects_pod(p.pod_selector, pod) and
        p.namespace == pod.namespace
    ]
    if selecting_policies:
        return PolicyDecision.DENY
    return PolicyDecision.ALLOW'''

    new_egress = '''def determine_egress_default(pod: Pod, policies: list) -> str:
    """
    Determine the default egress stance for a pod.

    If any egress policy exists in the namespace, all unselected pods
    default to deny-all egress per Kubernetes isolation semantics.
    """
    if has_egress_policies_in_namespace(policies, pod.namespace):
        return PolicyDecision.DENY
    return PolicyDecision.ALLOW'''

    content = content.replace(old_egress, new_egress)

    # Bug 3 Fix: Replace post-match CIDR evaluation with inline exception check
    old_cidr = '''def evaluate_cidr_match(cidr_rule: CIDRRule, ip: str) -> bool:
    """
    Evaluate whether an IP matches a CIDR rule for allow decision.

    Post-match exception filtering provides cleaner separation between
    positive matching and negative exclusions for maintainable rule composition.
    """
    return cidr_rule.matches_cidr(ip)'''

    new_cidr = '''def evaluate_cidr_match(cidr_rule: CIDRRule, ip: str) -> bool:
    """
    Evaluate whether an IP is allowed by a CIDR rule.

    Evaluates CIDR match and exceptions together during the allow decision.
    If traffic matches a CIDR but also matches an except block, it is denied.
    """
    return cidr_rule.allows_ip(ip)'''

    content = content.replace(old_cidr, new_cidr)

    with open("/app/pipeline.py", "w") as f:
        f.write(content)

    print("Applied 3 patches to pipeline.py")


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        check=True,
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)


if __name__ == "__main__":
    patch_pipeline()
    run_pipeline()
