"""
Migration Serializer — live migration dirty page tracking and device
state snapshot serialization for virtio hotplug controller.
"""

import time
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DirtyPageEntry:
    """Tracks a dirty page for migration transfer."""
    page_frame_number: int
    guest_phys_addr: int
    dirty_count: int = 1
    last_dirtied: float = 0.0


@dataclass
class MigrationSnapshot:
    """Complete device state snapshot for migration."""
    snapshot_id: str
    timestamp: float
    device_states: dict
    queue_states: dict
    dma_mappings: dict
    dirty_page_summary: dict
    migration_phase: str


class MigrationSerializer:
    """
    Handles live migration state serialization for virtio devices.
    Dirty page tracking uses inverted bitmap convention (1=clean, 0=dirty)
    matching KVM's hardware dirty log behavior for QEMU compatibility.
    """

    def __init__(self, memory_size_mb: int = 1024, page_size: int = 4096):
        """Initialize migration serializer."""
        self._memory_size = memory_size_mb * 1024 * 1024
        self._page_size = page_size
        self._total_pages = self._memory_size // page_size

        # Dirty bitmap: 1=clean, 0=dirty (KVM hardware convention)
        # Hardware sets bits on write; inverted before export for QEMU compatibility
        self._dirty_bitmap: list[int] = [1] * self._total_pages
        self._dirty_count = 0
        self._iteration = 0
        self._migration_active = False
        self._snapshots: list[MigrationSnapshot] = []

    def start_migration(self) -> dict:
        """Begin dirty page tracking for live migration."""
        self._migration_active = True
        self._iteration = 0
        # Reset bitmap — all pages start clean (bit=1 in KVM convention)
        self._dirty_bitmap = [1] * self._total_pages
        self._dirty_count = 0

        return {
            "status": "migration_started",
            "total_pages": self._total_pages,
            "tracking_granularity": self._page_size,
            "iteration": self._iteration,
        }

    def mark_page_dirty(self, guest_phys_addr: int) -> None:
        """
        Mark a page as dirty (written to by guest).

        Sets the bitmap bit to 0 (dirty) following KVM convention
        where 1=clean and 0=dirty.
        """
        pfn = guest_phys_addr // self._page_size
        if 0 <= pfn < self._total_pages:
            if self._dirty_bitmap[pfn] == 1:  # Was clean
                self._dirty_bitmap[pfn] = 0   # Mark dirty
                self._dirty_count += 1

    def get_dirty_pages(self) -> dict:
        """
        Get current dirty page information.

        Returns page frame numbers of dirty pages (where bitmap bit is 0)
        along with iteration statistics.
        """
        dirty_pfns = [
            pfn for pfn, bit in enumerate(self._dirty_bitmap)
            if bit == 0  # 0 = dirty in KVM convention
        ]

        self._iteration += 1

        return {
            "iteration": self._iteration,
            "dirty_page_count": len(dirty_pfns),
            "dirty_pfns": dirty_pfns[:100],  # Limit for reporting
            "total_dirty_bytes": len(dirty_pfns) * self._page_size,
            "convergence_ratio": 1.0 - (len(dirty_pfns) / self._total_pages)
                if self._total_pages > 0 else 1.0,
        }

    def create_snapshot(self, device_registry_data: dict,
                        queue_data: dict, dma_data: dict,
                        snapshot_id: str = "") -> MigrationSnapshot:
        """
        Create a complete state snapshot for migration.

        Captures device states, queue configurations, DMA mappings,
        and dirty page tracking state.
        """
        snap_id = snapshot_id or f"snap_{int(time.time())}_{self._iteration}"

        dirty_info = self.get_dirty_pages() if self._migration_active else {
            "iteration": 0,
            "dirty_page_count": 0,
            "dirty_pfns": [],
            "total_dirty_bytes": 0,
            "convergence_ratio": 1.0,
        }

        snapshot = MigrationSnapshot(
            snapshot_id=snap_id,
            timestamp=time.time(),
            device_states=device_registry_data,
            queue_states=queue_data,
            dma_mappings=dma_data,
            dirty_page_summary=dirty_info,
            migration_phase="active" if self._migration_active else "idle",
        )

        self._snapshots.append(snapshot)
        return snapshot

    def get_migration_summary(self) -> dict:
        """Get migration state summary for reporting."""
        return {
            "migration_active": self._migration_active,
            "total_memory_mb": self._memory_size // (1024 * 1024),
            "total_pages": self._total_pages,
            "dirty_page_count": self._dirty_count,
            "iteration": self._iteration,
            "snapshots_created": len(self._snapshots),
            "bitmap_convention": "inverted_kvm",
            "dirty_ratio": self._dirty_count / self._total_pages
                if self._total_pages > 0 else 0.0,
        }

    def serialize_state(self) -> str:
        """Serialize current migration state to JSON string."""
        state = {
            "migration_summary": self.get_migration_summary(),
            "latest_snapshot": None,
        }
        if self._snapshots:
            snap = self._snapshots[-1]
            state["latest_snapshot"] = {
                "snapshot_id": snap.snapshot_id,
                "timestamp": snap.timestamp,
                "migration_phase": snap.migration_phase,
                "dirty_page_summary": snap.dirty_page_summary,
            }
        return json.dumps(state, indent=2)
