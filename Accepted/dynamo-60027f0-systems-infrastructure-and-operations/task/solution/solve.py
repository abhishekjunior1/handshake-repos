"""Solution that fixes the stage ordering bugs in network.py and loadbalancer.py."""

import subprocess
import sys
from pathlib import Path


def patch_network():
    """Fix network.py: NAT must execute before firewall, and LB needs
    the original VIP for session affinity hashing.
    """
    path = Path("/app/network.py")
    content = path.read_text()

    # Fix Bug 1: Swap stages 2 and 3 (NAT before firewall)
    # Also fix Bug 2: save original destination for LB affinity
    old_stages = '''    # Stage 2: Firewall Policy Evaluation
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
    result["nat"] = nat_result'''

    new_stages = '''    # Stage 2: Save original VIP, then apply NAT
    original_destination = packet["destination_ip"]
    nat_rules = config.get("nat_rules", [])
    nat_result = _apply_nat(packet, nat_rules)
    result["nat"] = nat_result

    # Stage 3: Firewall Policy Evaluation (on post-NAT addresses)
    fw_result = evaluate_policy(packet, config)
    result["firewall"] = fw_result

    if fw_result["action"] == "deny":
        result["status"] = "denied"
        return result'''

    content = content.replace(old_stages, new_stages)

    # Fix Bug 2: Pass original VIP to LB for session affinity
    content = content.replace(
        '        lb_result = assign_backends(packet, config)',
        '        lb_result = assign_backends(packet, config, affinity_ip=original_destination)'
    )

    path.write_text(content)


def patch_loadbalancer():
    """Fix loadbalancer.py: add affinity_ip parameter for VIP-based hashing."""
    path = Path("/app/loadbalancer.py")
    content = path.read_text()

    # Add affinity_ip parameter to function signature
    content = content.replace(
        'def assign_backends(packet: dict, config: dict) -> dict:',
        'def assign_backends(packet: dict, config: dict, affinity_ip: str = None) -> dict:'
    )

    # Use affinity_ip for hashing when provided
    content = content.replace(
        '    # Consistent hash on destination IP for session affinity\n'
        '    dst_ip = packet.get("destination_ip", "0.0.0.0")',
        '    # Consistent hash for session affinity\n'
        '    dst_ip = affinity_ip if affinity_ip else packet.get("destination_ip", "0.0.0.0")'
    )

    path.write_text(content)


def run_pipeline():
    """Run the network pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/network.py", "/app/config.json"],
        capture_output=True, text=True, cwd="/app"
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    patch_network()
    patch_loadbalancer()
    run_pipeline()
