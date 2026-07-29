"""PLC Historian Archive Reader Module.

Reads and parses binary archive blocks from legacy PLC data historian
systems. The archive format stores process variable samples in
sequential blocks, each containing a batch of timestamped readings
from a single tag (process variable).

Archive Block Format:
    - Block header (16 bytes):
        [4 bytes] Magic: 0x48495354 ("HIST")
        [2 bytes] Block version (uint16 BE)
        [2 bytes] Tag ID (uint16 BE)
        [4 bytes] Sample count (uint32 BE)
        [4 bytes] Block flags (uint32 BE)
    - Samples (variable length, repeated sample_count times):
        [8 bytes] Timestamp (uint64 BE, microseconds since epoch)
        [2 bytes] Raw ADC value (uint16 BE)
        [2 bytes] Quality bitmask (uint16 BE)

Block flags:
    Bit 0: Compressed (swinging-door samples present)
    Bit 1: Interpolated (gap-fill samples included)
    Bit 2: Backfill (retroactively inserted data)
"""

import struct
from typing import List, Dict, Any

BLOCK_MAGIC = 0x48495354  # "HIST"
BLOCK_HEADER_SIZE = 16
SAMPLE_SIZE = 12  # 8 + 2 + 2


class ArchiveBlock:
    """Represents a parsed archive block with its samples."""

    def __init__(self, tag_id: int, version: int, flags: int,
                 samples: List[Dict[str, Any]]):
        self.tag_id = tag_id
        self.version = version
        self.flags = flags
        self.samples = samples

    @property
    def is_compressed(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def is_interpolated(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def is_backfill(self) -> bool:
        return bool(self.flags & 0x04)


def parse_block_header(data: bytes, offset: int = 0) -> Dict[str, int]:
    """Parse a 16-byte archive block header.

    Args:
        data: Raw bytes containing the block header.
        offset: Starting offset within data.

    Returns:
        Dictionary with magic, version, tag_id, sample_count, flags.

    Raises:
        ValueError: If magic number doesn't match or data too short.
    """
    if len(data) - offset < BLOCK_HEADER_SIZE:
        raise ValueError(
            f"Insufficient data for block header: "
            f"need {BLOCK_HEADER_SIZE}, have {len(data) - offset}"
        )

    magic = struct.unpack_from('>I', data, offset)[0]
    if magic != BLOCK_MAGIC:
        raise ValueError(
            f"Invalid block magic: 0x{magic:08X} "
            f"(expected 0x{BLOCK_MAGIC:08X})"
        )

    version = struct.unpack_from('>H', data, offset + 4)[0]
    tag_id = struct.unpack_from('>H', data, offset + 6)[0]
    sample_count = struct.unpack_from('>I', data, offset + 8)[0]
    flags = struct.unpack_from('>I', data, offset + 12)[0]

    return {
        'magic': magic,
        'version': version,
        'tag_id': tag_id,
        'sample_count': sample_count,
        'flags': flags,
    }


def parse_samples(data: bytes, offset: int, count: int) -> List[Dict[str, Any]]:
    """Parse raw samples from the archive block body.

    Each sample is 12 bytes: timestamp (8) + raw_value (2) + quality (2).

    Args:
        data: Raw bytes containing sample data.
        offset: Starting offset for first sample.
        count: Number of samples to parse.

    Returns:
        List of sample dictionaries with timestamp_us, raw_value, quality.
    """
    samples = []
    pos = offset

    for i in range(count):
        if pos + SAMPLE_SIZE > len(data):
            raise ValueError(
                f"Buffer underrun at sample {i}: "
                f"need {SAMPLE_SIZE} bytes at offset {pos}"
            )

        timestamp_us = struct.unpack_from('>Q', data, pos)[0]
        raw_value = struct.unpack_from('>H', data, pos + 8)[0]
        quality = struct.unpack_from('>H', data, pos + 10)[0]

        samples.append({
            'timestamp_us': timestamp_us,
            'raw_value': raw_value,
            'quality': quality,
        })
        pos += SAMPLE_SIZE

    return samples


def read_archive(data: bytes) -> List[ArchiveBlock]:
    """Read all blocks from an archive binary blob.

    Sequentially parses blocks until all data is consumed.

    Args:
        data: Complete archive binary data.

    Returns:
        List of ArchiveBlock instances.
    """
    blocks = []
    offset = 0

    while offset < len(data):
        if offset + BLOCK_HEADER_SIZE > len(data):
            break

        header = parse_block_header(data, offset)
        block_size = BLOCK_HEADER_SIZE + header['sample_count'] * SAMPLE_SIZE

        if offset + block_size > len(data):
            raise ValueError(
                f"Truncated block at offset {offset}: "
                f"declared size {block_size}, available {len(data) - offset}"
            )

        samples = parse_samples(
            data,
            offset + BLOCK_HEADER_SIZE,
            header['sample_count']
        )

        block = ArchiveBlock(
            tag_id=header['tag_id'],
            version=header['version'],
            flags=header['flags'],
            samples=samples,
        )
        blocks.append(block)
        offset += block_size

    return blocks
