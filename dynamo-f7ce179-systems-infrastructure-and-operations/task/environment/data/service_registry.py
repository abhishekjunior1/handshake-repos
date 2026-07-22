"""
Service Registry Module

Manages service discovery, backend registration, and health state tracking
for the service mesh. Provides methods to query active backends, check
staleness based on heartbeat TTLs, and manage service metadata.
"""

import time
from typing import Any


class Backend:
    """Represents a single backend instance for a service."""

    def __init__(self, backend_id: str, address: str, port: int,
                 weight: int = 1, registration_timestamp: float = 0.0,
                 last_heartbeat_timestamp: float = 0.0,
                 failure_count: int = 0, metadata: dict = None):
        self.backend_id = backend_id
        self.address = address
        self.port = port
        self.weight = weight
        self.registration_timestamp = registration_timestamp
        self.last_heartbeat_timestamp = last_heartbeat_timestamp
        self.failure_count = failure_count
        self.metadata = metadata or {}

    def endpoint(self) -> str:
        """Return the network endpoint as address:port."""
        return f"{self.address}:{self.port}"

    def to_dict(self) -> dict:
        """Serialize backend to dictionary."""
        return {
            "backend_id": self.backend_id,
            "address": self.address,
            "port": self.port,
            "weight": self.weight,
            "registration_timestamp": self.registration_timestamp,
            "last_heartbeat_timestamp": self.last_heartbeat_timestamp,
            "failure_count": self.failure_count,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Backend":
        """Deserialize backend from dictionary."""
        return cls(
            backend_id=data["backend_id"],
            address=data["address"],
            port=data["port"],
            weight=data.get("weight", 1),
            registration_timestamp=data.get("registration_timestamp", 0.0),
            last_heartbeat_timestamp=data.get("last_heartbeat_timestamp", 0.0),
            failure_count=data.get("failure_count", 0),
            metadata=data.get("metadata", {})
        )


class ServiceEntry:
    """Represents a registered service with its backends."""

    def __init__(self, service_name: str, backends: list = None,
                 ttl_seconds: float = 30.0, protocol: str = "http"):
        self.service_name = service_name
        self.backends = backends or []
        self.ttl_seconds = ttl_seconds
        self.protocol = protocol

    def add_backend(self, backend: Backend) -> None:
        """Register a new backend instance."""
        self.backends.append(backend)

    def remove_backend(self, backend_id: str) -> bool:
        """Deregister a backend by ID. Returns True if found and removed."""
        original_count = len(self.backends)
        self.backends = [b for b in self.backends if b.backend_id != backend_id]
        return len(self.backends) < original_count

    def get_backend_by_id(self, backend_id: str) -> Backend | None:
        """Look up a specific backend by its ID."""
        for backend in self.backends:
            if backend.backend_id == backend_id:
                return backend
        return None

    def to_dict(self) -> dict:
        """Serialize service entry."""
        return {
            "service_name": self.service_name,
            "backends": [b.to_dict() for b in self.backends],
            "ttl_seconds": self.ttl_seconds,
            "protocol": self.protocol
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServiceEntry":
        """Deserialize service entry from dictionary."""
        entry = cls(
            service_name=data["service_name"],
            ttl_seconds=data.get("ttl_seconds", 30.0),
            protocol=data.get("protocol", "http")
        )
        for b_data in data.get("backends", []):
            entry.add_backend(Backend.from_dict(b_data))
        return entry


class ServiceRegistry:
    """Central registry for all services in the mesh."""

    def __init__(self):
        self.services: dict[str, ServiceEntry] = {}

    def register_service(self, entry: ServiceEntry) -> None:
        """Register or update a service entry."""
        self.services[entry.service_name] = entry

    def get_service(self, service_name: str) -> ServiceEntry | None:
        """Retrieve a service entry by name."""
        return self.services.get(service_name)

    def get_healthy_backends(self, service_name: str,
                             current_time: float) -> list[Backend]:
        """Return backends that are not stale based on heartbeat TTL.

        A backend is considered healthy if:
            last_heartbeat_timestamp + ttl_seconds > current_time
        """
        entry = self.get_service(service_name)
        if entry is None:
            return []
        healthy = []
        for backend in entry.backends:
            if backend.last_heartbeat_timestamp + entry.ttl_seconds > current_time:
                healthy.append(backend)
        return healthy

    def is_backend_stale(self, service_name: str, backend: Backend,
                         current_time: float) -> bool:
        """Check if a specific backend has exceeded its heartbeat TTL.

        Uses last_heartbeat_timestamp as the anchor for staleness calculation.
        """
        entry = self.get_service(service_name)
        if entry is None:
            return True
        return backend.last_heartbeat_timestamp + entry.ttl_seconds <= current_time

    def get_all_services(self) -> list[str]:
        """List all registered service names."""
        return list(self.services.keys())

    def load_from_config(self, config: dict) -> None:
        """Populate registry from a configuration dictionary."""
        for svc_data in config.get("services", []):
            entry = ServiceEntry.from_dict(svc_data)
            self.register_service(entry)

    def to_dict(self) -> dict:
        """Serialize entire registry."""
        return {
            "services": [entry.to_dict() for entry in self.services.values()]
        }
