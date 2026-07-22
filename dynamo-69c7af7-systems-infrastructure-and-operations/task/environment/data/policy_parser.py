"""
Kubernetes NetworkPolicy parser module.

Parses NetworkPolicy JSON definitions into internal policy objects
for evaluation by the policy engine.
"""

import json
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class PortRule:
    """Represents a port/protocol rule in a NetworkPolicy."""
    protocol: str = "TCP"
    port: Optional[int] = None
    end_port: Optional[int] = None

    def matches(self, protocol: str, port: int) -> bool:
        """Check if this rule matches the given protocol and port."""
        if self.protocol.upper() != protocol.upper():
            return False
        if self.port is None:
            return True
        if self.end_port is not None:
            return self.port <= port <= self.end_port
        return self.port == port


@dataclass
class CIDRRule:
    """Represents a CIDR block rule with optional exceptions."""
    cidr: str
    except_cidrs: list = field(default_factory=list)

    def _ip_to_int(self, ip: str) -> int:
        """Convert an IP address string to an integer."""
        parts = ip.split(".")
        return (int(parts[0]) << 24) + (int(parts[1]) << 16) + (int(parts[2]) << 8) + int(parts[3])

    def _cidr_contains(self, cidr: str, ip: str) -> bool:
        """Check if a CIDR block contains the given IP address."""
        network, prefix_len = cidr.split("/")
        prefix_len = int(prefix_len)
        mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
        network_int = self._ip_to_int(network) & mask
        ip_int = self._ip_to_int(ip)
        return (ip_int & mask) == network_int

    def matches_cidr(self, ip: str) -> bool:
        """Check if IP matches the CIDR block (without exception handling)."""
        return self._cidr_contains(self.cidr, ip)

    def is_excepted(self, ip: str) -> bool:
        """Check if IP falls within any exception CIDR blocks."""
        for except_cidr in self.except_cidrs:
            if self._cidr_contains(except_cidr, ip):
                return True
        return False

    def allows_ip(self, ip: str) -> bool:
        """Full evaluation: matches CIDR and not in exceptions."""
        if not self.matches_cidr(ip):
            return False
        if self.is_excepted(ip):
            return False
        return True


@dataclass
class PeerSelector:
    """Represents a peer selector in ingress/egress rules."""
    pod_selector: Optional[dict] = None
    namespace_selector: Optional[dict] = None
    ip_block: Optional[CIDRRule] = None


@dataclass
class NetworkPolicyRule:
    """Represents a single ingress or egress rule."""
    peers: list = field(default_factory=list)
    ports: list = field(default_factory=list)


@dataclass
class NetworkPolicy:
    """Internal representation of a Kubernetes NetworkPolicy."""
    name: str
    namespace: str
    creation_timestamp: str
    pod_selector: dict = field(default_factory=dict)
    policy_types: list = field(default_factory=list)
    ingress_rules: list = field(default_factory=list)
    egress_rules: list = field(default_factory=list)


def parse_port_rule(port_data: dict) -> PortRule:
    """Parse a port rule from JSON data."""
    return PortRule(
        protocol=port_data.get("protocol", "TCP"),
        port=port_data.get("port"),
        end_port=port_data.get("endPort")
    )


def parse_cidr_rule(ip_block_data: dict) -> CIDRRule:
    """Parse a CIDR rule from JSON data."""
    return CIDRRule(
        cidr=ip_block_data["cidr"],
        except_cidrs=ip_block_data.get("except", [])
    )


def parse_peer_selector(peer_data: dict) -> PeerSelector:
    """Parse a peer selector from JSON data."""
    peer = PeerSelector()
    if "podSelector" in peer_data:
        peer.pod_selector = peer_data["podSelector"].get("matchLabels", {})
    if "namespaceSelector" in peer_data:
        peer.namespace_selector = peer_data["namespaceSelector"].get("matchLabels", {})
    if "ipBlock" in peer_data:
        peer.ip_block = parse_cidr_rule(peer_data["ipBlock"])
    return peer


def parse_rule(rule_data: dict) -> NetworkPolicyRule:
    """Parse an ingress or egress rule from JSON data."""
    rule = NetworkPolicyRule()
    for peer_data in rule_data.get("from", rule_data.get("to", [])):
        rule.peers.append(parse_peer_selector(peer_data))
    for port_data in rule_data.get("ports", []):
        rule.ports.append(parse_port_rule(port_data))
    return rule


def parse_policy(policy_data: dict) -> NetworkPolicy:
    """Parse a complete NetworkPolicy from JSON data."""
    metadata = policy_data["metadata"]
    spec = policy_data["spec"]

    policy = NetworkPolicy(
        name=metadata["name"],
        namespace=metadata["namespace"],
        creation_timestamp=metadata["creationTimestamp"],
        pod_selector=spec.get("podSelector", {}).get("matchLabels", {}),
        policy_types=spec.get("policyTypes", [])
    )

    for ingress_data in spec.get("ingress", []):
        policy.ingress_rules.append(parse_rule(ingress_data))

    for egress_data in spec.get("egress", []):
        policy.egress_rules.append(parse_rule(egress_data))

    return policy


def parse_policies(policies_data: list) -> list:
    """Parse a list of NetworkPolicy JSON objects into internal representations."""
    policies = []
    for policy_data in policies_data:
        try:
            parsed = parse_policy(policy_data)
            policies.append(parsed)
        except (KeyError, TypeError) as e:
            raise ValueError(f"Invalid policy format: {e}")
    return policies


def load_policies_from_config(config: dict) -> list:
    """Load and parse policies from a configuration dictionary."""
    raw_policies = config.get("policies", [])
    return parse_policies(raw_policies)
