"""PLC Historian Quality Decoder Module.

Interprets OPC UA quality bitmasks from historian samples and maps
them to standardized severity levels for the output stream.

OPC UA Quality Code Structure (16-bit):
    Bits 15-14: Major quality (00=Bad, 01=Uncertain, 10=N/A, 11=Good)
    Bits 13-8:  Sub-status code (specific condition)
    Bits 7-2:   Limit status and historian bits
    Bits 1-0:   Datasource-specific flags

Severity Levels (output):
    0 = Good (fully trustworthy)
    1 = Uncertain (usable with caveats)
    2 = Bad_Stale (last known value, source timeout)
    3 = Bad_Sensor (sensor failure detected)
    4 = Bad_Comm (communication failure)
    5 = Bad_Config (configuration error)

Quality Propagation:
    In historian backfill scenarios, quality annotations are applied
    retroactively — a later quality assessment supersedes earlier ones
    within the same batch. Propagation proceeds from the END of the
    batch toward the beginning, so that the most recent quality
    determination takes precedence over older assessments for any
    sample that hasn't been individually annotated.
"""

from typing import List, Dict, Any, Tuple

# Major quality extraction
QUALITY_MAJOR_MASK = 0xC000
QUALITY_MAJOR_SHIFT = 14

# Sub-status extraction
QUALITY_SUB_MASK = 0x3F00
QUALITY_SUB_SHIFT = 8

# Historian bits
QUALITY_HIST_MASK = 0x00FC
QUALITY_HIST_SHIFT = 2

# Major quality values
MAJOR_BAD = 0
MAJOR_UNCERTAIN = 1
MAJOR_NA = 2
MAJOR_GOOD = 3

# Sub-status codes for Bad quality
SUB_BAD_STALE = 0x01
SUB_BAD_SENSOR = 0x02
SUB_BAD_COMM = 0x03
SUB_BAD_CONFIG = 0x04

# Severity mapping
SEVERITY_GOOD = 0
SEVERITY_UNCERTAIN = 1
SEVERITY_BAD_STALE = 2
SEVERITY_BAD_SENSOR = 3
SEVERITY_BAD_COMM = 4
SEVERITY_BAD_CONFIG = 5


def decode_quality_major(quality_code: int) -> int:
    """Extract the major quality field from a 16-bit quality code.

    Args:
        quality_code: Raw 16-bit OPC UA quality bitmask.

    Returns:
        Major quality value (0-3).
    """
    return (quality_code & QUALITY_MAJOR_MASK) >> QUALITY_MAJOR_SHIFT


def decode_quality_sub(quality_code: int) -> int:
    """Extract the sub-status field from a quality code.

    Args:
        quality_code: Raw 16-bit OPC UA quality bitmask.

    Returns:
        Sub-status code (0-63).
    """
    return (quality_code & QUALITY_SUB_MASK) >> QUALITY_SUB_SHIFT


def decode_historian_bits(quality_code: int) -> int:
    """Extract historian-specific bits from quality code.

    Args:
        quality_code: Raw 16-bit OPC UA quality bitmask.

    Returns:
        Historian bits value (0-63).
    """
    return (quality_code & QUALITY_HIST_MASK) >> QUALITY_HIST_SHIFT


def map_to_severity(quality_code: int) -> int:
    """Map a raw quality code to a severity level.

    Args:
        quality_code: Raw 16-bit OPC UA quality bitmask.

    Returns:
        Integer severity level (0-5).
    """
    major = decode_quality_major(quality_code)

    if major == MAJOR_GOOD:
        return SEVERITY_GOOD
    elif major == MAJOR_UNCERTAIN:
        return SEVERITY_UNCERTAIN
    elif major == MAJOR_BAD:
        sub = decode_quality_sub(quality_code)
        if sub == SUB_BAD_STALE:
            return SEVERITY_BAD_STALE
        elif sub == SUB_BAD_SENSOR:
            return SEVERITY_BAD_SENSOR
        elif sub == SUB_BAD_COMM:
            return SEVERITY_BAD_COMM
        elif sub == SUB_BAD_CONFIG:
            return SEVERITY_BAD_CONFIG
        else:
            return SEVERITY_BAD_STALE  # Default bad sub-type
    else:
        return SEVERITY_UNCERTAIN  # N/A treated as uncertain


def propagate_quality(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Apply quality propagation across a sample batch.

    For historian backfill batches, quality is propagated in reverse
    chronological order — later quality assessments override earlier
    ones. A sample with GOOD quality acts as a propagation barrier;
    non-GOOD quality propagates backward until hitting a barrier or
    reaching the batch start.

    This implements the retroactive annotation model where instrument
    technicians mark quality issues that may have started before the
    diagnosis timestamp.

    Args:
        samples: List of sample dicts with 'severity' field already set.

    Returns:
        Updated sample list with propagated quality severity values.
    """
    if len(samples) <= 1:
        return samples

    # Reverse-chronological propagation: scan from end to start
    # A non-GOOD severity propagates backward until hitting GOOD
    propagated = [s.copy() for s in samples]
    active_severity = SEVERITY_GOOD

    for i in range(len(propagated) - 1, -1, -1):
        current_sev = propagated[i]['severity']
        if current_sev != SEVERITY_GOOD:
            # Non-good quality: this becomes the active propagation value
            active_severity = current_sev
        elif active_severity != SEVERITY_GOOD:
            # Good quality with active propagation: override
            propagated[i]['severity'] = active_severity
        else:
            # Good quality, no active propagation: barrier
            active_severity = SEVERITY_GOOD

    return propagated


def decode_quality_batch(samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Decode quality codes and apply propagation for a sample batch.

    Processes raw quality bitmasks into severity levels, then applies
    the historian-standard reverse-chronological propagation model.

    Args:
        samples: List of sample dicts with 'quality' field (raw bitmask).

    Returns:
        Samples with 'severity' field added and propagation applied.
    """
    # First pass: decode individual quality codes
    for sample in samples:
        sample['severity'] = map_to_severity(sample['quality'])

    # Second pass: apply batch propagation
    samples = propagate_quality(samples)

    return samples
