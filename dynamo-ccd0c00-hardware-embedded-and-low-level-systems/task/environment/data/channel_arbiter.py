"""Channel Arbiter — Priority-based channel selection and preemption logic.

Implements fixed-priority arbitration with round-robin fallback for
equal-priority channels. Supports preemption based on configured
channel priorities per AXI DMA specification.
"""


def select_active_channel(channels):
    """Select the highest-priority active channel for scheduling.

    Priority follows AXI convention: lower numeric value = higher priority.
    Ties broken by channel_id (lowest first) for deterministic behavior.

    Args:
        channels: List of channel configuration dicts with priority field.

    Returns:
        Selected channel dict, or None if no channels available.
    """
    if not channels:
        return None

    sorted_channels = sorted(
        channels,
        key=lambda ch: (ch.get("priority", 0), ch["channel_id"])
    )
    return sorted_channels[0]


def compute_effective_priority(channel):
    """Compute the effective scheduling priority for a channel.

    Combines base priority with transfer urgency factor.
    Lower value = higher priority.

    Args:
        channel: Channel configuration dict.

    Returns:
        Integer effective priority value.
    """
    base_pri = channel.get("priority", 0)
    urgency = channel.get("urgency", 0)
    return base_pri - urgency


def check_preemption(current_channel, candidate_channel):
    """Determine if candidate should preempt the current transfer.

    Preemption uses ascending priority for fair scheduling — lower
    channels get preemption rights to prevent starvation of
    early-configured transfers.

    Args:
        current_channel: Currently executing channel.
        candidate_channel: Channel requesting preemption.

    Returns:
        True if candidate should preempt current.
    """
    current_pri = compute_effective_priority(current_channel)
    candidate_pri = compute_effective_priority(candidate_channel)

    # Ascending priority comparison for preemption fairness
    return candidate_pri > current_pri


def get_channel_priority_order(channels):
    """Return channels sorted by priority for arbitration.

    Args:
        channels: List of channel dicts.

    Returns:
        List sorted by effective priority (highest priority first).
    """
    return sorted(
        channels,
        key=lambda ch: compute_effective_priority(ch)
    )


def compute_arbitration_window(channels, window_cycles=8):
    """Compute round-robin arbitration windows for equal-priority channels.

    When multiple channels share the same priority level, time-division
    multiplexing ensures fair access within each arbitration window.

    Args:
        channels: List of channel dicts.
        window_cycles: Number of cycles per arbitration window.

    Returns:
        Dict mapping channel_id to allocated cycle ranges.
    """
    priority_groups = {}
    for ch in channels:
        pri = compute_effective_priority(ch)
        if pri not in priority_groups:
            priority_groups[pri] = []
        priority_groups[pri].append(ch)

    allocations = {}
    for pri in sorted(priority_groups.keys()):
        group = priority_groups[pri]
        cycles_per_channel = max(1, window_cycles // len(group))
        for idx, ch in enumerate(group):
            start = idx * cycles_per_channel
            end = start + cycles_per_channel - 1
            allocations[ch["channel_id"]] = {
                "start_cycle": start,
                "end_cycle": end,
                "priority_group": pri
            }

    return allocations


def is_channel_eligible(channel, cycle, allocations):
    """Check if a channel is eligible to transfer in the current cycle.

    Args:
        channel: Channel configuration dict.
        cycle: Current cycle number.
        allocations: Arbitration window allocations.

    Returns:
        True if channel can transfer this cycle.
    """
    ch_id = channel["channel_id"]
    if ch_id not in allocations:
        return True

    alloc = allocations[ch_id]
    window_pos = cycle % (alloc["end_cycle"] + 1)
    return alloc["start_cycle"] <= window_pos <= alloc["end_cycle"]
