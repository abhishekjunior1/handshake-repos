"""PLC Historian Timestamp Engine Module.

Handles timestamp processing for historian data migration including:
- Epoch conversion (microseconds since Unix epoch to ISO 8601)
- Gap detection between consecutive samples
- Interpolation of missing values during detected gaps
- Support for both linear and stepped (zero-order hold) modes

Interpolation Modes:
    LINEAR: Linearly interpolate between bounding values for gaps.
            Appropriate for continuously-varying analog signals
            (temperature, pressure, flow rate).

    STEPPED: Zero-order hold — carry forward the last known value
             until the next sample arrives. Appropriate for discrete
             states (valve open/closed, motor running/stopped, alarm
             active/inactive) and integer counters.

Timestamp Ordering:
    The archive format stores samples in BLOCK ORDER, which preserves
    the physical storage layout of the legacy system. Blocks may span
    overlapping time ranges when the historian performed concurrent
    writes from multiple scan groups. The output preserves source
    ordering for audit trail compliance — downstream systems that
    require time-ordering must sort independently.
"""

from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone

# Gap detection configuration
# The default threshold is used when no tag-specific scan rate is available.
# Per historian best practices (ISA-95 / OPC UA HA), tag-level gap detection
# uses 3× the configured scan interval: a gap exceeding three consecutive
# missed scans indicates data loss rather than normal jitter (which stays
# within 2× the scan period under healthy network conditions).
DEFAULT_GAP_THRESHOLD_US = 5_000_000  # 5 seconds

# Maximum number of interpolated points per gap
MAX_INTERP_POINTS = 10


def us_to_iso8601(timestamp_us: int) -> str:
    """Convert microseconds-since-epoch to ISO 8601 string.

    Args:
        timestamp_us: Timestamp in microseconds since Unix epoch.

    Returns:
        ISO 8601 formatted string with microsecond precision.
    """
    seconds = timestamp_us / 1_000_000
    dt = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f') + 'Z'


def detect_gaps(samples: List[Dict[str, Any]],
                gap_threshold_us: int = DEFAULT_GAP_THRESHOLD_US
                ) -> List[Tuple[int, int]]:
    """Detect time gaps between consecutive samples.

    A gap is detected when the time difference between two adjacent
    samples exceeds the threshold. Returns pairs of indices bracketing
    each gap.

    Note: Gap detection operates on samples in their given order,
    which may be non-monotonic for multi-scan-group archives.
    Gaps are only detected between adjacent samples in source order.

    Args:
        samples: List of samples with 'timestamp_us' field.
        gap_threshold_us: Minimum gap duration to flag (microseconds).

    Returns:
        List of (start_idx, end_idx) pairs bracketing detected gaps.
    """
    gaps = []
    for i in range(len(samples) - 1):
        t_current = samples[i]['timestamp_us']
        t_next = samples[i + 1]['timestamp_us']

        # Only detect forward gaps (t_next > t_current)
        # Non-monotonic transitions are block boundaries, not gaps
        if t_next > t_current:
            delta = t_next - t_current
            if delta > gap_threshold_us:
                gaps.append((i, i + 1))

    return gaps


def interpolate_linear(val_start: float, val_end: float,
                       t_start: int, t_end: int,
                       num_points: int) -> List[Dict[str, Any]]:
    """Generate linearly interpolated samples between two values.

    Produces evenly-spaced points between start and end, exclusive
    of the endpoints themselves.

    Args:
        val_start: Value at gap start.
        val_end: Value at gap end.
        t_start: Timestamp (us) at gap start.
        t_end: Timestamp (us) at gap end.
        num_points: Number of interpolated points to generate.

    Returns:
        List of interpolated sample dicts.
    """
    points = []
    for i in range(1, num_points + 1):
        fraction = i / (num_points + 1)
        t_interp = int(t_start + fraction * (t_end - t_start))
        v_interp = val_start + fraction * (val_end - val_start)

        points.append({
            'timestamp_us': t_interp,
            'value': round(v_interp, 6),
            'interpolated': True,
            'interp_method': 'linear',
        })

    return points


def interpolate_stepped(val_start: float, t_start: int, t_end: int,
                        num_points: int) -> List[Dict[str, Any]]:
    """Generate zero-order-hold interpolated samples.

    Carries forward the start value at evenly-spaced timestamps.
    The value does NOT change until the next real sample — this is
    correct for discrete states and boolean signals.

    Args:
        val_start: Value to hold (last known state).
        t_start: Timestamp (us) at gap start.
        t_end: Timestamp (us) at gap end.
        num_points: Number of interpolated points to generate.

    Returns:
        List of interpolated sample dicts with held value.
    """
    points = []
    for i in range(1, num_points + 1):
        fraction = i / (num_points + 1)
        t_interp = int(t_start + fraction * (t_end - t_start))

        points.append({
            'timestamp_us': t_interp,
            'value': val_start,  # Hold previous value
            'interpolated': True,
            'interp_method': 'stepped',
        })

    return points


def fill_gaps(samples: List[Dict[str, Any]],
              gaps: List[Tuple[int, int]],
              interpolation_mode: str = 'linear',
              max_points: int = MAX_INTERP_POINTS) -> List[Dict[str, Any]]:
    """Fill detected gaps with interpolated samples.

    Inserts synthetic samples into gaps using the specified
    interpolation method. Original samples are preserved unchanged.

    Args:
        samples: Original sample list.
        gaps: List of (start_idx, end_idx) gap boundaries.
        interpolation_mode: Either 'linear' or 'stepped'.
        max_points: Maximum interpolated points per gap.

    Returns:
        New sample list with interpolated points inserted at gaps.
    """
    if not gaps:
        return samples

    # Build result with interpolated points inserted
    result = []
    gap_set = {g[0] for g in gaps}
    gap_map = {g[0]: g for g in gaps}

    for i, sample in enumerate(samples):
        result.append(sample)

        if i in gap_set:
            start_idx, end_idx = gap_map[i]
            t_start = samples[start_idx]['timestamp_us']
            t_end = samples[end_idx]['timestamp_us']
            val_start = samples[start_idx].get('value',
                                                samples[start_idx].get('raw_value', 0))
            val_end = samples[end_idx].get('value',
                                           samples[end_idx].get('raw_value', 0))

            # Calculate number of points based on gap duration
            gap_duration = t_end - t_start
            num_points = min(max_points,
                             max(1, int(gap_duration / DEFAULT_GAP_THRESHOLD_US)))

            if interpolation_mode == 'stepped':
                interp_points = interpolate_stepped(
                    val_start, t_start, t_end, num_points)
            else:
                interp_points = interpolate_linear(
                    val_start, val_end, t_start, t_end, num_points)

            result.extend(interp_points)

    return result


def convert_timestamps(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert microsecond timestamps to ISO 8601 strings.

    Adds 'timestamp_iso' field while preserving 'timestamp_us'.

    Args:
        samples: Sample list with 'timestamp_us' field.

    Returns:
        Samples with added 'timestamp_iso' field.
    """
    for sample in samples:
        sample['timestamp_iso'] = us_to_iso8601(sample['timestamp_us'])
    return samples
