"""Configuration parser for network packet processing pipeline.

Loads and validates the pipeline configuration including routes,
firewall rules, NAT rules, DNS records, QoS settings, load
balancer backends, and packet definitions.
"""

import json
import sys
from pathlib import Path


class ConfigError(Exception):
    """Raised when configuration is invalid or missing required fields."""
    pass


def load_config(config_path: str) -> dict:
    """Load and validate a JSON configuration file.

    Args:
        config_path: Path to the JSON configuration file.

    Returns:
        Parsed and validated configuration dictionary.

    Raises:
        ConfigError: If file is missing or has invalid structure.
    """
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(path) as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_path}: {e}")

    _validate(config)
    return config


def _validate(config: dict):
    """Validate required configuration sections."""
    if "packets" not in config:
        raise ConfigError("Missing required section: packets")
    if not config["packets"]:
        raise ConfigError("Packet list must not be empty")
    if "routes" not in config:
        raise ConfigError("Missing required section: routes")
    if "firewall_rules" not in config:
        raise ConfigError("Missing required section: firewall_rules")

    for i, packet in enumerate(config["packets"]):
        if "source_ip" not in packet:
            raise ConfigError(f"Packet {i} missing source_ip")
        if "destination_ip" not in packet and "hostname" not in packet:
            raise ConfigError(f"Packet {i} must have destination_ip or hostname")


def get_config_path() -> str:
    """Get config path from command line arguments or default."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    return "/app/config.json"
