"""DMA Reporter — Formats transfer results into structured output.

Generates a comprehensive JSON report from DMA transfer simulation
results including per-channel statistics, interrupt logs, and
overall controller performance metrics.
"""


def format_report(transfer_results, interrupt_log, channel_stats, config):
    """Format DMA simulation results into output report.

    Args:
        transfer_results: List of per-cycle transfer result dicts.
        interrupt_log: List of interrupt event dicts.
        channel_stats: Dict of per-channel cumulative statistics.
        config: Original DMA configuration.

    Returns:
        Formatted report dict ready for JSON serialization.
    """
    summary = compute_summary(transfer_results, channel_stats)
    formatted_channels = format_channel_stats(channel_stats, config)
    formatted_interrupts = format_interrupt_log(interrupt_log)
    performance = compute_performance_metrics(transfer_results, config)

    return {
        "summary": summary,
        "transfers": transfer_results,
        "channel_statistics": formatted_channels,
        "interrupt_log": formatted_interrupts,
        "performance": performance
    }


def compute_summary(transfer_results, channel_stats):
    """Compute overall transfer summary statistics.

    Args:
        transfer_results: List of per-cycle transfer results.
        channel_stats: Per-channel statistics dict.

    Returns:
        Summary dict with totals and averages.
    """
    total_bytes = sum(stats["total_bytes"] for stats in channel_stats.values())
    total_transfers = sum(stats["transfer_count"] for stats in channel_stats.values())
    total_preemptions = sum(stats["preemption_count"] for stats in channel_stats.values())
    total_cycles = len(transfer_results)

    completed = sum(1 for r in transfer_results if r["complete"])

    avg_burst = (
        sum(r["burst_size"] for r in transfer_results) / total_cycles
        if total_cycles > 0 else 0.0
    )

    return {
        "total_bytes_transferred": total_bytes,
        "total_transfer_operations": total_transfers,
        "total_preemptions": total_preemptions,
        "total_cycles_used": total_cycles,
        "completed_transfers": completed,
        "average_burst_size": round(avg_burst, 2)
    }


def format_channel_stats(channel_stats, config):
    """Format per-channel statistics with configuration context.

    Args:
        channel_stats: Raw per-channel statistics.
        config: Original configuration for enrichment.

    Returns:
        List of formatted channel statistic dicts.
    """
    channels_config = {ch["channel_id"]: ch for ch in config.get("channels", [])}
    formatted = []

    for ch_id in sorted(channel_stats.keys()):
        stats = channel_stats[ch_id]
        ch_config = channels_config.get(ch_id, {})

        formatted.append({
            "channel_id": ch_id,
            "priority": ch_config.get("priority", 0),
            "total_bytes": stats["total_bytes"],
            "transfer_count": stats["transfer_count"],
            "preemption_count": stats["preemption_count"],
            "efficiency": round(
                stats["total_bytes"] / (stats["transfer_count"] * ch_config.get("transfer_size", 1))
                if stats["transfer_count"] > 0 else 0.0,
                4
            )
        })

    return formatted


def format_interrupt_log(interrupt_log):
    """Format interrupt log with human-readable status.

    Args:
        interrupt_log: Raw interrupt event list.

    Returns:
        Formatted interrupt log with decoded status bits.
    """
    formatted = []
    for event in interrupt_log:
        status = event["status_bits"]
        completion_bits = status & 0xFFFF
        error_bits = (status >> 16) & 0xFFFF

        formatted.append({
            "channel_id": event["channel_id"],
            "cycle": event["cycle"],
            "status_hex": f"0x{status:08x}",
            "completion_pending": completion_bits != 0,
            "error_pending": error_bits != 0
        })

    return formatted


def compute_performance_metrics(transfer_results, config):
    """Compute controller performance metrics.

    Args:
        transfer_results: List of transfer results.
        config: DMA configuration.

    Returns:
        Performance metrics dict.
    """
    if not transfer_results:
        return {
            "bus_utilization": 0.0,
            "average_latency_cycles": 0.0,
            "throughput_bytes_per_cycle": 0.0
        }

    total_cycles = len(transfer_results)
    total_bytes = sum(r["bytes_transferred"] for r in transfer_results)
    active_cycles = sum(1 for r in transfer_results if r["bytes_transferred"] > 0)

    bus_utilization = active_cycles / total_cycles if total_cycles > 0 else 0.0
    throughput = total_bytes / total_cycles if total_cycles > 0 else 0.0

    # Average effective latency (cycles per completed transfer)
    completed = [r for r in transfer_results if r["complete"]]
    avg_latency = total_cycles / len(completed) if completed else 0.0

    return {
        "bus_utilization": round(bus_utilization, 4),
        "average_latency_cycles": round(avg_latency, 2),
        "throughput_bytes_per_cycle": round(throughput, 2)
    }
