"""
Flag Loader Module
==================
Loads and validates feature flag definitions from a JSON configuration file.
Handles parsing of flag metadata, targeting rules, rollout configurations,
dependency declarations, and mutual exclusion group definitions.

Provides structured flag objects for downstream evaluation stages.
"""

import json
import os
from typing import Any


class FlagDefinition:
    """Represents a single feature flag with all its configuration."""

    def __init__(self, raw: dict):
        self.name = raw["name"]
        self.enabled = raw.get("enabled", True)
        self.description = raw.get("description", "")
        self.rollout_percentage = raw.get("rollout_percentage", 100)
        self.targeting_rules = raw.get("targeting_rules", [])
        self.dependencies = raw.get("dependencies", [])
        self.tags = raw.get("tags", [])
        self.priority = raw.get("priority", 0)
        self._raw = raw

    def to_dict(self) -> dict:
        """Convert back to dictionary representation."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "description": self.description,
            "rollout_percentage": self.rollout_percentage,
            "targeting_rules": self.targeting_rules,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "priority": self.priority,
        }

    def __repr__(self):
        return f"FlagDefinition(name={self.name!r}, enabled={self.enabled})"


class DeviceRecord:
    """Represents a device in the fleet with its attributes."""

    def __init__(self, raw: dict):
        self.device_id = raw["device_id"]
        self.attributes = raw.get("attributes", {})
        self.last_seen = raw.get("last_seen", "")
        self.region = raw.get("region", "unknown")
        self.firmware_version = raw.get("firmware_version", "0.0.0")
        self.device_type = raw.get("device_type", "unknown")
        self._raw = raw

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """Retrieve a device attribute by key."""
        if key == "region":
            return self.region
        if key == "firmware_version":
            return self.firmware_version
        if key == "device_type":
            return self.device_type
        return self.attributes.get(key, default)

    def to_dict(self) -> dict:
        """Convert back to dictionary representation."""
        return {
            "device_id": self.device_id,
            "attributes": self.attributes,
            "last_seen": self.last_seen,
            "region": self.region,
            "firmware_version": self.firmware_version,
            "device_type": self.device_type,
        }

    def __repr__(self):
        return f"DeviceRecord(device_id={self.device_id!r})"


class ConfigLoader:
    """Loads and validates the complete configuration file."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._raw_config = None
        self._flags = None
        self._devices = None
        self._mutex_groups = None

    def load(self) -> dict:
        """Load configuration from JSON file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self._raw_config = json.load(f)

        self._validate_config()
        self._parse_flags()
        self._parse_devices()
        self._parse_mutex_groups()

        return self._raw_config

    def _validate_config(self):
        """Validate required top-level keys exist."""
        required_keys = ["flags", "devices"]
        for key in required_keys:
            if key not in self._raw_config:
                raise ValueError(f"Missing required config key: {key}")

    def _parse_flags(self):
        """Parse flag definitions into structured objects."""
        self._flags = [
            FlagDefinition(flag_data)
            for flag_data in self._raw_config["flags"]
        ]

    def _parse_devices(self):
        """Parse device records into structured objects."""
        self._devices = [
            DeviceRecord(device_data)
            for device_data in self._raw_config["devices"]
        ]

    def _parse_mutex_groups(self):
        """Parse mutual exclusion group definitions."""
        self._mutex_groups = self._raw_config.get("mutex_groups", [])

    def get_flags(self) -> list:
        """Return parsed flag definitions as dictionaries."""
        if self._flags is None:
            self.load()
        return [f.to_dict() for f in self._flags]

    def get_devices(self) -> list:
        """Return parsed device records as dictionaries."""
        if self._devices is None:
            self.load()
        return [d.to_dict() for d in self._devices]

    def get_mutex_groups(self) -> list:
        """Return mutual exclusion group definitions."""
        if self._mutex_groups is None:
            self.load()
        return self._mutex_groups
