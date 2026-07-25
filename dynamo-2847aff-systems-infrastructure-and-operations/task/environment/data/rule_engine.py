"""Firewall rule evaluation engine with CIDR matching and port range support."""

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class RuleMatch:
    """Result of a rule evaluation against a packet."""

    matched: bool
    rule_name: str = ""
    action: str = "deny"


@dataclass
class FirewallRule:
    """Single firewall rule with match criteria and action."""

    name: str
    action: str
    src_cidr: str = "0.0.0.0/0"
    dst_cidr: str = "0.0.0.0/0"
    src_port_min: int = 0
    src_port_max: int = 65535
    dst_port_min: int = 0
    dst_port_max: int = 65535
    protocol: str = "any"
    enabled: bool = True

    def matches(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, protocol: str) -> bool:
        """Evaluate whether this rule matches the given packet tuple."""
        if not self.enabled:
            return False
        if not cidr_match(src_ip, self.src_cidr):
            return False
        if not cidr_match(dst_ip, self.dst_cidr):
            return False
        if not port_in_range(src_port, self.src_port_min, self.src_port_max):
            return False
        if not port_in_range(dst_port, self.dst_port_min, self.dst_port_max):
            return False
        if self.protocol != "any" and self.protocol.lower() != protocol.lower():
            return False
        return True


def ip_to_int(ip: str) -> int:
    """Convert dotted-quad IP address to 32-bit integer."""
    octets = ip.split(".")
    result = 0
    for octet in octets:
        result = (result << 8) | int(octet)
    return result


def cidr_match(ip: str, cidr: str) -> bool:
    """Check if an IP address matches a CIDR notation network."""
    if cidr == "0.0.0.0/0" or cidr == "any":
        return True
    if "/" not in cidr:
        return ip == cidr
    network, prefix_str = cidr.split("/")
    prefix_len = int(prefix_str)
    if prefix_len == 0:
        return True
    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
    ip_int = ip_to_int(ip)
    net_int = ip_to_int(network)
    return (ip_int & mask) == (net_int & mask)


def port_in_range(port: int, port_min: int, port_max: int) -> bool:
    """Check if a port number falls within the specified range."""
    return port_min <= port <= port_max


def parse_rule(rule_def: dict) -> FirewallRule:
    """Parse a rule definition dictionary into a FirewallRule object."""
    src_port_range = rule_def.get("src_port_range", [0, 65535])
    dst_port_range = rule_def.get("dst_port_range", [0, 65535])

    return FirewallRule(
        name=rule_def["name"],
        action=rule_def["action"],
        src_cidr=rule_def.get("src_cidr", "0.0.0.0/0"),
        dst_cidr=rule_def.get("dst_cidr", "0.0.0.0/0"),
        src_port_min=src_port_range[0],
        src_port_max=src_port_range[1],
        dst_port_min=dst_port_range[0],
        dst_port_max=dst_port_range[1],
        protocol=rule_def.get("protocol", "any"),
        enabled=rule_def.get("enabled", True),
    )


def parse_ruleset(rules_config: List[dict]) -> List[FirewallRule]:
    """Parse a list of rule definitions into FirewallRule objects."""
    rules = []
    for rule_def in rules_config:
        rules.append(parse_rule(rule_def))
    return rules


def evaluate_rules(
    rules: List[FirewallRule],
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    protocol: str,
) -> RuleMatch:
    """Evaluate packet against rule list using zone-based first-match semantics.

    Returns the action of the first matching rule. If no rule matches,
    returns a deny action (implicit deny at end of ruleset).
    """
    # zone-based first-match semantics
    for rule in rules:
        if rule.matches(src_ip, dst_ip, src_port, dst_port, protocol):
            return RuleMatch(matched=True, rule_name=rule.name, action=rule.action)

    return RuleMatch(matched=False, rule_name="implicit-deny", action="deny")


def evaluate_packet_tuple(
    rules: List[FirewallRule], packet_tuple: Tuple[str, str, int, int, str]
) -> RuleMatch:
    """Convenience wrapper to evaluate a 5-tuple packet against rules."""
    src_ip, dst_ip, src_port, dst_port, protocol = packet_tuple
    return evaluate_rules(rules, src_ip, dst_ip, src_port, dst_port, protocol)
