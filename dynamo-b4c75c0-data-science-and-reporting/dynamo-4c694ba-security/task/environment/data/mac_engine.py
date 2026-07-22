"""
MAC (Message Authentication Code) engine implementing an HMAC-style
construction over arbitrary data using SHA-256 as the underlying hash.

Provides both single-shot MAC computation and incremental (streaming)
MAC computation for large messages.
"""

import hashlib
import struct


_IPAD = 0x36
_OPAD = 0x5C
_BLOCK_SIZE = 64  # SHA-256 block size


def _prepare_key(key: bytes) -> bytes:
    """
    Prepare the MAC key to block size.
    If longer than block size, hash it first.
    If shorter, pad with zeros.
    """
    if len(key) > _BLOCK_SIZE:
        key = hashlib.sha256(key).digest()
    return key.ljust(_BLOCK_SIZE, b'\x00')


def compute_mac(key: bytes, data: bytes) -> bytes:
    """
    Compute MAC over the given data using the provided key.

    Implements HMAC construction:
        MAC = H((key XOR opad) || H((key XOR ipad) || data))

    Parameters:
        key: MAC key (any length, will be normalized)
        data: Data to authenticate

    Returns:
        32-byte MAC tag
    """
    prepared_key = _prepare_key(key)

    # Inner hash: H((key XOR ipad) || data)
    inner_key = bytes(k ^ _IPAD for k in prepared_key)
    inner_hash = hashlib.sha256(inner_key + data).digest()

    # Outer hash: H((key XOR opad) || inner_hash)
    outer_key = bytes(k ^ _OPAD for k in prepared_key)
    mac_tag = hashlib.sha256(outer_key + inner_hash).digest()

    return mac_tag


def compute_mac_with_context(key: bytes, data: bytes,
                             context: bytes = b'') -> bytes:
    """
    Compute MAC with additional context binding.

    The context is prepended to the data before MAC computation,
    providing domain separation when the same key is used for
    multiple purposes.

    Parameters:
        key: MAC key
        data: Primary data to authenticate
        context: Additional context for domain binding

    Returns:
        32-byte MAC tag
    """
    # Encode context length to prevent length-extension ambiguity
    context_header = struct.pack('>I', len(context))
    bound_data = context_header + context + data
    return compute_mac(key, bound_data)


class StreamingMAC:
    """
    Incremental MAC computation for processing large messages
    without loading them entirely into memory.
    """

    def __init__(self, key: bytes):
        """Initialize streaming MAC with the given key."""
        self._prepared_key = _prepare_key(key)
        inner_key = bytes(k ^ _IPAD for k in self._prepared_key)
        self._inner_hasher = hashlib.sha256(inner_key)
        self._finalized = False

    def update(self, data: bytes) -> None:
        """Feed additional data into the MAC computation."""
        if self._finalized:
            raise RuntimeError("MAC already finalized")
        self._inner_hasher.update(data)

    def finalize(self) -> bytes:
        """
        Complete the MAC computation and return the tag.
        Cannot be called more than once.
        """
        if self._finalized:
            raise RuntimeError("MAC already finalized")
        self._finalized = True

        inner_hash = self._inner_hasher.digest()
        outer_key = bytes(k ^ _OPAD for k in self._prepared_key)
        return hashlib.sha256(outer_key + inner_hash).digest()


def verify_mac(key: bytes, data: bytes, expected_tag: bytes) -> bool:
    """
    Verify a MAC tag in constant time.

    Parameters:
        key: MAC key
        data: Data that was authenticated
        expected_tag: The tag to verify against

    Returns:
        True if the tag is valid, False otherwise
    """
    computed_tag = compute_mac(key, data)
    return _constant_time_compare(computed_tag, expected_tag)


def _constant_time_compare(a: bytes, b: bytes) -> bool:
    """Compare two byte strings in constant time to prevent timing attacks."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0


def compute_mac_chain(key: bytes, blocks: list) -> bytes:
    """
    Compute a chained MAC over multiple data blocks.

    Each block's MAC feeds into the next computation, creating
    a dependency chain that authenticates both content and ordering.

    Parameters:
        key: MAC key
        blocks: List of data blocks to authenticate in order

    Returns:
        Final 32-byte chain MAC tag
    """
    if not blocks:
        return compute_mac(key, b'')

    current_tag = b'\x00' * 32  # Initial chain value

    for i, block in enumerate(blocks):
        # Include block index and previous tag in computation
        block_header = struct.pack('>II', i, len(block))
        chain_input = current_tag + block_header + block
        current_tag = compute_mac(key, chain_input)

    return current_tag


def truncate_mac(tag: bytes, length: int) -> bytes:
    """
    Truncate a MAC tag to the specified length.

    Common in protocols where bandwidth is limited but full
    MAC strength isn't required.

    Parameters:
        tag: Full MAC tag
        length: Desired output length (must be >= 8 bytes)

    Returns:
        Truncated tag
    """
    if length < 8:
        raise ValueError("Truncated MAC must be at least 8 bytes")
    if length > len(tag):
        raise ValueError("Cannot expand MAC beyond original length")
    return tag[:length]
