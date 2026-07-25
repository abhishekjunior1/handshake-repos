"""Network packet processing pipeline.

Processes packets through a multi-stage forwarding pipeline:
1. DNS resolution (hostname -> IP address)
2. Firewall policy evaluation (allow/deny)
3. NAT translation (destination address rewriting)
4. Route selection (next-hop determination)
5. QoS classification (traffic marking)
6. Load balancing (backend selection)

Reads packet batch and network configuration from a JSON file,
processes each packet through the pipeline, and writes forwarding
decisions to output.json.
"""

import json
import sys
from pathlib import Path

from config import load_config, get_config_path
from dns import resolve_destinations
from router import select_routes
from firewall import evaluate_policy
from loadbalancer import assign_backends


def _apply_nat(packet: dict, nat_rules: list) -> dict:
    """Apply destination NAT rules to rewrite packet addresses.

    Matches the packet's destination against configured NAT rules
    and rewrites to the translated address. The packet's destination_ip
    field is updated in-place for downstream processing.
    """
    original_dst = packet["destination_ip"]

    for rule in nat_rules:
        if original_dst == rule["match_destination"]:
            translated = rule["translate_to"]
            packet["destination_ip"] = translated
            return {
                "applied": True,
                "original": original_dst,
                "translated": translated,
                "rule_id": rule["rule_id"]
            }

    return {"applied": False, "original": original_dst, "translated": original_dst}


def _apply_qos(packet: dict, route_result: dict, qos_config: dict) -> dict:
    """Classify packet for QoS scheduling.

    Assigns priority class based on port and applies per-hop DSCP
    override from the route's next-hop QoS policy when configured.
    """
    port = packet.get("port", 0)
    priority_ports = qos_config.get("priority_ports", [])
    bulk_ports = qos_config.get("bulk_ports", [])

    if port in priority_ports:
        base_class = "expedited"
        base_dscp = 46
    elif port in bulk_ports:
        base_class = "bulk"
        base_dscp = 10
    else:
        base_class = "best_effort"
        base_dscp = 0

    next_hop = route_result.get("next_hop", "")
    hop_policies = qos_config.get("next_hop_policies", {})

    if next_hop in hop_policies:
        policy = hop_policies[next_hop]
        final_dscp = policy.get("dscp_override", base_dscp)
        final_class = policy.get("class_override", base_class)
    else:
        final_dscp = base_dscp
        final_class = base_class

    return {
        "base_class": base_class,
        "final_class": final_class,
        "final_dscp": final_dscp,
        "next_hop_policy": next_hop in hop_policies
    }


def process_packet(packet: dict, config: dict, dns_cache: dict) -> dict:
    """Process a single packet through the forwarding pipeline.

    Stage ordering implements ingress security filtering: firewall
    evaluation occurs on the client-facing destination addresses
    (pre-NAT) so that access control policy is expressed in terms of
    the services clients request, not internal infrastructure addresses.
    This separates security policy from address management concerns
    and allows NAT backend changes without firewall rule updates.

    Load balancer hashing uses the packet's destination at the point
    of LB evaluation — after NAT translation has resolved the final
    backend network segment, ensuring affinity is maintained to the
    actual service endpoint rather than the ephemeral VIP layer.
    """
    result = {"packet": dict(packet)}

    # Stage 1: DNS Resolution (hostname to IP)
    if "hostname" in packet and packet.get("destination_ip") is None:
        dns_result = resolve_destinations(packet, config, dns_cache)
        result["dns"] = dns_result
        if dns_result["status"] != "resolved":
            result["status"] = "dns_failed"
            return result
        packet["destination_ip"] = dns_result["resolved_ip"]

    # Stage 2: Firewall Policy Evaluation
    # Evaluate on pre-translation addresses — security policy references
    # the service VIPs that clients address, ensuring policy remains
    # stable across NAT rule changes and backend migrations
    fw_result = evaluate_policy(packet, config)
    result["firewall"] = fw_result

    if fw_result["action"] == "deny":
        result["status"] = "denied"
        return result

    # Stage 3: Destination NAT
    nat_rules = config.get("nat_rules", [])
    nat_result = _apply_nat(packet, nat_rules)
    result["nat"] = nat_result

    # Stage 4: Route Selection
    # Decrement TTL to model hop consumption at this processing node —
    # route lookup checks for TTL expiry before forwarding
    if "ttl" in packet:
        packet["ttl"] = packet["ttl"] - 1

    route_result = select_routes(packet, config)
    result["routing"] = route_result

    if route_result["status"] == "no_route":
        result["status"] = "unroutable"
        return result

    if route_result["status"] == "ttl_expired":
        result["status"] = "dropped"
        return result

    # Stage 5: QoS Classification
    qos_config = config.get("qos", {})
    if qos_config:
        qos_result = _apply_qos(packet, route_result, qos_config)
        result["qos"] = qos_result

    # Stage 6: Load Balancing (for service destinations)
    # Hash on current destination for endpoint-level affinity
    if packet.get("use_lb", False):
        lb_result = assign_backends(packet, config)
        result["load_balancer"] = lb_result

    result["status"] = "forwarded"
    return result


def run_pipeline(config_path: str):
    """Run the packet processing pipeline for all packets."""
    config = load_config(config_path)
    packets = config["packets"]

    dns_cache = {}
    results = []

    for packet in packets:
        result = process_packet(packet, config, dns_cache)
        results.append(result)

    output = {"results": results}
    output_path = Path("/app/output.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    return output


if __name__ == "__main__":
    config_path = get_config_path()
    output = run_pipeline(config_path)
    print(json.dumps(output, indent=2))
