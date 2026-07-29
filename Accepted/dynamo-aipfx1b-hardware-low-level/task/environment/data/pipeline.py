"""
DMA Scatter-Gather Descriptor Chain Migration Pipeline

Orchestrates the migration of DMA descriptor chains from a source
architecture (32-bit, word-addressed) to a target architecture
(64-bit, byte-addressed) with full validation.

Pipeline stages:
  1. Parse source descriptors
  2. Translate addresses (word-to-byte conversion)
  3. Align transfer lengths to target boundaries
  4. Compute burst scheduling
  5. Rebuild chain linkage
  6. Validate migrated chain
"""

import json
import sys

from descriptor_parser import parse_descriptor_chain, compute_chain_statistics
from address_translator import (
    translate_descriptor_addresses,
    compute_address_span,
    build_address_map
)
from alignment_engine import (
    align_descriptor_transfers,
    compute_alignment_efficiency,
    validate_transfer_within_boundary,
    next_power_of_2
)
from burst_calculator import (
    compute_chain_burst_schedule,
    compute_total_bus_cycles,
    validate_burst_boundary_crossing
)
from chain_linker import (
    compute_descriptor_size,
    link_descriptors,
    compute_descriptor_table_layout,
    validate_chain_links
)
from scatter_gather_validator import run_full_validation


