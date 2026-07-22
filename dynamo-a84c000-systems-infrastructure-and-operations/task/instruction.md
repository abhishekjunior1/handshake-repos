You are debugging a virtio device hotplug controller pipeline that orchestrates device initialization in a KVM/QEMU virtualization environment. The pipeline coordinates capability negotiation, virtqueue setup, IOMMU DMA mapping, and live migration preparation for hotplugged virtio devices.

The codebase is at `/app/` with the following modules:

- `/app/pipeline.py` — orchestrator driving the hotplug lifecycle
- `/app/capability_negotiator.py` — virtio feature bit negotiation between host and guest
- `/app/queue_manager.py` — virtqueue descriptor ring allocation and interrupt setup
- `/app/dma_mapper.py` — IOMMU page table mapping and scatter-gather translation
- `/app/device_registry.py` — device state machine tracking lifecycle transitions
- `/app/migration_serializer.py` — dirty page tracking and state serialization
- `/app/hotplug_reporter.py` — output JSON formatting

The pipeline reads `/app/input.json` and writes results to `/app/output.json`.

The pipeline produces correct output on the current configuration. There are bugs that manifest under different hardware/guest configurations. Fix the pipeline so it produces correct output for any valid configuration.

Important: the device registry stores state transitions internally in reverse-chronological order (index 0 = newest) for O(1) current-state access; the emitted `state_history` field in output is chronological (oldest to newest) and is already correct — do not change the output ordering or the internal storage convention. Preserve the inverted dirty page bitmap convention in migration serialization (1=clean, 0=dirty per KVM hardware dirty log compatibility).

The output JSON has this structure:
```json
{
  "pipeline_status": "completed",
  "stages": {
    "device_registry": {
      "device_count": <int>,
      "devices": { "<device_id>": { "device_id": <str>, "device_type": <str>, "vendor_id": <int>, "current_state": <str>, "transition_count": <int>, "state_history": [<str>...], "properties": {...} } },
      "total_transitions": <int>
    },
    "capability_negotiation": {
      "host_feature_count": <int>, "guest_feature_count": <int>, "negotiated_feature_count": <int>, "rejected_feature_count": <int>,
      "host_features": [<int>...], "guest_features": [<int>...], "negotiated_features": [<int>...], "rejected_features": [<int>...],
      "feature_names": { "<bit>": "<name>" }
    },
    "queue_configuration": {
      "configured": <bool>, "num_queues": <int>, "base_depth": <int>, "effective_depth": <int>,
      "queues": [{ "queue_index": <int>, "ring_size": <int>, "descriptor_table_addr": <hex_str>, "avail_ring_addr": <hex_str>, "used_ring_addr": <hex_str>, "interrupt_vector": <int>, "avail_idx": <int>, "used_idx": <int>, "descriptors_in_flight": <int>, "total_submitted": <int> }],
      "submission_result": { "queue_index": <int>, "submitted": <int>, "current_avail_idx": <int>, "descriptors_in_flight": <int>, "submissions": [{"avail_idx": <int>, "ring_position": <int>}] }
    },
    "dma_mappings": {
      "iommu_enabled": <bool>, "guest_page_size": <int>, "host_page_size": <int>, "total_regions": <int>, "total_mappings": <int>, "total_mapped_bytes": <int>,
      "regions": [{ "guest_start": <hex_str>, "host_start": <hex_str>, "size": <int>, "page_count": <int>, "mapping_page_size": <int>, "iova_start": <hex_str>, "iova_end": <hex_str> }]
    },
    "migration_state": {
      "migration_active": <bool>, "total_memory_mb": <int>, "total_pages": <int>, "dirty_page_count": <int>, "iteration": <int>, "snapshots_created": <int>, "bitmap_convention": <str>, "dirty_ratio": <float>
    }
  }
}
```

Run the pipeline: `cd /app && python3 pipeline.py`
