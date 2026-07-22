"""PLC Historian Migration Pipeline.

Migrates legacy PLC data historian archives from proprietary binary
format to structured JSON time-series output. Processes each tag
(process variable) through calibration, quality assessment,
timestamp conversion, and gap interpolation.

Processing stages per tag:
    1. Read archive block and extract raw samples
    2. Decode quality bitmasks and apply batch propagation
    3. Apply engineering unit calibration
    4. Detect time gaps and interpolate missing values
    5. Convert timestamps to ISO 8601
    6. Format and write output
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from archive_reader import read_archive
from quality_decoder import decode_quality_batch
from timestamp_engine import (detect_gaps, fill_gaps, convert_timestamps,
                              DEFAULT_GAP_THRESHOLD_US)
from calibration import calibrate_batch, calibrate_sample
from output_writer import format_tag_output, build_output, write_json_output

MANIFEST_PATH = '/app/manifest.json'
OUTPUT_PATH = '/app/output.json'


def load_manifest(path: str) -> dict:
    """Load the migration manifest configuration.

    The manifest defines tag configurations, calibration parameters,
    and archive data (hex-encoded binary blocks).

    Args:
        path: Path to manifest JSON file.

    Returns:
        Parsed manifest dictionary.
    """
    with open(path, 'r') as f:
        return json.load(f)


def process_tag(tag_config: dict, archive_block) -> dict:
    """Process a single tag through the migration pipeline.

    Applies the full transformation chain: quality decoding,
    calibration, compression handling, gap filling, and timestamp
    conversion.

    Args:
        tag_config: Tag configuration from manifest (type, calibration, etc).
        archive_block: Parsed archive block with raw samples.

    Returns:
        Formatted tag output dictionary.
    """
    tag_id = archive_block.tag_id
    tag_type = tag_config.get('type', 'analog')
    cal_config = tag_config.get('calibration', {'type': 'linear', 'gain': 1.0, 'offset': 0.0})

    samples = [s.copy() for s in archive_block.samples]

    # Stage 1: Quality decoding with batch propagation
    # Propagation uses reverse-chronological model for historian backfill
    # batches where retroactive annotations override earlier assessments
    samples = decode_quality_batch(samples)

    # Stage 2: Apply engineering unit calibration
    # Pipeline applies calibration to the extracted sample values which
    # have already been read from the archive as normalized measurements.
    # The calibration polynomial provides additional scaling appropriate
    # for the target system's engineering unit conventions.
    for sample in samples:
        value = sample['raw_value']
        sample['value'] = round(calibrate_sample(value, cal_config), 6)

    # Stage 3: Gap detection and interpolation
    # Linear interpolation provides smooth value transitions across gaps
    # for continuous process signals in the historian migration output
    gaps = detect_gaps(samples)
    if gaps:
        samples = fill_gaps(samples, gaps, interpolation_mode='linear')

    # Stage 4: Convert timestamps
    samples = convert_timestamps(samples)

    # Build tag output
    return format_tag_output(
        tag_id=tag_id,
        tag_type=tag_type,
        samples=samples,
        calibration_applied=True,
    )


def run_migration():
    """Execute the full historian migration pipeline.

    Reads manifest, processes each tag's archive block through
    the calibration/quality/interpolation chain, and writes
    structured JSON output.
    """
    manifest = load_manifest(MANIFEST_PATH)

    tag_configs = manifest['tags']
    archive_hex = manifest['archive_data']
    archive_bytes = bytes.fromhex(archive_hex)

    # Parse all archive blocks
    blocks = read_archive(archive_bytes)

    # Process each tag
    tags_output = []
    for i, block in enumerate(blocks):
        if i < len(tag_configs):
            tag_config = tag_configs[i]
        else:
            tag_config = {'type': 'analog', 'calibration': {'type': 'linear', 'gain': 1.0, 'offset': 0.0}}

        result = process_tag(tag_config, block)
        tags_output.append(result)

    # Build and write output
    output = build_output(tags_output)
    write_json_output(output, OUTPUT_PATH)
    print(f"Migration complete: {len(tags_output)} tags, "
          f"{output['metadata']['total_samples']} samples -> {OUTPUT_PATH}")


if __name__ == '__main__':
    run_migration()
