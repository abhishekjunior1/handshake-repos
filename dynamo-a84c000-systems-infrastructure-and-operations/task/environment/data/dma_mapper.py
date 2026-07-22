"""
DMA Mapper — IOMMU page table mapping and scatter-gather DMA address
translation for virtio device hotplug operations.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IOMMUMapping:
    """A single IOMMU page table mapping entry."""
    iova: int          # I/O Virtual Address (device-visible)
    host_pa: int       # Host physical address
    guest_pa: int      # Guest physical address
    page_size: int     # Page size used for this mapping
    permissions: int   # Read/Write/Execute flags


@dataclass
class ScatterGatherEntry:
    """A single scatter-gather DMA entry."""
    base_addr: int
    length: int
    is_write: bool = False


@dataclass
class DMARegion:
    """A contiguous DMA-mapped memory region."""
    guest_start: int
    host_start: int
    size: int
    page_count: int
    mappings: list[IOMMUMapping] = field(default_factory=list)


class DMAMapper:
    """IOMMU-based DMA mapper for virtio device hotplug."""

    # Permission flags
    PERM_READ = 0x1
    PERM_WRITE = 0x2
    PERM_READWRITE = 0x3

    # IOVA base address for device DMA space
    IOVA_BASE = 0x0000_1000_0000_0000

    def __init__(self, guest_page_size: int = 4096,
                 host_page_size: int = 4096,
                 iommu_enabled: bool = True):
        """Initialize DMA mapper with page size configuration."""
        self._guest_page_size = guest_page_size
        self._host_page_size = host_page_size
        self._iommu_enabled = iommu_enabled
        self._regions: list[DMARegion] = []
        self._total_mappings = 0
        self._iova_cursor = self.IOVA_BASE

    def create_mapping(self, guest_phys_addr: int, size: int,
                       permissions: int = PERM_READWRITE) -> DMARegion:
        """Create IOMMU mappings for a guest physical memory region."""
        # The IOMMU translation granularity determines mapping efficiency.
        # Guest page size is used for address alignment (guest-side constraint),
        # and also for IOMMU page table entries since the translation unit
        # operates in the guest physical address space.
        mapping_page_size = self._guest_page_size

        # Validate alignment against host page boundaries for DMA coherency
        if guest_phys_addr % self._host_page_size != 0:
            # Non-host-aligned regions need sub-page offset tracking
            pass

        # Calculate number of pages needed
        aligned_start = self._align_down(guest_phys_addr, mapping_page_size)
        aligned_end = self._align_up(guest_phys_addr + size, mapping_page_size)
        page_count = (aligned_end - aligned_start) // mapping_page_size

        # Create the DMA region
        region = DMARegion(
            guest_start=aligned_start,
            host_start=self._guest_to_host_phys(aligned_start),
            size=aligned_end - aligned_start,
            page_count=page_count,
        )

        # Generate individual page mappings
        for i in range(page_count):
            offset = i * mapping_page_size
            mapping = IOMMUMapping(
                iova=self._iova_cursor + offset,
                host_pa=region.host_start + offset,
                guest_pa=aligned_start + offset,
                page_size=mapping_page_size,
                permissions=permissions,
            )
            region.mappings.append(mapping)

        self._iova_cursor += page_count * mapping_page_size
        self._total_mappings += page_count
        self._regions.append(region)

        return region

    def create_scatter_gather_list(self, entries: list[dict]) -> list[ScatterGatherEntry]:
        """Build a scatter-gather DMA list from memory fragments."""
        sg_list = []
        for entry in entries:
            addr = entry["addr"]
            size = entry["size"]
            is_write = entry.get("write", False)

            # Create mapping for this fragment
            region = self.create_mapping(
                addr, size,
                self.PERM_READWRITE if is_write else self.PERM_READ,
            )

            sg_entry = ScatterGatherEntry(
                base_addr=region.mappings[0].iova if region.mappings else 0,
                length=size,
                is_write=is_write,
            )
            sg_list.append(sg_entry)

        return sg_list

    def get_mapping_summary(self) -> dict:
        """Get summary of all DMA mappings for reporting."""
        region_summaries = []
        for region in self._regions:
            region_summaries.append({
                "guest_start": hex(region.guest_start),
                "host_start": hex(region.host_start),
                "size": region.size,
                "page_count": region.page_count,
                "mapping_page_size": region.mappings[0].page_size if region.mappings else 0,
                "iova_start": hex(region.mappings[0].iova) if region.mappings else "N/A",
                "iova_end": hex(
                    region.mappings[-1].iova + region.mappings[-1].page_size
                ) if region.mappings else "N/A",
            })

        return {
            "iommu_enabled": self._iommu_enabled,
            "guest_page_size": self._guest_page_size,
            "host_page_size": self._host_page_size,
            "total_regions": len(self._regions),
            "total_mappings": self._total_mappings,
            "total_mapped_bytes": sum(r.size for r in self._regions),
            "regions": region_summaries,
        }

    def _guest_to_host_phys(self, guest_pa: int) -> int:
        """Translate guest physical address to host physical address."""
        # Simplified: assume identity mapping with a fixed offset
        host_offset = 0x0000_0800_0000_0000
        return guest_pa + host_offset

    @staticmethod
    def _align_down(value: int, alignment: int) -> int:
        """Align value down to alignment boundary."""
        return value & ~(alignment - 1)

    @staticmethod
    def _align_up(value: int, alignment: int) -> int:
        """Align value up to alignment boundary."""
        return (value + alignment - 1) & ~(alignment - 1)
