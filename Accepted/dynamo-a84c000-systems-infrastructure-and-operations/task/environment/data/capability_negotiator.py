"""
Virtio Capability Negotiator — handles feature bit negotiation between
host hypervisor and guest driver during device initialization.
"""

from dataclasses import dataclass, field


# Standard virtio feature bits
VIRTIO_F_NOTIFY_ON_EMPTY = 24
VIRTIO_F_ANY_LAYOUT = 27
VIRTIO_F_RING_INDIRECT_DESC = 28
VIRTIO_F_RING_EVENT_IDX = 29
VIRTIO_F_VERSION_1 = 32
VIRTIO_F_ACCESS_PLATFORM = 33
VIRTIO_F_RING_PACKED = 34
VIRTIO_F_ORDER_PLATFORM = 36
VIRTIO_F_SR_IOV = 37
VIRTIO_F_INDIRECT_DESC = 28
VIRTIO_F_EVENT_IDX = 29

# Feature bit names for human-readable output
FEATURE_NAMES = {
    24: "NOTIFY_ON_EMPTY",
    27: "ANY_LAYOUT",
    28: "INDIRECT_DESC",
    29: "EVENT_IDX",
    32: "VERSION_1",
    33: "ACCESS_PLATFORM",
    34: "RING_PACKED",
    36: "ORDER_PLATFORM",
    37: "SR_IOV",
}


@dataclass
class NegotiationResult:
    """Result of feature bit negotiation."""
    host_features: list[int]
    guest_features: list[int]
    negotiated_features: list[int]
    rejected_features: list[int]
    feature_names: dict[int, str] = field(default_factory=dict)


class CapabilityNegotiator:
    """Performs virtio feature bit negotiation between host and guest."""

    def __init__(self, host_features: list[int], guest_features: list[int]):
        """Initialize negotiator with host and guest feature sets."""
        self._host_features = sorted(set(host_features))
        self._guest_features = sorted(set(guest_features))
        self._negotiated: list[int] = []
        self._rejected: list[int] = []
        self._negotiation_complete = False

    def negotiate(self) -> NegotiationResult:
        """Perform feature bit negotiation — returns intersection of features."""
        host_set = set(self._host_features)
        guest_set = set(self._guest_features)

        # Negotiated features = intersection of host and guest capabilities
        self._negotiated = sorted(host_set & guest_set)

        # Rejected features = host offered but guest cannot support
        self._rejected = sorted(host_set - guest_set)

        self._negotiation_complete = True

        return NegotiationResult(
            host_features=self._host_features,
            guest_features=self._guest_features,
            negotiated_features=self._negotiated,
            rejected_features=self._rejected,
            feature_names={
                bit: FEATURE_NAMES.get(bit, f"UNKNOWN_{bit}")
                for bit in self._host_features
            },
        )

    @property
    def negotiated_features(self) -> list[int]:
        """Get the negotiated feature set after negotiation."""
        if not self._negotiation_complete:
            raise RuntimeError("Negotiation has not been performed yet")
        return self._negotiated.copy()

    @property
    def host_features(self) -> list[int]:
        """Get the host-advertised feature set."""
        return self._host_features.copy()

    def has_feature(self, feature_bit: int) -> bool:
        """Check if a specific feature was negotiated."""
        return feature_bit in self._negotiated

    def get_queue_depth_multiplier(self, features: list[int]) -> int:
        """
        Calculate queue depth multiplier based on active features.

        INDIRECT_DESC enables larger effective queue depths by allowing
        chained descriptor tables. EVENT_IDX reduces interrupt overhead
        enabling higher throughput.
        """
        multiplier = 1
        if VIRTIO_F_INDIRECT_DESC in features:
            multiplier *= 2  # Indirect descriptors double effective depth
        if VIRTIO_F_EVENT_IDX in features:
            multiplier += 1  # Event index adds one more multiplier unit
        return multiplier

    def get_negotiation_summary(self) -> dict:
        """Generate a summary of the negotiation for reporting."""
        if not self._negotiation_complete:
            raise RuntimeError("Negotiation has not been performed yet")

        return {
            "host_feature_count": len(self._host_features),
            "guest_feature_count": len(self._guest_features),
            "negotiated_feature_count": len(self._negotiated),
            "rejected_feature_count": len(self._rejected),
            "host_features": self._host_features,
            "guest_features": self._guest_features,
            "negotiated_features": self._negotiated,
            "rejected_features": self._rejected,
            "feature_names": {
                bit: FEATURE_NAMES.get(bit, f"FEATURE_{bit}")
                for bit in sorted(set(self._host_features + self._guest_features))
            },
        }
