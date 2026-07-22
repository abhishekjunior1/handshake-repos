"""Zone definition parser for zone-based firewall configuration."""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Zone:
    """Represents a single firewall security zone."""

    name: str
    interfaces: List[str]
    default_action: str = "deny"
    description: str = ""

    def contains_interface(self, interface: str) -> bool:
        """Check if a given interface belongs to this zone."""
        return interface in self.interfaces

    def to_dict(self) -> dict:
        """Serialize zone to dictionary."""
        return {
            "name": self.name,
            "interfaces": self.interfaces,
            "default_action": self.default_action,
            "description": self.description,
        }


@dataclass
class ZoneMap:
    """Complete mapping of zones and their interface assignments."""

    zones: Dict[str, Zone] = field(default_factory=dict)
    interface_to_zone: Dict[str, str] = field(default_factory=dict)

    def add_zone(self, zone: Zone) -> None:
        """Register a zone and index its interfaces."""
        self.zones[zone.name] = zone
        for iface in zone.interfaces:
            self.interface_to_zone[iface] = zone.name

    def get_zone_by_name(self, name: str) -> Optional[Zone]:
        """Retrieve a zone object by its name."""
        return self.zones.get(name)

    def get_zone_for_interface(self, interface: str) -> Optional[str]:
        """Resolve which zone an interface belongs to."""
        return self.interface_to_zone.get(interface)

    def resolve_zone_for_ip(self, ip_address: str, subnet_map: Dict[str, str]) -> Optional[str]:
        """Resolve zone membership for an IP address using subnet-to-interface mapping."""
        for subnet, interface in subnet_map.items():
            if ip_in_subnet(ip_address, subnet):
                return self.interface_to_zone.get(interface)
        return None

    def list_zones(self) -> List[str]:
        """Return all zone names."""
        return list(self.zones.keys())

    def get_default_action(self, zone_name: str) -> str:
        """Get the default action for a zone (applied when no rule matches)."""
        zone = self.zones.get(zone_name)
        if zone:
            return zone.default_action
        return "deny"


def ip_in_subnet(ip: str, subnet: str) -> bool:
    """Check if an IP address falls within a CIDR subnet."""
    if "/" not in subnet:
        return ip == subnet
    network, prefix_len = subnet.split("/")
    prefix_len = int(prefix_len)
    ip_int = ip_to_int(ip)
    net_int = ip_to_int(network)
    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
    return (ip_int & mask) == (net_int & mask)


def ip_to_int(ip: str) -> int:
    """Convert dotted-quad IP to integer."""
    parts = ip.split(".")
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])


def parse_zones(config: dict) -> ZoneMap:
    """Parse zone definitions from configuration dictionary.

    Expected format:
    {
        "zones": [
            {
                "name": "zone_name",
                "interfaces": ["eth0"],
                "default_action": "deny",
                "description": "..."
            }
        ]
    }
    """
    zone_map = ZoneMap()
    zones_config = config.get("zones", [])

    for zone_def in zones_config:
        name = zone_def["name"]
        interfaces = zone_def.get("interfaces", [])
        default_action = zone_def.get("default_action", "deny")
        description = zone_def.get("description", "")

        zone = Zone(
            name=name,
            interfaces=interfaces,
            default_action=default_action,
            description=description,
        )
        zone_map.add_zone(zone)

    return zone_map


def load_zones_from_file(filepath: str) -> ZoneMap:
    """Load and parse zones from a JSON configuration file."""
    with open(filepath, "r") as f:
        config = json.load(f)
    return parse_zones(config)
