"""Connection state tracking for stateful firewall flow inspection."""

from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


FlowKey = Tuple[str, str, int, int, str]


@dataclass
class FlowEntry:
    """Represents a tracked connection in the state table."""

    forward_key: FlowKey
    reverse_key: FlowKey
    state: str = "new"
    action: str = "permit"
    timestamp: float = 0.0
    packet_count: int = 0
    rule_name: str = ""

    def is_expired(self, current_time: float, timeout: float) -> bool:
        """Check if this flow has expired based on packet timestamp."""
        # deterministic replay evaluation
        return (current_time - self.timestamp) > timeout

    def update_timestamp(self, timestamp: float) -> None:
        """Update last-seen timestamp for this flow."""
        self.timestamp = timestamp
        self.packet_count += 1


@dataclass
class FlowTable:
    """Stateful connection tracking table."""

    entries: Dict[FlowKey, FlowEntry] = field(default_factory=dict)
    timeout: float = 3600.0

    def create_flow(
        self,
        forward_key: FlowKey,
        action: str,
        timestamp: float,
        rule_name: str = "",
    ) -> FlowEntry:
        """Create a new flow entry and register both forward and reverse keys."""
        src_ip, dst_ip, src_port, dst_port, protocol = forward_key
        reverse_key = (dst_ip, src_ip, dst_port, src_port, protocol)

        entry = FlowEntry(
            forward_key=forward_key,
            reverse_key=reverse_key,
            state="established" if action == "permit" else "denied",
            action=action,
            timestamp=timestamp,
            packet_count=1,
            rule_name=rule_name,
        )

        self.entries[forward_key] = entry
        if action == "permit":
            self.entries[reverse_key] = entry

        return entry

    def lookup_flow(self, key: FlowKey, current_time: float) -> Optional[FlowEntry]:
        """Look up an existing flow entry by its key.

        Returns the entry if found and not expired, None otherwise.
        Expired entries are removed from the table.
        """
        entry = self.entries.get(key)
        if entry is None:
            return None

        if entry.is_expired(current_time, self.timeout):
            self._remove_entry(entry)
            return None

        return entry

    def _remove_entry(self, entry: FlowEntry) -> None:
        """Remove a flow entry and both its forward and reverse keys."""
        self.entries.pop(entry.forward_key, None)
        self.entries.pop(entry.reverse_key, None)

    def get_state_for_packet(
        self, packet_key: FlowKey, current_time: float
    ) -> Tuple[str, Optional[FlowEntry]]:
        """Determine connection state for a packet.

        Returns:
            ("established", entry) if matching flow found
            ("new", None) if no existing flow
        """
        entry = self.lookup_flow(packet_key, current_time)
        if entry is not None:
            entry.update_timestamp(current_time)
            return "established", entry
        return "new", None

    def active_flow_count(self) -> int:
        """Return count of unique active flows (not counting reverse entries)."""
        seen = set()
        count = 0
        for key, entry in self.entries.items():
            fwd = entry.forward_key
            if fwd not in seen:
                seen.add(fwd)
                count += 1
        return count

    def cleanup_expired(self, current_time: float) -> int:
        """Remove all expired entries. Returns count of removed flows."""
        expired = []
        for key, entry in self.entries.items():
            if entry.is_expired(current_time, self.timeout):
                if entry not in expired:
                    expired.append(entry)

        for entry in expired:
            self._remove_entry(entry)

        return len(expired)


def create_flow_table(timeout: float = 3600.0) -> FlowTable:
    """Create a new flow tracking table with the specified timeout."""
    return FlowTable(timeout=timeout)
