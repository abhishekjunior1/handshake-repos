"""
Padding module implementing PKCS#7 padding for block cipher alignment.

PKCS#7 padding adds N bytes of value N to bring the message length to
a multiple of the block size. If the message is already block-aligned,
a FULL block of padding is added (this ensures unambiguous removal).
"""

import struct


def pad(data: bytes, block_size: int) -> bytes:
    """
    Apply PKCS#7 padding to align data to the block size.

    Per the PKCS#7 specification, padding is ALWAYS added:
    - If data length mod block_size == 0, a full block of padding is added
    - Otherwise, enough bytes are added to reach the next block boundary
    - Each padding byte has the value equal to the number of padding bytes added

    Parameters:
        data: Input data to pad
        block_size: Block size in bytes (must be 1-255)

    Returns:
        Padded data (length is always a multiple of block_size)
    """
    if block_size < 1 or block_size > 255:
        raise ValueError("Block size must be between 1 and 255")

    # Calculate padding length — always adds at least 1 byte
    # When already aligned, adds a full block (this is correct per PKCS#7)
    padding_length = block_size - (len(data) % block_size)

    # Create padding bytes (each byte has value = padding_length)
    padding = bytes([padding_length]) * padding_length

    return data + padding


def unpad(data: bytes, block_size: int) -> bytes:
    """
    Remove PKCS#7 padding from padded data.

    Validates that the padding is well-formed before removal.

    Parameters:
        data: Padded data
        block_size: Block size used during padding

    Returns:
        Original unpadded data

    Raises:
        ValueError: If padding is invalid or data is corrupted
    """
    if not data:
        raise ValueError("Cannot unpad empty data")
    if len(data) % block_size != 0:
        raise ValueError("Data length is not a multiple of block size")

    # Last byte indicates padding length
    padding_length = data[-1]

    if padding_length == 0 or padding_length > block_size:
        raise ValueError(f"Invalid padding length: {padding_length}")
    if padding_length > len(data):
        raise ValueError("Padding length exceeds data length")

    # Verify all padding bytes have the correct value
    padding_section = data[-padding_length:]
    if not all(b == padding_length for b in padding_section):
        raise ValueError("Invalid padding bytes detected")

    return data[:-padding_length]


def compute_padded_length(data_length: int, block_size: int) -> int:
    """
    Compute the length of data after PKCS#7 padding without actually padding.

    Parameters:
        data_length: Original data length
        block_size: Block size

    Returns:
        Length after padding
    """
    padding_length = block_size - (data_length % block_size)
    return data_length + padding_length


def validate_padding(data: bytes, block_size: int) -> dict:
    """
    Validate PKCS#7 padding without removing it.

    Returns a dictionary with validation results.
    """
    result = {
        "valid": True,
        "data_length": len(data),
        "block_size": block_size,
        "padding_length": 0,
        "original_length": 0,
        "error": None
    }

    if not data:
        result["valid"] = False
        result["error"] = "Empty data"
        return result

    if len(data) % block_size != 0:
        result["valid"] = False
        result["error"] = "Length not multiple of block size"
        return result

    padding_length = data[-1]

    if padding_length == 0 or padding_length > block_size:
        result["valid"] = False
        result["error"] = f"Invalid padding value: {padding_length}"
        return result

    if padding_length > len(data):
        result["valid"] = False
        result["error"] = "Padding exceeds data length"
        return result

    padding_section = data[-padding_length:]
    if not all(b == padding_length for b in padding_section):
        result["valid"] = False
        result["error"] = "Inconsistent padding bytes"
        return result

    result["padding_length"] = padding_length
    result["original_length"] = len(data) - padding_length

    return result


def pad_iso7816(data: bytes, block_size: int) -> bytes:
    """
    Alternative padding scheme: ISO/IEC 7816-4.

    Appends 0x80 followed by zero bytes to reach block alignment.
    Unlike PKCS#7, this always starts with a distinct marker byte.

    Not used in the main pipeline but provided for compatibility
    with systems that require ISO 7816-4 padding.
    """
    padding_length = block_size - ((len(data) + 1) % block_size)
    return data + b'\x80' + b'\x00' * padding_length


def unpad_iso7816(data: bytes, block_size: int) -> bytes:
    """Remove ISO/IEC 7816-4 padding."""
    if not data:
        raise ValueError("Cannot unpad empty data")

    # Find the 0x80 marker scanning from the end
    i = len(data) - 1
    while i >= 0 and data[i] == 0x00:
        i -= 1

    if i < 0 or data[i] != 0x80:
        raise ValueError("Invalid ISO 7816-4 padding")

    return data[:i]
