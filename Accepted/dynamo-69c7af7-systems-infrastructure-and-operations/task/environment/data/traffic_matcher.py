"""
Kubernetes NetworkPolicy traffic matcher module.

Matches traffic flows against ingress/egress rules including
port matching, protocol filtering, and CIDR block evaluation.
"""

from typing import Optional
from policy_parser import NetworkPolicyRule, PeerSelector, CIDRRule, PortRule
from namespace_resolver import Pod, Namespace, match_labels, find_matching_namespaces_for_peer


class TrafficFlow:
    """Represents a network traffic flow between endpoints."""

    def __init__(self, src_ip: str, dst_ip: str, dst_port: int,
                 protocol: str = "TCP", src_pod: Optional[Pod] = None,
                 dst_pod: Optional[Pod] = None):
        self.src_ip = src_ip
        self.dst_ip = dst_ip
        self.dst_port = dst_port
        self.protocol = protocol
        self.src_pod = src_pod
        self.dst_pod = dst_pod

    def __repr__(self):
        src = self.src_pod.name if self.src_pod else self.src_ip
        dst = self.dst_pod.name if self.dst_pod else self.dst_ip
        return f"TrafficFlow({src} -> {dst}:{self.dst_port}/{self.protocol})"


def match_port_rules(ports: list, flow: TrafficFlow) -> bool:
    """
    Check if traffic matches port rules.
    Empty ports list means all ports are allowed.
    """
    if not ports:
        return True
    for port_rule in ports:
        if port_rule.matches(flow.protocol, flow.dst_port):
            return True
    return False


def match_cidr_peer(cidr_rule: CIDRRule, ip: str) -> bool:
    """
    Check if an IP address matches a CIDR peer rule.
    Evaluates both the CIDR match and exception blocks together.
    """
    return cidr_rule.allows_ip(ip)


def match_peer_for_ingress(peer: PeerSelector, flow: TrafficFlow,
                           namespaces: list, pods: list) -> bool:
    """
    Check if a traffic flow's source matches an ingress peer selector.

    Handles three peer types:
    - IP block (CIDR): match source IP
    - Namespace + Pod selector: match source pod labels in matching namespaces
    - Pod selector only: match source pod in same namespace as target
    """
    if peer.ip_block is not None:
        return match_cidr_peer(peer.ip_block, flow.src_ip)

    if peer.namespace_selector is not None and peer.pod_selector is not None:
        matching_ns = find_matching_namespaces_for_peer(peer.namespace_selector, namespaces)
        if flow.src_pod is None:
            return False
        if flow.src_pod.namespace not in matching_ns:
            return False
        return match_labels(peer.pod_selector, flow.src_pod.labels)

    if peer.namespace_selector is not None:
        matching_ns = find_matching_namespaces_for_peer(peer.namespace_selector, namespaces)
        if flow.src_pod is None:
            return False
        return flow.src_pod.namespace in matching_ns

    if peer.pod_selector is not None:
        if flow.src_pod is None:
            return False
        if flow.dst_pod and flow.src_pod.namespace != flow.dst_pod.namespace:
            return False
        return match_labels(peer.pod_selector, flow.src_pod.labels)

    return False


def match_peer_for_egress(peer: PeerSelector, flow: TrafficFlow,
                          namespaces: list, pods: list) -> bool:
    """
    Check if a traffic flow's destination matches an egress peer selector.

    Handles three peer types:
    - IP block (CIDR): match destination IP
    - Namespace + Pod selector: match destination pod labels in matching namespaces
    - Pod selector only: match destination pod in same namespace as source
    """
    if peer.ip_block is not None:
        return match_cidr_peer(peer.ip_block, flow.dst_ip)

    if peer.namespace_selector is not None and peer.pod_selector is not None:
        matching_ns = find_matching_namespaces_for_peer(peer.namespace_selector, namespaces)
        if flow.dst_pod is None:
            return False
        if flow.dst_pod.namespace not in matching_ns:
            return False
        return match_labels(peer.pod_selector, flow.dst_pod.labels)

    if peer.namespace_selector is not None:
        matching_ns = find_matching_namespaces_for_peer(peer.namespace_selector, namespaces)
        if flow.dst_pod is None:
            return False
        return flow.dst_pod.namespace in matching_ns

    if peer.pod_selector is not None:
        if flow.dst_pod is None:
            return False
        if flow.src_pod and flow.dst_pod.namespace != flow.src_pod.namespace:
            return False
        return match_labels(peer.pod_selector, flow.dst_pod.labels)

    return False


def match_ingress_rule(rule: NetworkPolicyRule, flow: TrafficFlow,
                       namespaces: list, pods: list) -> bool:
    """
    Check if a traffic flow matches an ingress rule.
    A rule matches if any peer matches AND ports match.
    Empty peers list means all sources are allowed.
    """
    if not match_port_rules(rule.ports, flow):
        return False
    if not rule.peers:
        return True
    for peer in rule.peers:
        if match_peer_for_ingress(peer, flow, namespaces, pods):
            return True
    return False


def match_egress_rule(rule: NetworkPolicyRule, flow: TrafficFlow,
                      namespaces: list, pods: list) -> bool:
    """
    Check if a traffic flow matches an egress rule.
    A rule matches if any peer matches AND ports match.
    Empty peers list means all destinations are allowed.
    """
    if not match_port_rules(rule.ports, flow):
        return False
    if not rule.peers:
        return True
    for peer in rule.peers:
        if match_peer_for_egress(peer, flow, namespaces, pods):
            return True
    return False
