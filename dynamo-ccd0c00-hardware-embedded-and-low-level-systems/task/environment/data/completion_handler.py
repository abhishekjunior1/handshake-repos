"""Completion Handler — Interrupt generation and status register management.

Manages DMA transfer completion events, error detection, and interrupt
status register updates. Implements write-1-to-clear semantics for
interrupt acknowledgment per ARM/AXI interrupt controller convention.
"""


def generate_completion_status(channel_id, bytes_transferred, total_size,
                                burst_size, preempted):
    """Generate transfer completion status for a channel.

    Args:
        channel_id: DMA channel identifier.
        bytes_transferred: Bytes successfully transferred this cycle.
        total_size: Total transfer size requested.
        burst_size: Burst size used for transfer.
        preempted: Whether transfer was preempted.

    Returns:
        Dict with completion status, progress, and error flags.
    """
    complete = bytes_transferred >= total_size and not preempted
    progress = min(1.0, bytes_transferred / total_size) if total_size > 0 else 0.0

    # Check for transfer errors
    error = False
    error_code = 0

    if bytes_transferred > total_size:
        error = True
        error_code = 0x01  # Overrun
    elif burst_size > total_size and total_size > 0:
        error = True
        error_code = 0x02  # Burst exceeds transfer

    return {
        "channel_id": channel_id,
        "complete": complete,
        "progress": round(progress, 6),
        "bytes_transferred": bytes_transferred,
        "error": error,
        "error_code": error_code,
        "preempted": preempted
    }


def update_interrupt_status(channel_id, transfer_complete, error, current_status):
    """Update interrupt status register using write-1-to-clear convention.

    In ARM/AXI interrupt controllers, software acknowledges a pending
    interrupt by writing 1 to the corresponding status bit. The hardware
    clears the bit when a 1 is written. Setting a new interrupt is done
    by the hardware asserting the bit.

    This function SETS the interrupt bit for the channel (hardware assertion).
    Clearing happens when software writes 1 to acknowledge.

    Args:
        channel_id: Channel that triggered the interrupt.
        transfer_complete: Whether transfer completed successfully.
        error: Whether an error occurred.
        current_status: Current interrupt status register value.

    Returns:
        Updated interrupt status register value.
    """
    # Set the channel's completion bit (hardware assertion)
    channel_bit = 1 << channel_id

    # Set completion interrupt
    if transfer_complete:
        current_status |= channel_bit

    # Set error interrupt in upper half of register
    if error:
        error_bit = 1 << (channel_id + 16)
        current_status |= error_bit

    return current_status


def acknowledge_interrupt(status_register, ack_value):
    """Process interrupt acknowledgment (write-1-to-clear).

    Software writes a value with bits set for each interrupt to acknowledge.
    The hardware clears those bits from the status register.

    Args:
        status_register: Current interrupt status register.
        ack_value: Value written by software (1s indicate bits to clear).

    Returns:
        Updated status register with acknowledged bits cleared.
    """
    # Write-1-to-clear: bits that are 1 in ack_value get CLEARED
    return status_register & ~ack_value


def compute_interrupt_latency(channel_id, cycle, config):
    """Estimate interrupt delivery latency based on controller configuration.

    Args:
        channel_id: Channel generating the interrupt.
        cycle: Current bus cycle count.
        config: Controller configuration.

    Returns:
        Estimated latency in bus cycles.
    """
    base_latency = config.get("interrupt_latency_cycles", 4)
    priority_penalty = channel_id  # Lower channels get faster delivery
    arbitration_delay = config.get("arbitration_cycles", 2)

    total_latency = base_latency + priority_penalty + arbitration_delay
    return total_latency


def check_error_threshold(channel_stats, max_errors=3):
    """Check if a channel has exceeded the error threshold.

    Args:
        channel_stats: Dict with error counts per channel.
        max_errors: Maximum allowed errors before channel disable.

    Returns:
        List of channel_ids that should be disabled.
    """
    disabled = []
    for ch_id, stats in channel_stats.items():
        if stats.get("error_count", 0) >= max_errors:
            disabled.append(ch_id)
    return disabled


def format_status_register(status_value):
    """Format interrupt status register for human-readable display.

    Args:
        status_value: Integer status register value.

    Returns:
        Dict with completion_bits, error_bits, and raw hex value.
    """
    completion_bits = status_value & 0xFFFF
    error_bits = (status_value >> 16) & 0xFFFF

    active_completions = []
    active_errors = []

    for i in range(16):
        if completion_bits & (1 << i):
            active_completions.append(i)
        if error_bits & (1 << i):
            active_errors.append(i)

    return {
        "raw_hex": f"0x{status_value:08x}",
        "completion_channels": active_completions,
        "error_channels": active_errors,
        "any_pending": status_value != 0
    }
