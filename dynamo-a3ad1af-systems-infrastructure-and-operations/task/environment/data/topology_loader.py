"""
Network topology loader. Parses JSON topology definitions into structured
router, interface, link, and subnet objects for downstream processing.
"""

import json
from typing import Any


def load_topology(filepath: str) -> dict:
    """Load and validate a network topology file."""
    with open(filepath, "r") as f:
        raw = json.load(f)

    topology = {
        "routers": _parse_routers(raw.get("routers", [])),
        "links": _parse_links(raw.get("links", [])),
        "subnets": _parse_subnets(raw.get("subnets", [])),
        "vlans": _parse_vlans(raw.get("vlans", [])),
        "reference_bandwidth": raw.get("reference_bandwidth", 100000),
        "ospf_areas": raw.get("ospf_areas", []),
    }
    return topology


def _parse_routers(router_list: list) -> list:
    """Parse router definitions with their interfaces."""
    routers = []
    for r in router_list:
        router = {
            "id": r["id"],
            "hostname": r.get("hostname", r["id"]),
            "interfaces": _parse_interfaces(r.get("interfaces", [])),
            "ospf_area": r.get("ospf_area", 0),
            "router_priority": r.get("router_priority", 1),
        }
        routers.append(router)
    return routers


def _parse_interfaces(iface_list: list) -> list:
    """Parse interface definitions with IP, mask, bandwidth, and MTU."""
    interfaces = []
    for iface in iface_list:
        parsed = {
            "name": iface["name"],
            "ip_address": iface["ip_address"],
            "subnet_mask": iface["subnet_mask"],
            "bandwidth": iface.get("bandwidth", 1000),
            "mtu": iface.get("mtu", 1500),
            "status": iface.get("status", "up"),
            "ospf_cost": iface.get("ospf_cost", None),
            "vlan_id": iface.get("vlan_id", None),
            "description": iface.get("description", ""),
        }
        interfaces.append(parsed)
    return interfaces


def _parse_links(link_list: list) -> list:
    """Parse link definitions connecting router interfaces."""
    links = []
    for link in link_list:
        parsed = {
            "id": link["id"],
            "endpoints": link["endpoints"],
            "bandwidth": link.get("bandwidth", 1000),
            "link_type": link.get("link_type", "point-to-point"),
            "metric": link.get("metric", None),
            "latency_ms": link.get("latency_ms", 1),
        }
        links.append(parsed)
    return links


def _parse_subnets(subnet_list: list) -> list:
    """Parse subnet definitions."""
    subnets = []
    for s in subnet_list:
        parsed = {
            "network": s["network"],
            "prefix_length": s["prefix_length"],
            "vlan_id": s.get("vlan_id", None),
            "description": s.get("description", ""),
        }
        subnets.append(parsed)
    return subnets


def _parse_vlans(vlan_list: list) -> list:
    """Parse VLAN configurations."""
    vlans = []
    for v in vlan_list:
        parsed = {
            "id": v["id"],
            "name": v.get("name", f"VLAN_{v['id']}"),
            "network": v.get("network", None),
            "prefix_length": v.get("prefix_length", None),
        }
        vlans.append(parsed)
    return vlans


def get_router_by_id(topology: dict, router_id: str) -> dict | None:
    """Find a router by its ID."""
    for router in topology["routers"]:
        if router["id"] == router_id:
            return router
    return None


def get_interface(topology: dict, router_id: str, iface_name: str) -> dict | None:
    """Find a specific interface on a router."""
    router = get_router_by_id(topology, router_id)
    if router is None:
        return None
    for iface in router["interfaces"]:
        if iface["name"] == iface_name:
            return iface
    return None


def get_link_between(topology: dict, router_a: str, router_b: str) -> dict | None:
    """Find the link connecting two routers."""
    for link in topology["links"]:
        eps = link["endpoints"]
        routers_in_link = [ep["router_id"] for ep in eps]
        if router_a in routers_in_link and router_b in routers_in_link:
            return link
    return None


def get_link_for_interface(topology: dict, router_id: str, iface_name: str) -> dict | None:
    """Find the link associated with a specific interface on a router."""
    for link in topology["links"]:
        for ep in link["endpoints"]:
            if ep["router_id"] == router_id and ep["interface"] == iface_name:
                return link
    return None


def compute_network_address(ip: str, prefix_length: int) -> str:
    """Compute the network address from an IP and prefix length."""
    octets = [int(o) for o in ip.split(".")]
    ip_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
    mask = (0xFFFFFFFF << (32 - prefix_length)) & 0xFFFFFFFF
    net_int = ip_int & mask
    return f"{(net_int >> 24) & 0xFF}.{(net_int >> 16) & 0xFF}.{(net_int >> 8) & 0xFF}.{net_int & 0xFF}"


def prefix_from_mask(subnet_mask: str) -> int:
    """Convert dotted subnet mask to prefix length."""
    octets = [int(o) for o in subnet_mask.split(".")]
    mask_int = (octets[0] << 24) | (octets[1] << 16) | (octets[2] << 8) | octets[3]
    count = 0
    while mask_int & 0x80000000:
        count += 1
        mask_int = (mask_int << 1) & 0xFFFFFFFF
    return count
