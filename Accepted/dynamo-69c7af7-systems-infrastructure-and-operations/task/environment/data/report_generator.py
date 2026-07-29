"""
Kubernetes NetworkPolicy report generator module.

Formats evaluation results into structured output for
reporting and analysis.
"""

import json
from typing import Optional


class EvaluationResult:
    """Stores a single traffic evaluation result."""

    def __init__(self, flow_id: str, src: str, dst: str, port: int,
                 protocol: str, ingress_verdict: str, egress_verdict: str,
                 final_verdict: str, reason: str = "",
                 ingress_policy: str = "", egress_policy: str = ""):
        self.flow_id = flow_id
        self.src = src
        self.dst = dst
        self.port = port
        self.protocol = protocol
        self.ingress_verdict = ingress_verdict
        self.egress_verdict = egress_verdict
        self.final_verdict = final_verdict
        self.reason = reason
        self.ingress_policy = ingress_policy
        self.egress_policy = egress_policy

    def to_dict(self) -> dict:
        """Convert result to dictionary."""
        return {
            "flow_id": self.flow_id,
            "source": self.src,
            "destination": self.dst,
            "port": self.port,
            "protocol": self.protocol,
            "ingress_verdict": self.ingress_verdict,
            "egress_verdict": self.egress_verdict,
            "final_verdict": self.final_verdict,
            "reason": self.reason,
            "ingress_policy": self.ingress_policy,
            "egress_policy": self.egress_policy
        }


class EvaluationReport:
    """Collects and formats evaluation results into a report."""

    def __init__(self, config_name: str = ""):
        self.config_name = config_name
        self.results = []
        self.summary = {}
        self.connection_stats = {}

    def add_result(self, result: EvaluationResult):
        """Add an evaluation result to the report."""
        self.results.append(result)

    def compute_summary(self):
        """Compute summary statistics from results."""
        total = len(self.results)
        allowed = sum(1 for r in self.results if r.final_verdict == "ALLOW")
        denied = sum(1 for r in self.results if r.final_verdict == "DENY")

        self.summary = {
            "total_flows_evaluated": total,
            "allowed": allowed,
            "denied": denied,
            "allow_rate": round(allowed / total, 4) if total > 0 else 0.0
        }

    def set_connection_stats(self, stats: dict):
        """Set connection tracker statistics."""
        self.connection_stats = stats

    def generate(self) -> dict:
        """Generate the complete evaluation report."""
        self.compute_summary()
        return {
            "config_name": self.config_name,
            "summary": self.summary,
            "connection_stats": self.connection_stats,
            "evaluations": [r.to_dict() for r in self.results]
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string."""
        return json.dumps(self.generate(), indent=indent, sort_keys=True)


def format_verdict(ingress_verdict: str, egress_verdict: str) -> str:
    """
    Compute final verdict from ingress and egress decisions.
    Both must allow for traffic to pass.
    """
    if ingress_verdict == "DENY" or egress_verdict == "DENY":
        return "DENY"
    return "ALLOW"


def build_result(flow_id: str, flow_info: dict,
                 ingress_decision: dict, egress_decision: dict) -> EvaluationResult:
    """Build an EvaluationResult from flow info and decisions."""
    final = format_verdict(ingress_decision["verdict"], egress_decision["verdict"])

    reasons = []
    if ingress_decision.get("reason"):
        reasons.append(f"ingress: {ingress_decision['reason']}")
    if egress_decision.get("reason"):
        reasons.append(f"egress: {egress_decision['reason']}")

    return EvaluationResult(
        flow_id=flow_id,
        src=flow_info["src"],
        dst=flow_info["dst"],
        port=flow_info["port"],
        protocol=flow_info["protocol"],
        ingress_verdict=ingress_decision["verdict"],
        egress_verdict=egress_decision["verdict"],
        final_verdict=final,
        reason="; ".join(reasons),
        ingress_policy=ingress_decision.get("policy_name", ""),
        egress_policy=egress_decision.get("policy_name", "")
    )