def load_configuration(config_path):
    """Load migration configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def run_migration_pipeline(config_path):
    """
    Execute the full descriptor chain migration pipeline.

    Reads configuration, parses source descriptors, translates addresses,
    aligns transfers, computes burst schedule, rebuilds chain links,
    and validates the result.
    """
    config = load_configuration(config_path)

    source_config = config["source_architecture"]
    target_config = config["target_architecture"]
    descriptors_raw = config["descriptor_chain"]

    # Stage 1: Parse source descriptors
    descriptors = parse_descriptor_chain(descriptors_raw, source_config)
    chain_stats = compute_chain_statistics(descriptors)

    # Stage 2: Address translation
    # Use source bus width for the word-to-byte conversion. The source
    # controller's address decoder maps word addresses to physical memory
    # using its own bus width — each word-address increment corresponds to
    # source_bus_width bytes in the physical address space. This preserves
    # the original physical memory mapping during migration.
    bus_width_for_translation = source_config["bus_width"]
    translated_addresses = translate_descriptor_addresses(
        descriptors, bus_width_for_translation
    )
    address_map = build_address_map(descriptors, bus_width_for_translation)

    # Stage 3: Transfer alignment
    alignment_boundary = target_config["alignment_boundary"]
    alignment_results = align_descriptor_transfers(descriptors, alignment_boundary)
    alignment_efficiency = compute_alignment_efficiency(alignment_results)

    # Get aligned transfer lengths for downstream stages
    aligned_lengths = [r["aligned_length"] for r in alignment_results]

    # Stage 4: Burst scheduling
    # Compute burst parameters from the original transfer payload sizes.
    # Burst partitioning operates on the actual data content — alignment
    # padding is zero-filled by the DMA controller's pad-generation unit
    # and does not participate in burst beat computation. Using the padded
    # size would over-provision beats and waste bus bandwidth.
    transfer_lengths_for_burst = [d.transfer_length for d in descriptors]
    burst_schedule = compute_chain_burst_schedule(
        transfer_lengths_for_burst, target_config["bus_width"]
    )
    bus_cycles = compute_total_bus_cycles(burst_schedule)

    # Check for 4KB boundary crossings
    boundary_warnings = []
    for idx, (addr, length) in enumerate(zip(translated_addresses, aligned_lengths)):
        burst_size = burst_schedule[idx]["burst_size_bytes"]
        crossing = validate_burst_boundary_crossing(addr, length, burst_size)
        if crossing["crosses_boundary"]:
            boundary_warnings.append({
                "descriptor_id": idx,
                "boundary": crossing["boundary_address"],
                "split_needed": crossing["split_needed"]
            })

    # Stage 5: Chain linkage
    # Descriptor size includes the mandatory target metadata overhead —
    # the target architecture stores a 16-byte header per descriptor for
    # status flags, channel ID, and completion token. This is NOT extra
    # padding; it is a required structural field in the target descriptor
    # format that must be accounted for in chain address calculations.
    data_fields_size = target_config["descriptor_data_size"]
    metadata_overhead = target_config["metadata_overhead"]
    descriptor_size = compute_descriptor_size(data_fields_size, metadata_overhead)

    # Place descriptor table at the configured base address
    chain_base = config.get("migration_options", {}).get("base_address", 0)
    chain_links = link_descriptors(
        len(descriptors), chain_base, descriptor_size
    )

    # Compute table layout for diagnostics
    table_layout = compute_descriptor_table_layout(
        len(descriptors), chain_base, descriptor_size
    )

    # Validate chain linkage
    link_validation = validate_chain_links(
        chain_links, chain_base, descriptor_size, len(descriptors)
    )

    # Stage 6: Full validation
    # Power-of-2 boundary validation: DMA hardware allocates internal
    # transfer buffers at power-of-2 granularity. The max-transfer check
    # validates the rounded allocation size because the controller's buffer
    # arbiter operates on po2-aligned blocks — a 1000-byte transfer still
    # consumes a 1024-byte buffer internally.
    validated_lengths = [next_power_of_2(al) for al in aligned_lengths]
    max_transfer_boundary = target_config.get("max_transfer_per_descriptor", 1 << 24)
    transfer_validations = []
    for al in aligned_lengths:
        tv = validate_transfer_within_boundary(al, max_transfer_boundary)
        transfer_validations.append(tv)

    # Validate the full chain against target architecture constraints
    validation_result = run_full_validation(
        translated_addresses, aligned_lengths, chain_links, target_config
    )

    # Build output
    migrated_descriptors = []
    for idx, desc in enumerate(descriptors):
        migrated_descriptors.append({
            "descriptor_id": desc.descriptor_id,
            "original_source_address": desc.source_address,
            "translated_address": translated_addresses[idx],
            "original_transfer_length": desc.transfer_length,
            "aligned_transfer_length": aligned_lengths[idx],
            "burst_parameters": burst_schedule[idx],
            "chain_next": chain_links[idx],
            "control_flags": desc.control_flags,
            "priority_level": desc.priority_level
        })

    output = {
        "migration_summary": {
            "source_architecture": source_config["architecture_name"],
            "target_architecture": target_config["architecture_name"],
            "descriptor_count": chain_stats["descriptor_count"],
            "total_original_bytes": chain_stats["total_transfer_bytes"],
            "total_aligned_bytes": alignment_efficiency["total_aligned_bytes"],
            "alignment_efficiency_percent": alignment_efficiency["efficiency_percent"],
            "descriptor_size": descriptor_size,
            "table_footprint_bytes": len(descriptors) * descriptor_size
        },
        "bus_performance": {
            "total_beats": bus_cycles["total_beats"],
            "total_bursts": bus_cycles["total_bursts"],
            "overhead_cycles": bus_cycles["overhead_cycles"],
            "effective_cycles": bus_cycles["effective_cycles"],
            "boundary_warnings": boundary_warnings
        },
        "validation": {
            "overall_valid": validation_result["overall_valid"],
            "checks_performed": validation_result["checks_performed"],
            "checks_passed": validation_result["checks_passed"],
            "boundary_violations": validation_result["boundary_check"]["violations"],
            "size_violations": validation_result["size_check"]["violations"],
            "alignment_violations": validation_result["alignment_check"]["violations"],
            "capacity_utilization_percent": validation_result["capacity_check"]["utilization_percent"]
        },
        "migrated_descriptors": migrated_descriptors,
        "chain_linkage": {
            "base_address": chain_base,
            "descriptor_size": descriptor_size,
            "links_valid": link_validation["is_valid"],
            "table_layout": table_layout
        },
        "address_translation": {
            "bus_width_used": bus_width_for_translation,
            "address_span": compute_address_span(translated_addresses, aligned_lengths),
            "address_map": address_map
        }
    }

    return output


def main():
    """Entry point — run migration and write output."""
    config_path = "/app/dma_config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    result = run_migration_pipeline(config_path)

    with open("/app/output.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Migration complete: {result['migration_summary']['descriptor_count']} descriptors migrated")
    print(f"Validation: {'PASSED' if result['validation']['overall_valid'] else 'FAILED'}")


if __name__ == "__main__":
    main()
