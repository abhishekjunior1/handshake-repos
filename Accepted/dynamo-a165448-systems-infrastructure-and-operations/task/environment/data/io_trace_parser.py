"""
Block I/O trace parser for storage tiering analysis.

Parses raw I/O trace events from structured JSON format containing
timestamp, logical block address (LBA), operation type, block size,
and device identifier. Produces normalized trace records suitable
for downstream heat classification and wear estimation.
"""

import json
from typing import Any


# Standard block size for LBA normalization (4 KiB sectors)
SECTOR_SIZE_BYTES = 4096

# Maximum LBA range per device (used for address space partitioning)
MAX_LBA_RANGE = 2**48


def load_trace_file(filepath: str) -> dict[str, Any]:
    """Load and validate the storage configuration and trace data."""
    with open(filepath, "r") as f:
        data = json.load(f)

    required_keys = ["devices", "tiers", "trace_events", "config"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key in trace file: {key}")

    return data


def parse_trace_events(raw_events: list[dict]) -> list[dict]:
    """
    Parse raw trace events into normalized records.

    Each record contains:
      - timestamp_us: event time in microseconds
      - lba_start: starting logical block address
      - lba_end: ending logical block address (exclusive)
      - block_count: number of 4K blocks accessed
      - op_type: 'read' or 'write'
      - device_id: target device identifier
      - io_size_bytes: total I/O size in bytes
    """
    parsed = []
    for event in raw_events:
        lba_start = event["lba"]
        io_size = event["size_bytes"]
        block_count = (io_size + SECTOR_SIZE_BYTES - 1) // SECTOR_SIZE_BYTES
        lba_end = lba_start + block_count

        record = {
            "timestamp_us": event["timestamp_us"],
            "lba_start": lba_start,
            "lba_end": lba_end,
            "block_count": block_count,
            "op_type": event["op_type"].lower(),
            "device_id": event["device_id"],
            "io_size_bytes": io_size,
        }
        parsed.append(record)

    return parsed


def compute_access_intervals(events: list[dict]) -> dict[str, list[dict]]:
    """
    Group events by device and compute inter-access intervals.

    Returns a mapping from device_id to a list of interval records,
    where each interval contains the LBA range and elapsed time
    since the previous access to that range.
    """
    device_events: dict[str, list[dict]] = {}
    for evt in events:
        dev = evt["device_id"]
        if dev not in device_events:
            device_events[dev] = []
        device_events[dev].append(evt)

    intervals: dict[str, list[dict]] = {}
    for dev, dev_events in device_events.items():
        sorted_events = sorted(dev_events, key=lambda e: e["timestamp_us"])
        dev_intervals = []
        last_access: dict[int, int] = {}

        for evt in sorted_events:
            for lba in range(evt["lba_start"], evt["lba_end"]):
                prev_time = last_access.get(lba)
                if prev_time is not None:
                    interval_us = evt["timestamp_us"] - prev_time
                    dev_intervals.append({
                        "lba": lba,
                        "interval_us": interval_us,
                        "timestamp_us": evt["timestamp_us"],
                        "op_type": evt["op_type"],
                    })
                last_access[lba] = evt["timestamp_us"]

        intervals[dev] = dev_intervals

    return intervals


def aggregate_block_stats(events: list[dict]) -> dict[str, dict]:
    """
    Compute per-block access statistics across all events.

    Returns a mapping from 'device_id:lba' to statistics including
    total accesses, read/write ratio, first/last access times,
    and total bytes transferred.
    """
    block_stats: dict[str, dict] = {}

    for evt in events:
        for lba in range(evt["lba_start"], evt["lba_end"]):
            key = f"{evt['device_id']}:{lba}"
            if key not in block_stats:
                block_stats[key] = {
                    "device_id": evt["device_id"],
                    "lba": lba,
                    "total_accesses": 0,
                    "read_count": 0,
                    "write_count": 0,
                    "first_access_us": evt["timestamp_us"],
                    "last_access_us": evt["timestamp_us"],
                    "total_bytes": 0,
                }

            stats = block_stats[key]
            stats["total_accesses"] += 1
            if evt["op_type"] == "read":
                stats["read_count"] += 1
            else:
                stats["write_count"] += 1
            stats["last_access_us"] = max(stats["last_access_us"], evt["timestamp_us"])
            stats["first_access_us"] = min(stats["first_access_us"], evt["timestamp_us"])
            stats["total_bytes"] += evt["io_size_bytes"] // evt["block_count"]

    return block_stats


def extract_device_write_volumes(events: list[dict],
                                  interval_start_us: int = 0) -> dict[str, dict]:
    """
    Compute per-device write volume statistics.

    Separates cumulative (all-time) write volumes from interval-specific
    writes. The interval boundary allows computing wear rate from only
    the most recent measurement window rather than lifetime totals.

    Args:
        events: parsed trace event records
        interval_start_us: start timestamp of current measurement interval.
            Writes before this timestamp count toward cumulative only.
            Writes at or after this timestamp count toward both cumulative
            and interval metrics.

    Returns mapping from device_id to:
      - total_write_bytes: cumulative bytes written (all events)
      - total_write_blocks: cumulative blocks written (all events)
      - write_event_count: number of write operations
      - interval_write_bytes: bytes written in current interval only
      - interval_write_blocks: blocks written in current interval only
    """
    device_writes: dict[str, dict] = {}

    for evt in events:
        if evt["op_type"] != "write":
            continue

        dev = evt["device_id"]
        if dev not in device_writes:
            device_writes[dev] = {
                "total_write_bytes": 0,
                "total_write_blocks": 0,
                "write_event_count": 0,
                "interval_write_bytes": 0,
                "interval_write_blocks": 0,
            }

        stats = device_writes[dev]
        stats["total_write_bytes"] += evt["io_size_bytes"]
        stats["total_write_blocks"] += evt["block_count"]
        stats["write_event_count"] += 1

        # Only count toward interval if within the measurement window
        if evt["timestamp_us"] >= interval_start_us:
            stats["interval_write_bytes"] += evt["io_size_bytes"]
            stats["interval_write_blocks"] += evt["block_count"]

    return device_writes
