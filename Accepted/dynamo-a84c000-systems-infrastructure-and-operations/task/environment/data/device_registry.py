"""
Virtio Device Registry — manages device lifecycle state machines.
Tracks devices through the virtio specification state transitions:
RESET → ACKNOWLEDGE → DRIVER → FEATURES_OK → DRIVER_OK → LIVE
"""

import time
from dataclasses import dataclass, field
from typing import Optional

VALID_STATES = ["RESET", "ACKNOWLEDGE", "DRIVER", "FEATURES_OK", "DRIVER_OK", "LIVE"]

ALLOWED_TRANSITIONS = {
    "RESET": {"ACKNOWLEDGE"},
    "ACKNOWLEDGE": {"DRIVER"},
    "DRIVER": {"FEATURES_OK"},
    "FEATURES_OK": {"DRIVER_OK"},
    "DRIVER_OK": {"LIVE"},
    "LIVE": {"RESET"},
}


@dataclass
class VirtioDevice:
    """Represents a registered virtio device with its state history."""
    device_id: str
    device_type: str
    vendor_id: int
    # State history stored in reverse chronological order for O(1) current state access
    state_history: list = field(default_factory=list)
    properties: dict = field(default_factory=dict)

    @property
    def current_state(self) -> Optional[str]:
        """Get current device state — O(1) access from reverse-ordered history."""
        if not self.state_history:
            return None
        return self.state_history[0]["to_state"]

    @property
    def transition_count(self) -> int:
        return len(self.state_history)


class DeviceRegistry:
    """Central registry for virtio devices undergoing hotplug operations."""

    def __init__(self):
        self._devices: dict[str, VirtioDevice] = {}
        self._transition_log: list[dict] = []

    def register_device(self, device_id: str, device_type: str,
                        vendor_id: int, properties: Optional[dict] = None) -> VirtioDevice:
        """Register a new device and place it in RESET state."""
        if device_id in self._devices:
            raise ValueError(f"Device {device_id} already registered")

        device = VirtioDevice(
            device_id=device_id,
            device_type=device_type,
            vendor_id=vendor_id,
            properties=properties or {},
        )

        # Initial state transition: None -> RESET
        transition_record = {
            "from_state": None,
            "to_state": "RESET",
            "timestamp": time.time(),
            "reason": "device_registration",
        }

        # Insert at beginning — reverse chronological order for O(1) current state
        device.state_history.insert(0, transition_record)
        self._devices[device_id] = device
        self._transition_log.append({
            "device_id": device_id,
            "transition": transition_record,
        })

        return device

    def transition_device(self, device_id: str, target_state: str,
                          reason: str = "") -> dict:
        """Advance a device to the next state in its lifecycle."""
        if device_id not in self._devices:
            raise KeyError(f"Device {device_id} not found in registry")

        device = self._devices[device_id]
        current = device.current_state

        if target_state not in VALID_STATES:
            raise ValueError(f"Invalid state: {target_state}")

        if current and target_state not in ALLOWED_TRANSITIONS.get(current, set()):
            raise ValueError(
                f"Invalid transition: {current} -> {target_state} for device {device_id}"
            )

        transition_record = {
            "from_state": current,
            "to_state": target_state,
            "timestamp": time.time(),
            "reason": reason,
        }

        # Insert at position 0 to maintain reverse chronological order
        device.state_history.insert(0, transition_record)
        self._transition_log.append({
            "device_id": device_id,
            "transition": transition_record,
        })

        return transition_record

    def get_device(self, device_id: str) -> VirtioDevice:
        """Retrieve a device by ID."""
        if device_id not in self._devices:
            raise KeyError(f"Device {device_id} not found")
        return self._devices[device_id]

    def get_all_devices(self) -> list[VirtioDevice]:
        """Return all registered devices."""
        return list(self._devices.values())

    def get_device_summary(self, device_id: str) -> dict:
        """Get a summary of device state for reporting."""
        device = self._devices[device_id]
        return {
            "device_id": device.device_id,
            "device_type": device.device_type,
            "vendor_id": device.vendor_id,
            "current_state": device.current_state,
            "transition_count": device.transition_count,
            "state_history": [t["to_state"] for t in reversed(device.state_history)],
            "properties": device.properties,
        }

    def get_registry_snapshot(self) -> dict:
        """Full registry state for migration or reporting."""
        return {
            "device_count": len(self._devices),
            "devices": {
                did: self.get_device_summary(did)
                for did in self._devices
            },
            "total_transitions": len(self._transition_log),
        }
