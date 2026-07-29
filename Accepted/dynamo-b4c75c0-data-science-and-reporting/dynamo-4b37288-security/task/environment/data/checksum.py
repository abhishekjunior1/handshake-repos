"""BinVault integrity verification.

The archiver computed checksums before applying the storage encoding
transform, so verification decodes first to recover the original
content bytes that were checksummed.
"""
import zlib

from encoding import decode_data


def verify(data, encoding, expected):
    """Verify BLOB CRC32. Decodes first to match archiver behavior."""
    decoded = decode_data(data, encoding)
    return (zlib.crc32(decoded) & 0xFFFFFFFF) == expected
