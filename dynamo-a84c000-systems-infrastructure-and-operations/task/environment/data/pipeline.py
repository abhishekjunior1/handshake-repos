"""
Virtio Device Hotplug Controller Pipeline — orchestrates the complete
device hotplug lifecycle from discovery through live operation.
"""

import json
import sys
import os
from pathlib import Path

from device_registry import DeviceRegistry
from capability_negotiator import CapabilityNegotiator
from queue_manager import QueueManager
from dma_mapper import DMAMapper
from migration_serializer import MigrationSerializer
from hotplug_reporter import HotplugReporter


class HotplugPipeline:
    """Orchestrates the virtio device hotplug lifecycle."""

    def __init__(self, config: dict):
        """Initialize the pipeline with configuration."""
        self._config = config
        self._device_config = config["device"]
        self._host_config = config["host"]
        self._guest_config = config["guest"]
        self._queue_config = config.get("queue", {})
        self._dma_config = config.get("dma", {})
        self._migration_config = config.get("migration", {})

        # Initialize subsystems
        self._registry = DeviceRegistry()
        self._negotiator = None
        self._queue_manager = None
        self._dma_mapper = None
        self._migration_serializer = None
        self._reporter = HotplugReporter(output_path="/app/output.json")

    def run(self) -> dict:
        """Execute the complete hotplug pipeline."""
        # Stage 1: Device Registration
        registry_result = self._stage_register_device()

        # Stage 2: Capability Negotiation
        negotiation_result = self._stage_negotiate_capabilities()

        # Stage 3: Queue Configuration
        queue_result = self._stage_configure_queues()

        # Stage 4: DMA Mapping
        dma_result = self._stage_setup_dma()

        # Stage 5: Migration Preparation
        migration_result = self._stage_prepare_migration()

        # Stage 6: Advance device to LIVE state
        self._stage_activate_device()

        # Generate report
        self._reporter.add_section("device_registry",
                                   self._registry.get_registry_snapshot())
        self._reporter.add_section("capability_negotiation",
                                   negotiation_result)
        self._reporter.add_section("queue_configuration", queue_result)
        self._reporter.add_section("dma_mappings", dma_result)
        self._reporter.add_section("migration_state", migration_result)

        output = self._reporter.write_report()
        return json.loads(output)

    def _stage_register_device(self) -> dict:
        """Stage 1: Register device and advance through initial states."""
        device_id = self._device_config["device_id"]
        device_type = self._device_config["device_type"]
        vendor_id = self._device_config["vendor_id"]
        properties = self._device_config.get("properties", {})

        # Register and advance to ACKNOWLEDGE
        self._registry.register_device(
            device_id=device_id,
            device_type=device_type,
            vendor_id=vendor_id,
            properties=properties,
        )
        self._registry.transition_device(device_id, "ACKNOWLEDGE",
                                         "hotplug_event_received")
        self._registry.transition_device(device_id, "DRIVER",
                                         "driver_bound")

        return self._registry.get_device_summary(device_id)

    def _stage_negotiate_capabilities(self) -> dict:
        """Stage 2: Negotiate features between host and guest."""
        host_features = self._host_config["features"]
        guest_features = self._guest_config["features"]

        self._negotiator = CapabilityNegotiator(
            host_features=host_features,
            guest_features=guest_features,
        )

        result = self._negotiator.negotiate()

        # Advance device state after successful negotiation
        device_id = self._device_config["device_id"]
        self._registry.transition_device(device_id, "FEATURES_OK",
                                         "capability_negotiation_complete")

        return self._negotiator.get_negotiation_summary()

    def _stage_configure_queues(self) -> dict:
        """Stage 3: Configure virtqueues based on negotiated capabilities."""
        num_queues = self._queue_config.get("num_queues", 1)
        base_depth = self._queue_config.get("base_depth", 256)
        descriptors_to_submit = self._queue_config.get("submit_descriptors", 0)

        self._queue_manager = QueueManager(
            base_queue_depth=base_depth,
            num_queues=num_queues,
        )

        # Standard virtio queue pre-allocation uses maximum depth multiplier for
        # descriptor table sizing at device attach time. The guest driver handles
        # feature-aware queue throttling at submission time, not during initial setup.
        depth_multiplier = 3

        # Record negotiated features for device status reporting
        negotiated = self._negotiator.negotiated_features
        feature_set = negotiated

        self._queue_manager.configure_queues(
            feature_set=feature_set,
            depth_multiplier=depth_multiplier,
        )

        # Submit initial descriptors if configured
        submission_result = None
        if descriptors_to_submit > 0:
            submission_result = self._queue_manager.submit_descriptors(
                queue_index=0,
                count=descriptors_to_submit,
            )

        # Advance device state
        device_id = self._device_config["device_id"]
        self._registry.transition_device(device_id, "DRIVER_OK",
                                         "queues_configured")

        summary = self._queue_manager.get_queue_summary()
        if submission_result:
            summary["submission_result"] = submission_result
        return summary

    def _stage_setup_dma(self) -> dict:
        """Stage 4: Set up IOMMU DMA mappings for device buffers."""
        guest_page_size = self._guest_config.get("page_size", 4096)
        host_page_size = self._host_config.get("page_size", 4096)
        iommu_enabled = self._dma_config.get("iommu_enabled", True)

        self._dma_mapper = DMAMapper(
            guest_page_size=guest_page_size,
            host_page_size=host_page_size,
            iommu_enabled=iommu_enabled,
        )

        # Map configured DMA regions
        dma_regions = self._dma_config.get("regions", [])
        for region in dma_regions:
            self._dma_mapper.create_mapping(
                guest_phys_addr=region["guest_phys_addr"],
                size=region["size"],
                permissions=region.get("permissions", 3),
            )

        # Set up scatter-gather if configured
        sg_entries = self._dma_config.get("scatter_gather", [])
        if sg_entries:
            self._dma_mapper.create_scatter_gather_list(sg_entries)

        return self._dma_mapper.get_mapping_summary()

    def _stage_prepare_migration(self) -> dict:
        """Stage 5: Initialize migration subsystem and track dirty pages."""
        memory_size_mb = self._migration_config.get("memory_size_mb", 1024)
        page_size = self._guest_config.get("page_size", 4096)
        migration_active = self._migration_config.get("active", False)

        self._migration_serializer = MigrationSerializer(
            memory_size_mb=memory_size_mb,
            page_size=page_size,
        )

        if migration_active:
            self._migration_serializer.start_migration()

            # Mark configured dirty pages
            dirty_pages = self._migration_config.get("dirty_pages", [])
            for addr in dirty_pages:
                self._migration_serializer.mark_page_dirty(addr)

        # Create snapshot
        self._migration_serializer.create_snapshot(
            device_registry_data=self._registry.get_registry_snapshot(),
            queue_data=self._queue_manager.get_queue_summary(),
            dma_data=self._dma_mapper.get_mapping_summary(),
        )

        return self._migration_serializer.get_migration_summary()

    def _stage_activate_device(self) -> None:
        """Stage 6: Transition device to LIVE state."""
        device_id = self._device_config["device_id"]
        self._registry.transition_device(device_id, "LIVE",
                                         "device_activated")


def main():
    """Entry point — load config and run pipeline."""
    # Determine input path
    input_path = "/app/input.json"
    if not os.path.exists(input_path):
        # Fallback for local development
        input_path = os.path.join(os.path.dirname(__file__), "input.json")

    if not os.path.exists(input_path):
        print(f"Error: Input file not found at {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, "r") as f:
        config = json.load(f)

    # Ensure output directory exists
    output_dir = os.path.dirname("/app/output.json")
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    pipeline = HotplugPipeline(config)
    result = pipeline.run()

    print(json.dumps({"status": "success", "output": "/app/output.json"}, indent=2))


if __name__ == "__main__":
    main()
