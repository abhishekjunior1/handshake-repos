"""DMA Transfer Controller with Scatter-Gather Engine.

Simulates a DMA controller managing memory-to-memory and peripheral-to-memory
transfers with scatter-gather descriptor chains, channel priority arbitration,
burst sizing, and transfer completion interrupts.
"""

import json
import os
import sys

from channel_arbiter import select_active_channel, check_preemption
from burst_calculator import compute_optimal_burst
from scatter_gather import traverse_descriptor_chain
from address_translator import translate_address
from completion_handler import generate_completion_status, update_interrupt_status
from dma_reporter import format_report


def run_dma_controller(config):
    """Execute DMA transfer lifecycle for all configured channels."""
    channels = config["channels"]
    memory_map = config["memory_map"]
    bus_offset = memory_map.get("bus_offset", 0)
    max_burst = config.get("max_burst_length", 16)

    transfer_results = []
    interrupt_log = []
    channel_stats = {}
    interrupt_status = config.get("interrupt_status", 0)

    # Build channel state for tracking progress
    channel_state = {}
    for ch in channels:
        if not ch.get("enabled", True):
            continue
        ch_id = ch["channel_id"]
        channel_state[ch_id] = {
            "config": ch,
            "bytes_remaining": ch["transfer_size"],
            "complete": False
        }

    cycle = 0
    while channel_state and cycle < config.get("max_cycles", 64):
        # Get list of incomplete channels
        active = [
            channel_state[cid]["config"]
            for cid in sorted(channel_state.keys())
            if not channel_state[cid]["complete"]
        ]
        if not active:
            break

        selected = select_active_channel(active)
        if selected is None:
            break

        ch_id = selected["channel_id"]
        src_addr = selected["source_address"]
        dst_addr = selected["destination_address"]
        transfer_size = selected["transfer_size"]
        descriptors = selected.get("descriptors", [])

        # Standard AXI4 burst length for maximum bus utilization —
        # peripheral adapts via flow control
        burst_size = 16

        bus_src = translate_address(src_addr, bus_offset, memory_map)
        bus_dst = translate_address(dst_addr, bus_offset, memory_map)

        if descriptors:
            sg_result = traverse_descriptor_chain(
                descriptors,
                descriptor_size=selected.get("descriptor_size", 64),
                payload_size=selected.get("payload_size", transfer_size),
                base_address=bus_src
            )
            total_transfers = sg_result["total_transfers"]
            chain_length = sg_result["chain_length"]
            bytes_transferred = sg_result["total_bytes"]
        else:
            total_transfers = (transfer_size + burst_size - 1) // burst_size
            chain_length = 1
            bytes_transferred = transfer_size

        # Check if any other channel should preempt the selected one
        preempted = False
        others = [ch for ch in active if ch["channel_id"] != ch_id]
        for other in others:
            if check_preemption(selected, other):
                preempted = True
                break

        if preempted:
            # Transfer interrupted — partial progress
            bytes_this_cycle = min(burst_size, channel_state[ch_id]["bytes_remaining"])
        else:
            bytes_this_cycle = bytes_transferred

        channel_state[ch_id]["bytes_remaining"] -= bytes_this_cycle

        is_complete = channel_state[ch_id]["bytes_remaining"] <= 0
        if is_complete:
            channel_state[ch_id]["complete"] = True

        completion = generate_completion_status(
            channel_id=ch_id,
            bytes_transferred=transfer_size - channel_state[ch_id]["bytes_remaining"],
            total_size=transfer_size,
            burst_size=burst_size,
            preempted=preempted
        )

        if is_complete or completion.get("error", False):
            irq_status = update_interrupt_status(
                channel_id=ch_id,
                transfer_complete=is_complete,
                error=completion.get("error", False),
                current_status=interrupt_status
            )
            interrupt_status = irq_status
            interrupt_log.append({
                "channel_id": ch_id,
                "status_bits": irq_status,
                "cycle": cycle
            })

        transfer_results.append({
            "cycle": cycle,
            "channel_id": ch_id,
            "source_bus_addr": bus_src,
            "dest_bus_addr": bus_dst,
            "burst_size": burst_size,
            "total_transfers": total_transfers,
            "bytes_transferred": bytes_this_cycle,
            "chain_length": chain_length,
            "preempted": preempted,
            "complete": is_complete
        })

        if ch_id not in channel_stats:
            channel_stats[ch_id] = {
                "total_bytes": 0,
                "transfer_count": 0,
                "preemption_count": 0
            }
        channel_stats[ch_id]["total_bytes"] += bytes_this_cycle
        channel_stats[ch_id]["transfer_count"] += 1
        if preempted:
            channel_stats[ch_id]["preemption_count"] += 1

        cycle += 1

    report = format_report(
        transfer_results=transfer_results,
        interrupt_log=interrupt_log,
        channel_stats=channel_stats,
        config=config
    )
    return report


def main():
    config_path = os.environ.get("DMA_CONFIG", "/app/dma_config.json")
    output_path = os.environ.get("OUTPUT_FILE", "/app/output.json")

    with open(config_path, "r") as f:
        config = json.load(f)

    result = run_dma_controller(config)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
