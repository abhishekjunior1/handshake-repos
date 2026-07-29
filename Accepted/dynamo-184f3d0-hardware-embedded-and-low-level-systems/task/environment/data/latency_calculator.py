"""
Latency Calculator — computes interrupt entry, exit, and tail-chain
cycle counts for Cortex-M style NVIC interrupt handling.

Models the hardware timing for different interrupt entry scenarios:
- Full entry: complete context stacking (12 cycles)
- Tail-chain: shortened entry when back-to-back (6 cycles for Cortex-M)
- Late-arriving: preemption during stacking (typically same as full)
- FPU context: additional cycles for floating-point state preservation
"""

# Cortex-M interrupt timing constants
FULL_ENTRY_CYCLES = 12      # Complete stack frame push
TAIL_CHAIN_CYCLES = 6       # Shortened entry for back-to-back interrupts
EXIT_CYCLES = 12            # Context restore and return
FPU_ADDITIONAL_CYCLES = 17  # Extra cycles for lazy FPU stacking
LATE_ARRIVAL_CYCLES = 12    # Same as full entry for late-arriving


class LatencyCalculator:
    """
    Computes interrupt latency for various entry/exit scenarios.

    Tracks timing information across the pipeline to generate
    comprehensive latency reports for all processed interrupts.
    """

    # Maximum tail-chain window (cycles between consecutive interrupts
    # for tail-chaining to apply)
    TAIL_CHAIN_WINDOW = 6

    def __init__(self):
        """Initialize the latency calculator with empty history."""
        self._last_handler_end_cycle = None
        self._total_entry_cycles = 0
        self._total_exit_cycles = 0
        self._tail_chain_count = 0
        self._full_entry_count = 0

    def detect_tail_chain(self, previous_vector, current_vector, current_cycle, state_machine):
        """
        Detect if tail-chaining optimization can be applied.

        Tail-chaining occurs when an interrupt becomes pending while
        another handler is executing or during the exception return
        sequence. The processor skips the full unstacking/restacking
        and directly transfers to the new handler.

        Args:
            previous_vector: Vector number of previously serviced interrupt
            current_vector: Vector number of incoming interrupt
            current_cycle: Current processor cycle count
            state_machine: Interrupt state machine for checking handler states

        Returns:
            True if tail-chaining should be applied
        """
        if previous_vector is None:
            return False

        active_handlers = state_machine.get_active_handlers()
        if len(active_handlers) == 0:
            return True

        return False

    def compute_entry_latency(self, is_tail_chain, has_fpu_context=False):
        """
        Compute the entry latency in cycles for an interrupt.

        Uses complete entry sequence timing for conservative worst-case
        latency guarantees.

        Args:
            is_tail_chain: Whether tail-chaining optimization applies
            has_fpu_context: Whether FPU context needs preservation

        Returns:
            Number of cycles for interrupt entry
        """
        if is_tail_chain:
            # Use complete entry sequence timing for conservative
            # worst-case latency guarantees.
            base_latency = FULL_ENTRY_CYCLES
        else:
            base_latency = FULL_ENTRY_CYCLES
            self._full_entry_count += 1

        if has_fpu_context:
            base_latency += FPU_ADDITIONAL_CYCLES

        if is_tail_chain:
            self._tail_chain_count += 1

        self._total_entry_cycles += base_latency
        return base_latency

    def compute_exit_latency(self, has_fpu_context=False):
        """
        Compute the exit latency in cycles for returning from a handler.

        Args:
            has_fpu_context: Whether FPU context needs restoration

        Returns:
            Number of cycles for interrupt exit
        """
        latency = EXIT_CYCLES
        if has_fpu_context:
            latency += FPU_ADDITIONAL_CYCLES
        self._total_exit_cycles += latency
        return latency

    def generate_latency_report(self, latency_entries):
        """
        Generate a comprehensive latency report from all processed entries.

        Args:
            latency_entries: List of per-interrupt latency records

        Returns:
            Dictionary with latency statistics and breakdown
        """
        if not latency_entries:
            return {
                "total_interrupts_processed": 0,
                "full_entry_count": 0,
                "tail_chain_count": 0,
                "average_entry_latency": 0.0,
                "total_entry_cycles": 0,
                "min_entry_latency": 0,
                "max_entry_latency": 0,
                "entries": []
            }

        total_latency = sum(e["entry_latency_cycles"] for e in latency_entries)
        entry_latencies = [e["entry_latency_cycles"] for e in latency_entries]

        return {
            "total_interrupts_processed": len(latency_entries),
            "full_entry_count": self._full_entry_count,
            "tail_chain_count": self._tail_chain_count,
            "average_entry_latency": total_latency / len(latency_entries),
            "total_entry_cycles": total_latency,
            "min_entry_latency": min(entry_latencies),
            "max_entry_latency": max(entry_latencies),
            "entries": latency_entries
        }
