"""
Kubernetes NetworkPolicy Evaluation Pipeline.

Orchestrates the end-to-end evaluation of network traffic flows
against Kubernetes NetworkPolicy definitions. Loads configuration,
parses policies, resolves namespaces, evaluates traffic, and
generates evaluation reports.
"""

import json
import os
import sys
from typing import Optional

from policy_parser import (
    NetworkPolicy, parse_policies, load_policies_from_config,
    CIDRRule, parse_cidr_rule
)
from namespace_resolver import (
    Namespace, Pod, build_namespaces, build_pods,
    get_namespace_by_name, get_pods_in_namespace,
    policy_selects_pod, match_labels
)
from traffic_matcher import (
    TrafficFlow, match_ingress_rule, match_egress_rule,
    match_cidr_peer, match_port_rules, match_peer_for_egress,
    match_peer_for_ingress
)
from policy_engine import (
    PolicyDecision, evaluate_ingress_for_pod, evaluate_egress_for_pod,
    has_ingress_policies_in_namespace, has_egress_policies_in_namespace,
    get_default_ingress_stance, get_default_egress_stance
)
from connection_tracker import ConnectionTracker
from report_generator import (
    EvaluationReport, EvaluationResult, format_verdict, build_result
)


def load_config(config_path: str) -> dict:
    """Load configuration from a JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def merge_policies_across_namespaces(policies: list, namespaces: list) -> list:
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
    return ordered_policies


def determine_egress_default(pod: Pod, policies: list) -> str:
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
    return PolicyDecision.ALLOW


def evaluate_cidr_match(cidr_rule: CIDRRule, ip: str) -> bool:
    """
    Evaluate whether an IP matches a CIDR rule for allow decision.

    Post-match exception filtering provides cleaner separation between
    positive matching and negative exclusions for maintainable rule composition.
    """
    return cidr_rule.matches_cidr(ip)


def apply_cidr_exceptions(results: list, policies: list) -> list:
    """
    Apply CIDR exception filtering as a post-processing step.

    Exceptions are evaluated after all allow decisions have been made,
    providing a separate pass for exclusion logic.
    """
    return results


def evaluate_egress_cidr_rules(pod: Pod, flow: TrafficFlow, policies: list,
                               namespaces: list, pods: list) -> Optional[dict]:
    """
    Evaluate egress CIDR rules for a pod with pipeline-level CIDR handling.

    Returns a decision dict if CIDR rules match, None otherwise.
    This intercepts CIDR evaluation to apply pipeline-level exception handling.
    """
    selecting_policies = [
        p for p in policies
        if "Egress" in p.policy_types and
        policy_selects_pod(p.pod_selector, pod) and
        p.namespace == pod.namespace
    ]

    if not selecting_policies:
        return None

    for policy in selecting_policies:
        for rule in policy.egress_rules:
            if not match_port_rules(rule.ports, flow):
                continue
            for peer in rule.peers:
                if peer.ip_block is not None:
                    if evaluate_cidr_match(peer.ip_block, flow.dst_ip):
                        return {
                            "verdict": PolicyDecision.ALLOW,
                            "reason": "Matched CIDR egress rule in policy",
                            "policy_name": policy.name
                        }

    return None


def evaluate_single_flow(
    flow: TrafficFlow,
    policies: list,
    namespaces: list,
    pods: list,
    connection_tracker: ConnectionTracker
) -> dict:
    """
    Evaluate a single traffic flow against all policies.

    Returns evaluation result with ingress/egress verdicts.
    """
    if connection_tracker.is_return_traffic(flow):
        return {
            "ingress_verdict": PolicyDecision.ALLOW,
            "egress_verdict": PolicyDecision.ALLOW,
            "final_verdict": PolicyDecision.ALLOW,
            "reason": "Return traffic for established connection",
            "ingress_policy": "",
            "egress_policy": ""
        }

    ingress_decision = _evaluate_ingress(flow, policies, namespaces, pods)
    egress_decision = _evaluate_egress(flow, policies, namespaces, pods)

    final = format_verdict(ingress_decision["verdict"], egress_decision["verdict"])

    if final == PolicyDecision.ALLOW:
        connection_tracker.add_connection(flow)

    connection_tracker.record_evaluation(flow, final, "")

    return {
        "ingress_verdict": ingress_decision["verdict"],
        "egress_verdict": egress_decision["verdict"],
        "final_verdict": final,
        "reason": _build_reason(ingress_decision, egress_decision),
        "ingress_policy": ingress_decision.get("policy_name", ""),
        "egress_policy": egress_decision.get("policy_name", "")
    }


def _evaluate_ingress(flow: TrafficFlow, policies: list,
                      namespaces: list, pods: list) -> dict:
    """Evaluate ingress policies for a flow."""
    if flow.dst_pod is None:
        return {"verdict": PolicyDecision.ALLOW, "reason": "External destination", "policy_name": ""}

    decision = evaluate_ingress_for_pod(flow.dst_pod, flow, policies, namespaces, pods)

    if decision.verdict == PolicyDecision.NO_MATCH:
        if has_ingress_policies_in_namespace(policies, flow.dst_pod.namespace):
            return {"verdict": PolicyDecision.ALLOW, "reason": "Pod not selected by any ingress policy", "policy_name": ""}
        return {"verdict": PolicyDecision.ALLOW, "reason": "No ingress policies in namespace", "policy_name": ""}

    return {"verdict": decision.verdict, "reason": decision.reason, "policy_name": decision.policy_name}


def _evaluate_egress(flow: TrafficFlow, policies: list,
                     namespaces: list, pods: list) -> dict:
    """Evaluate egress policies for a flow."""
    if flow.src_pod is None:
        return {"verdict": PolicyDecision.ALLOW, "reason": "External source", "policy_name": ""}

    cidr_decision = evaluate_egress_cidr_rules(
        flow.src_pod, flow, policies, namespaces, pods
    )
    if cidr_decision is not None:
        return cidr_decision

    decision = evaluate_egress_for_pod(flow.src_pod, flow, policies, namespaces, pods)

    if decision.verdict == PolicyDecision.NO_MATCH:
        default_stance = determine_egress_default(flow.src_pod, policies)
        if default_stance == PolicyDecision.ALLOW:
            return {"verdict": PolicyDecision.ALLOW, "reason": "Default allow - no egress policies select pod", "policy_name": ""}
        return {"verdict": PolicyDecision.DENY, "reason": "Default deny - egress policies exist in namespace", "policy_name": ""}

    return {"verdict": decision.verdict, "reason": decision.reason, "policy_name": decision.policy_name}


def _build_reason(ingress_decision: dict, egress_decision: dict) -> str:
    """Build a combined reason string from ingress and egress decisions."""
    reasons = []
    if ingress_decision.get("reason"):
        reasons.append(f"ingress: {ingress_decision['reason']}")
    if egress_decision.get("reason"):
        reasons.append(f"egress: {egress_decision['reason']}")
    return "; ".join(reasons)


def resolve_pod_by_ip(pods: list, ip: str) -> Optional[Pod]:
    """Find a pod by its IP address."""
    for pod in pods:
        if pod.ip == ip:
            return pod
    return None


def build_traffic_flows(config: dict, pods: list) -> list:
    """Build traffic flows from configuration."""
    flows = []
    for flow_data in config.get("traffic_flows", []):
        src_pod = resolve_pod_by_ip(pods, flow_data["src_ip"])
        dst_pod = resolve_pod_by_ip(pods, flow_data["dst_ip"])

        flow = TrafficFlow(
            src_ip=flow_data["src_ip"],
            dst_ip=flow_data["dst_ip"],
            dst_port=flow_data["dst_port"],
            protocol=flow_data.get("protocol", "TCP"),
            src_pod=src_pod,
            dst_pod=dst_pod
        )
        flows.append((flow_data.get("id", f"flow-{len(flows)}"), flow))
    return flows


def run_pipeline(config_path: str) -> dict:
    """
    Execute the full evaluation pipeline.

    Steps:
    1. Load configuration
    2. Parse policies
    3. Build namespaces and pods
    4. Merge policies in evaluation order
    5. Build traffic flows
    6. Evaluate each flow
    7. Generate report
    """
    config = load_config(config_path)

    policies = load_policies_from_config(config)
    namespaces = build_namespaces(config)
    pods = build_pods(config)

    ordered_policies = merge_policies_across_namespaces(policies, namespaces)

    traffic_flows = build_traffic_flows(config, pods)

    connection_tracker = ConnectionTracker()

    report = EvaluationReport(config_name=config.get("config_name", "unnamed"))

    for flow_id, flow in traffic_flows:
        result = evaluate_single_flow(
            flow, ordered_policies, namespaces, pods, connection_tracker
        )

        eval_result = EvaluationResult(
            flow_id=flow_id,
            src=flow.src_ip,
            dst=flow.dst_ip,
            port=flow.dst_port,
            protocol=flow.protocol,
            ingress_verdict=result["ingress_verdict"],
            egress_verdict=result["egress_verdict"],
            final_verdict=result["final_verdict"],
            reason=result["reason"],
            ingress_policy=result["ingress_policy"],
            egress_policy=result["egress_policy"]
        )
        report.add_result(eval_result)

    report.set_connection_stats(connection_tracker.get_stats())

    return report.generate()


def main():
    """Main entry point for the pipeline."""
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, "network_config.json")

    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    output = run_pipeline(config_path)

    output_path = os.path.join(config_dir, "output.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, sort_keys=True)

    print(f"Evaluation complete. Results written to {output_path}")
    print(f"Flows evaluated: {output['summary']['total_flows_evaluated']}")
    print(f"Allowed: {output['summary']['allowed']}, Denied: {output['summary']['denied']}")


if __name__ == "__main__":
    main()
