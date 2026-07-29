"""
Address validator. Checks IP/subnet consistency, detects overlapping
address assignments, and validates interface addressing against the topology.
"""

from topology_loader import compute_network_address, prefix_from_mask


def validate_addressing(topology: dict) -> dict:
    """Run all address validation checks against the topology."""
    results = {
        "consistency_errors": check_subnet_consistency(topology),
        "overlap_warnings": detect_address_overlaps(topology),
        "interface_errors": validate_interface_addressing(topology),
        "total_interfaces_checked": _count_interfaces(topology),
    }
    results["is_valid"] = (
        len(results["consistency_errors"]) == 0
        and len(results["interface_errors"]) == 0
    )
    return results


def check_subnet_consistency(topology: dict) -> list:
    """Verify that each interface IP belongs to its declared subnet."""
    errors = []
    for router in topology["routers"]:
        for iface in router["interfaces"]:
            if iface["status"] == "down":
                continue
            ip = iface["ip_address"]
            mask = iface["subnet_mask"]
            prefix = prefix_from_mask(mask)
            net_addr = compute_network_address(ip, prefix)

            # Check against declared subnets
            matched_subnet = _find_matching_subnet(topology, net_addr, prefix)
            if matched_subnet is None and topology["subnets"]:
                errors.append({
                    "router": router["id"],
                    "interface": iface["name"],
                    "ip": ip,
                    "computed_network": net_addr,
                    "prefix_length": prefix,
                    "error": "interface network not found in declared subnets",
                })
    return errors


def detect_address_overlaps(topology: dict) -> list:
    """Detect overlapping IP address assignments across all interfaces."""
    warnings = []
    all_addresses = []

    for router in topology["routers"]:
        for iface in router["interfaces"]:
            if iface["status"] == "down":
                continue
            all_addresses.append({
                "router": router["id"],
                "interface": iface["name"],
                "ip": iface["ip_address"],
                "prefix": prefix_from_mask(iface["subnet_mask"]),
            })

    # Check for duplicate IPs
    seen_ips = {}
    for entry in all_addresses:
        ip = entry["ip"]
        if ip in seen_ips:
            warnings.append({
                "type": "duplicate_ip",
                "ip": ip,
                "first": f"{seen_ips[ip]['router']}:{seen_ips[ip]['interface']}",
                "second": f"{entry['router']}:{entry['interface']}",
            })
        else:
            seen_ips[ip] = entry

    # Check for overlapping subnets on different segments
    networks = []
    for entry in all_addresses:
        net = compute_network_address(entry["ip"], entry["prefix"])
        networks.append({
            "network": net,
            "prefix": entry["prefix"],
            "router": entry["router"],
            "interface": entry["interface"],
        })

    for i in range(len(networks)):
        for j in range(i + 1, len(networks)):
            if _subnets_overlap(networks[i], networks[j]):
                if networks[i]["network"] != networks[j]["network"] or networks[i]["prefix"] != networks[j]["prefix"]:
                    warnings.append({
                        "type": "subnet_overlap",
                        "first": f"{networks[i]['router']}:{networks[i]['interface']} ({networks[i]['network']}/{networks[i]['prefix']})",
                        "second": f"{networks[j]['router']}:{networks[j]['interface']} ({networks[j]['network']}/{networks[j]['prefix']})",
                    })

    return warnings


def validate_interface_addressing(topology: dict) -> list:
    """Validate link endpoint addressing - both ends should be in same subnet."""
    errors = []
    for link in topology["links"]:
        if len(link["endpoints"]) != 2:
            continue
        ep_a = link["endpoints"][0]
        ep_b = link["endpoints"][1]

        iface_a = _get_iface_from_topology(topology, ep_a["router_id"], ep_a["interface"])
        iface_b = _get_iface_from_topology(topology, ep_b["router_id"], ep_b["interface"])

        if iface_a is None or iface_b is None:
            continue

        prefix_a = prefix_from_mask(iface_a["subnet_mask"])
        prefix_b = prefix_from_mask(iface_b["subnet_mask"])

        net_a = compute_network_address(iface_a["ip_address"], prefix_a)
        net_b = compute_network_address(iface_b["ip_address"], prefix_b)

        if net_a != net_b or prefix_a != prefix_b:
            errors.append({
                "link": link["id"],
                "endpoint_a": f"{ep_a['router_id']}:{ep_a['interface']} ({iface_a['ip_address']}/{prefix_a})",
                "endpoint_b": f"{ep_b['router_id']}:{ep_b['interface']} ({iface_b['ip_address']}/{prefix_b})",
                "error": "link endpoints in different subnets",
            })

    return errors


def _find_matching_subnet(topology: dict, network: str, prefix: int) -> dict | None:
    """Find a declared subnet matching the given network/prefix."""
    for subnet in topology["subnets"]:
        if subnet["network"] == network and subnet["prefix_length"] == prefix:
            return subnet
    return None


def _subnets_overlap(net_a: dict, net_b: dict) -> bool:
    """Check if two subnets overlap."""
    a_start = _ip_to_int(net_a["network"])
    a_end = a_start + (1 << (32 - net_a["prefix"])) - 1
    b_start = _ip_to_int(net_b["network"])
    b_end = b_start + (1 << (32 - net_b["prefix"])) - 1
    return a_start <= b_end and b_start <= a_end


def _ip_to_int(ip: str) -> int:
    """Convert dotted IP to integer."""
    octets = [int(o) for o in ip.split(".")]
    return (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]


def _get_iface_from_topology(topology: dict, router_id: str, iface_name: str) -> dict | None:
    """Get interface object from topology by router ID and interface name."""
    for router in topology["routers"]:
        if router["id"] == router_id:
            for iface in router["interfaces"]:
                if iface["name"] == iface_name:
                    return iface
    return None


def _count_interfaces(topology: dict) -> int:
    """Count total number of active interfaces."""
    count = 0
    for router in topology["routers"]:
        for iface in router["interfaces"]:
            if iface["status"] != "down":
                count += 1
    return count
