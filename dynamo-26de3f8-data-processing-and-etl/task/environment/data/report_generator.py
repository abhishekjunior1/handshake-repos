"""
Report generator for the streaming pipeline. Formats final output.
"""


def build_report(stream_name, window_size, decay_factor, window_results,
                 total_events, total_after_dedup):
    """Build the output report."""
    return {
        "stream_name": stream_name,
        "config": {
            "window_size_sec": window_size,
            "decay_factor": decay_factor,
        },
        "windows": window_results,
        "summary": {
            "total_events": total_events,
            "events_after_dedup": total_after_dedup,
            "duplicates_removed": total_events - total_after_dedup,
            "windows_produced": len(window_results),
        },
    }
