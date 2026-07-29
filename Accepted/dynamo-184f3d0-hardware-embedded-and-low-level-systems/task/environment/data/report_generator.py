"""
Report Generator — formats the interrupt controller pipeline output
into structured JSON format for verification.

Combines results from all pipeline stages into the final output
document with all required sections.
"""


class ReportGenerator:
    """
    Formats and combines pipeline stage outputs into final report.

    Output structure:
    - preemption_events: List of preemption decisions made
    - handler_timeline: Ordered list of handler executions
    - latency_report: Timing statistics and per-interrupt breakdown
    - vector_map: Vector table address mapping
    - priority_state: Final state of all registered interrupts
    """

    def format_output(self, preemption_events, handler_timeline,
                      latency_report, vector_map, priority_state):
        """
        Assemble the final output document from all pipeline stages.

        Args:
            preemption_events: List of preemption event records
            handler_timeline: Ordered handler execution timeline
            latency_report: Latency statistics dictionary
            vector_map: Vector table mapping
            priority_state: Final interrupt states

        Returns:
            Complete output dictionary for JSON serialization
        """
        output = {
            "preemption_events": preemption_events,
            "handler_timeline": handler_timeline,
            "latency_report": latency_report,
            "vector_map": vector_map,
            "priority_state": priority_state,
            "summary": self._generate_summary(
                preemption_events, handler_timeline, latency_report
            )
        }
        return output

    def _generate_summary(self, preemption_events, handler_timeline, latency_report):
        """
        Generate a high-level summary of pipeline execution.

        Returns:
            Summary dictionary with key metrics
        """
        tail_chain_events = [
            e for e in preemption_events if e.get("tail_chained", False)
        ]
        unique_vectors = set(e["vector"] for e in handler_timeline)

        return {
            "total_preemptions": len(preemption_events),
            "total_handlers_executed": len(handler_timeline),
            "tail_chain_optimizations": len(tail_chain_events),
            "unique_vectors_serviced": len(unique_vectors),
            "total_latency_cycles": latency_report.get("total_entry_cycles", 0),
            "average_entry_latency": latency_report.get("average_entry_latency", 0.0)
        }
