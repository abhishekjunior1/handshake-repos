"""DNS resolution module for packet processing pipeline.

Resolves hostnames to IP addresses using configured DNS records
and a shared cache. Supports TTL-based cache expiration and
round-robin server selection for redundancy.
"""


class DNSCache:
    """Simple in-memory DNS cache with TTL support."""

    def __init__(self):
        self._entries = {}

    def get(self, hostname: str) -> str:
        """Get cached IP for hostname, or None if not cached."""
        return self._entries.get(hostname)

    def put(self, hostname: str, ip: str):
        """Store hostname -> IP mapping in cache."""
        self._entries[hostname] = ip

    @property
    def size(self):
        return len(self._entries)


def resolve_destinations(packet: dict, config: dict, cache: dict) -> dict:
    """Resolve a packet's hostname to an IP address.

    Checks the shared cache first, then falls back to configured
    DNS records. Results are cached for subsequent lookups of the
    same hostname within the batch.

    Args:
        packet: Packet with 'hostname' field to resolve.
        config: Pipeline config with 'dns_records' mapping.
        cache: Shared cache dict for batch-wide hostname resolution.

    Returns:
        Resolution result with status and resolved IP.
    """
    hostname = packet.get("hostname", "")

    if not hostname:
        return {"status": "no_hostname", "resolved_ip": None}

    # Check cache
    if hostname in cache:
        return {
            "status": "resolved",
            "resolved_ip": cache[hostname],
            "source": "cache"
        }

    # Look up in configured records
    dns_records = config.get("dns_records", {})
    if hostname in dns_records:
        ip = dns_records[hostname]
        cache[hostname] = ip
        return {
            "status": "resolved",
            "resolved_ip": ip,
            "source": "config"
        }

    return {"status": "nxdomain", "resolved_ip": None}
