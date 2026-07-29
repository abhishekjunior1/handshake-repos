"""
IP Address Normalizer

Normalizes IP addresses for consistent correlation across heterogeneous
sensor infrastructure. Handles IPv4-mapped IPv6 addresses, IPv6 abbreviation
expansion, and loopback address normalization to ensure the same host is
always represented consistently in the correlation pipeline.
"""

import ipaddress
from typing import Any


def normalize_ip(ip_str: str) -> str:
    """
    Normalize an IP address string for consistent correlation.

    Handles:
    - IPv4-mapped IPv6 to IPv4 conversion (::ffff:10.0.1.1 -> 10.0.1.1)
    - IPv6 abbreviation expansion to full form
    - Loopback normalization (::1 -> 127.0.0.1)
    - Whitespace stripping

    Args:
        ip_str: Raw IP address string from sensor data.

    Returns:
        Normalized IP address string.
    """
    ip_str = ip_str.strip()

    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        # If parsing fails, return stripped original
        return ip_str

    # Handle IPv6 addresses
    if isinstance(addr, ipaddress.IPv6Address):
        # Check for IPv4-mapped IPv6 (::ffff:x.x.x.x)
        if is_ipv4_mapped(ip_str):
            return extract_ipv4_from_mapped(ip_str)

        # Normalize IPv6 loopback to IPv4 loopback
        if addr == ipaddress.ip_address('::1'):
            return '127.0.0.1'

        # Return exploded form for consistent representation
        return str(addr.exploded)

    # IPv4 - return standard string representation
    return str(addr)


def is_ipv4_mapped(ip_str: str) -> bool:
    """
    Check if an IP address string is an IPv4-mapped IPv6 address.

    IPv4-mapped IPv6 addresses have the form ::ffff:a.b.c.d and represent
    IPv4 addresses within the IPv6 address space.

    Args:
        ip_str: IP address string to check.

    Returns:
        True if the address is an IPv4-mapped IPv6 address.
    """
    ip_str = ip_str.strip()

    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    if isinstance(addr, ipaddress.IPv6Address):
        return addr.ipv4_mapped is not None

    return False


def extract_ipv4_from_mapped(ip_str: str) -> str:
    """
    Extract the IPv4 address from an IPv4-mapped IPv6 address.

    Args:
        ip_str: IPv4-mapped IPv6 address string (e.g., '::ffff:10.0.1.1').

    Returns:
        The extracted IPv4 address string (e.g., '10.0.1.1').

    Raises:
        ValueError: If the address is not an IPv4-mapped IPv6 address.
    """
    ip_str = ip_str.strip()

    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        raise ValueError(f"Invalid IP address: {ip_str}")

    if not isinstance(addr, ipaddress.IPv6Address):
        raise ValueError(f"Not an IPv6 address: {ip_str}")

    mapped = addr.ipv4_mapped
    if mapped is None:
        raise ValueError(f"Not an IPv4-mapped IPv6 address: {ip_str}")

    return str(mapped)
