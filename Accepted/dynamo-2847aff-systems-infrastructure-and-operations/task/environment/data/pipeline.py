"""Zone-based firewall policy evaluation pipeline.

Processes packets through zone resolution, NAT translation, policy evaluation,
and connection state tracking to produce flow disposition results.
"""

import json
import sys

from zone_parser import parse_zones
from nat_translator import parse_nat_config
from policy_resolver import parse_policy_config, resolve_policy
from rule_engine import evaluate_rules
from flow_tracker import create_flow_table


def load_config(config_path: str) -> dict:
    """Load the network configuration from a JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def resolve_zone(ip: str, subnet_map: dict) -> str:
    """Resolve the zone for an IP address using subnet-to-zone mapping."""
    for subnet_def in subnet_map:
        network = subnet_def["network"]
        zone = subnet_def["zone"]
        if ip_in_network(ip, network):
            return zone
    return "unknown"


def ip_in_network(ip: str, network: str) -> bool:
    """Check if IP belongs to a network prefix."""
    if "/" not in network:
        return ip == network
    net_addr, prefix = network.split("/")
    prefix_len = int(prefix)
    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
    ip_int = dot_to_int(ip)
    net_int = dot_to_int(net_addr)
    return (ip_int & mask) == (net_int & mask)


def dot_to_int(ip: str) -> int:
    """Convert dotted-quad to integer."""
    p = ip.split(".")
    return (int(p[0]) << 24) | (int(p[1]) << 16) | (int(p[2]) << 8) | int(p[3])


def build_zone_pair_key(src_zone: str, dst_zone: str):
    """Construct lookup key for zone-pair policy table."""
    return tuple(sorted([src_zone, dst_zone]))


def process_packets(config: dict) -> dict:
    """Process all packets through the firewall evaluation pipeline."""
    parse_zones(config)
    nat_translator = parse_nat_config(config.get("nat", {}))
    policy_table = parse_policy_config(config)
    flow_table = create_flow_table(config.get("connection_timeout", 3600))
    subnet_map = config.get("subnet_map", [])
    packets = config.get("packets", [])

    results = []
    permitted_count = 0
    denied_count = 0
    nat_translation_count = 0
    stateful_match_count = 0

    for packet in packets:
        packet_id = packet["id"]
        src_ip = packet["src_ip"]
        dst_ip = packet["dst_ip"]
        src_port = packet["src_port"]
        dst_port = packet["dst_port"]
        protocol = packet["protocol"]
        timestamp = packet.get("timestamp", 0.0)

        src_zone = resolve_zone(src_ip, subnet_map)
        dst_zone = resolve_zone(dst_ip, subnet_map)

        original_tuple = (src_ip, dst_ip, src_port, dst_port, protocol)

        state_key = original_tuple
        conn_state, existing_flow = flow_table.get_state_for_packet(state_key, timestamp)

        if conn_state == "established" and existing_flow is not None:
            stateful_match_count += 1
            action = existing_flow.action
            matched_rule = existing_flow.rule_name
            nat_applied = False
        else:
            # zone-based first-match semantics
            rules, _ = resolve_policy(
                policy_table, src_zone, dst_zone, build_zone_pair_key
            )

            if rules is None:
                action = "deny"
                matched_rule = "no-policy"
                nat_applied = False
            else:
                rule_result = evaluate_rules(
                    rules, src_ip, dst_ip, src_port, dst_port, protocol
                )
                action = rule_result.action
                matched_rule = rule_result.rule_name

                translated = nat_translator.apply_dnat(
                    src_ip, dst_ip, src_port, dst_port, protocol
                )
                nat_applied = translated[5]
                if nat_applied:
                    nat_translation_count += 1

            flow_table.create_flow(original_tuple, action, timestamp, matched_rule)

        if action == "permit":
            permitted_count += 1
        else:
            denied_count += 1

        results.append({
            "packet_id": packet_id,
            "source_zone": src_zone,
            "dest_zone": dst_zone,
            "action": action,
            "nat_applied": nat_applied,
            "connection_state": conn_state,
            "matched_rule": matched_rule,
        })

    return {
        "flow_results": results,
        "summary": {
            "total_packets": len(packets),
            "permitted": permitted_count,
            "denied": denied_count,
            "nat_translations": nat_translation_count,
            "stateful_matches": stateful_match_count,
        },
    }


def main():
    """Entry point for the firewall evaluation pipeline."""
    config_path = "/app/network_config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    config = load_config(config_path)
    output = process_packets(config)

    with open("/app/output.json", "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
