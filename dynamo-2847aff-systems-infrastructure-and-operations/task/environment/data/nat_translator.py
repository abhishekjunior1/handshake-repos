"""NAT translation engine supporting SNAT and DNAT pool mappings."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class NatEntry:
    """A single NAT mapping entry."""

    original_ip: str
    translated_ip: str
    original_port_min: int = 0
    original_port_max: int = 65535
    translated_port_min: int = 0
    translated_port_max: int = 65535
    protocol: str = "any"

    def matches_ip(self, ip: str) -> bool:
        """Check if the given IP matches this NAT entry's original IP or CIDR."""
        if "/" in self.original_ip:
            return cidr_contains(self.original_ip, ip)
        return ip == self.original_ip

    def matches_port(self, port: int) -> bool:
        """Check if port falls in the original port range."""
        return self.original_port_min <= port <= self.original_port_max

    def translate_ip(self, ip: str) -> str:
        """Return the translated IP for a matching original."""
        return self.translated_ip

    def translate_port(self, port: int) -> int:
        """Translate port based on range offset."""
        if self.original_port_min == self.translated_port_min:
            return port
        offset = port - self.original_port_min
        return self.translated_port_min + offset


@dataclass
class NatPool:
    """Collection of NAT entries for a direction (SNAT or DNAT)."""

    entries: List[NatEntry] = field(default_factory=list)

    def add_entry(self, entry: NatEntry) -> None:
        """Add a NAT mapping entry to this pool."""
        self.entries.append(entry)

    def find_match(self, ip: str, port: int, protocol: str) -> Optional[NatEntry]:
        """Find the first NAT entry matching the given IP, port, and protocol."""
        for entry in self.entries:
            if not entry.matches_ip(ip):
                continue
            if not entry.matches_port(port):
                continue
            if entry.protocol != "any" and entry.protocol.lower() != protocol.lower():
                continue
            return entry
        return None


@dataclass
class NatTranslator:
    """Handles both source and destination NAT translations."""

    snat_pool: NatPool = field(default_factory=NatPool)
    dnat_pool: NatPool = field(default_factory=NatPool)

    def apply_dnat(
        self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, protocol: str
    ) -> Tuple[str, str, int, int, str, bool]:
        """Apply destination NAT to packet. Returns translated tuple and whether NAT was applied."""
        entry = self.dnat_pool.find_match(dst_ip, dst_port, protocol)
        if entry is None:
            return src_ip, dst_ip, src_port, dst_port, protocol, False
        new_dst_ip = entry.translate_ip(dst_ip)
        new_dst_port = entry.translate_port(dst_port)
        nat_applied = (new_dst_ip != dst_ip) or (new_dst_port != dst_port)
        return src_ip, new_dst_ip, src_port, new_dst_port, protocol, nat_applied

    def apply_snat(
        self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, protocol: str
    ) -> Tuple[str, str, int, int, str, bool]:
        """Apply source NAT to packet. Returns translated tuple and whether NAT was applied."""
        entry = self.snat_pool.find_match(src_ip, src_port, protocol)
        if entry is None:
            return src_ip, dst_ip, src_port, dst_port, protocol, False
        new_src_ip = entry.translate_ip(src_ip)
        new_src_port = entry.translate_port(src_port)
        nat_applied = (new_src_ip != src_ip) or (new_src_port != src_port)
        return new_src_ip, dst_ip, new_src_port, dst_port, protocol, nat_applied


def cidr_contains(cidr: str, ip: str) -> bool:
    """Check if IP falls within a CIDR range."""
    network, prefix_str = cidr.split("/")
    prefix_len = int(prefix_str)
    if prefix_len == 0:
        return True
    mask = (0xFFFFFFFF << (32 - prefix_len)) & 0xFFFFFFFF
    ip_int = ip_to_int(ip)
    net_int = ip_to_int(network)
    return (ip_int & mask) == (net_int & mask)


def ip_to_int(ip: str) -> int:
    """Convert dotted-quad to integer."""
    parts = ip.split(".")
    return (int(parts[0]) << 24) | (int(parts[1]) << 16) | (int(parts[2]) << 8) | int(parts[3])


def parse_nat_config(config: dict) -> NatTranslator:
    """Parse NAT configuration into a NatTranslator instance."""
    translator = NatTranslator()

    for dnat_def in config.get("dnat_rules", []):
        entry = NatEntry(
            original_ip=dnat_def["original_ip"],
            translated_ip=dnat_def["translated_ip"],
            original_port_min=dnat_def.get("port_range", [0, 65535])[0],
            original_port_max=dnat_def.get("port_range", [0, 65535])[1],
            translated_port_min=dnat_def.get("translated_port_range", dnat_def.get("port_range", [0, 65535]))[0],
            translated_port_max=dnat_def.get("translated_port_range", dnat_def.get("port_range", [0, 65535]))[1],
            protocol=dnat_def.get("protocol", "any"),
        )
        translator.dnat_pool.add_entry(entry)

    for snat_def in config.get("snat_rules", []):
        entry = NatEntry(
            original_ip=snat_def["original_ip"],
            translated_ip=snat_def["translated_ip"],
            original_port_min=snat_def.get("port_range", [0, 65535])[0],
            original_port_max=snat_def.get("port_range", [0, 65535])[1],
            translated_port_min=snat_def.get("translated_port_range", snat_def.get("port_range", [0, 65535]))[0],
            translated_port_max=snat_def.get("translated_port_range", snat_def.get("port_range", [0, 65535]))[1],
            protocol=snat_def.get("protocol", "any"),
        )
        translator.snat_pool.add_entry(entry)

    return translator
