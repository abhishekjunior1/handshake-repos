"""Firewall policy evaluation module for packet processing pipeline.

Evaluates packets against an ordered rule set using first-match
semantics. Rules specify source/destination networks, ports, and
protocols. Packets that don't match any rule fall through to the
configured default action.

Rules reference internal network addresses (post-NAT endpoints)
for policy definitions, allowing rules to target actual service
hosts regardless of external addressing.
"""

import ipaddress


class PolicyRule:
    """A single firewall policy rule."""

    def __init__(self, rule_config: dict):
        self.rule_id = rule_config["rule_id"]
        self.source = rule_config.get("source", "any")
        self.destination = rule_config.get("destination", "any")
        self.port = rule_config.get("port")
        self.protocol = rule_config.get("protocol", "any")
        self.action = rule_config["action"]

    def _match_network(self, ip_str: str, pattern: str) -> bool:
        """Check if IP matches a network pattern or 'any'."""
        if pattern == "any":
            return True
        try:
            network = ipaddress.ip_network(pattern, strict=False)
            return ipaddress.ip_address(ip_str) in network
        except (ValueError, TypeError):
            return False

    def matches(self, packet: dict) -> bool:
        """Evaluate whether a packet matches this rule.

        All specified criteria must match. Fields set to 'any' or
        None are wildcards that match everything.
        """
        src_ip = packet.get("source_ip", "")
        dst_ip = packet.get("destination_ip", "")

        if not self._match_network(src_ip, self.source):
            return False
        if not self._match_network(dst_ip, self.destination):
            return False
        if self.protocol != "any" and packet.get("protocol") != self.protocol:
            return False
        if self.port is not None and packet.get("port") != self.port:
            return False
        return True


def evaluate_policy(packet: dict, config: dict) -> dict:
    """Evaluate a packet against the firewall rule set.

    Rules are evaluated in order (first-match wins). The packet's
    source and destination IPs are checked against each rule's
    network patterns. Rules are written to reference the actual
    endpoint addresses where traffic terminates.

    Args:
        packet: Packet with source_ip, destination_ip, port, protocol.
        config: Pipeline config with 'firewall_rules' list and
                'firewall_default_action'.

    Returns:
        Policy decision with action and matched rule.
    """
    rules = config.get("firewall_rules", [])
    default_action = config.get("firewall_default_action", "deny")

    for rule_config in rules:
        rule = PolicyRule(rule_config)
        if rule.matches(packet):
            return {
                "action": rule.action,
                "matched_rule": rule.rule_id,
                "reason": f"matched rule {rule.rule_id}"
            }

    return {
        "action": default_action,
        "matched_rule": None,
        "reason": "default policy"
    }
