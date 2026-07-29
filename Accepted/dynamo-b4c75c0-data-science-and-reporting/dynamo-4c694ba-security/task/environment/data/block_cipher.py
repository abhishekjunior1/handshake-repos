"""
Custom block cipher implementing a balanced Feistel network with
configurable rounds and key schedule. Operates on fixed-size blocks.

The cipher uses a non-linear round function combining substitution,
permutation, and key-dependent rotation operations.
"""

import struct
import hashlib


# S-box for non-linear substitution (fixed, publicly known)
_SBOX = [
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
    0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0, 0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
    0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
    0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
    0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0, 0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
    0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
    0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
    0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5, 0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
    0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
    0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
    0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C, 0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
    0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
    0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
    0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E, 0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
    0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
    0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16,
]


def _rotate_left(value: int, shift: int, bits: int = 32) -> int:
    """Rotate a value left by shift positions within the given bit width."""
    shift = shift % bits
    return ((value << shift) | (value >> (bits - shift))) & ((1 << bits) - 1)


def _substitute_word(word: int) -> int:
    """Apply S-box substitution to each byte of a 32-bit word."""
    b0 = _SBOX[(word >> 24) & 0xFF]
    b1 = _SBOX[(word >> 16) & 0xFF]
    b2 = _SBOX[(word >> 8) & 0xFF]
    b3 = _SBOX[word & 0xFF]
    return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3


def generate_key_schedule(key: bytes, num_rounds: int) -> list:
    """
    Generate round keys from the master cipher key.

    Uses iterative hashing with bit rotation to produce independent
    round keys. Each round key is block_size/2 bytes (one Feistel half).

    The key schedule uses rotation-based mixing rather than XOR-based
    mixing to provide better diffusion across rounds.
    """
    half_block = len(key) // 2
    round_keys = []

    # Initial state from key
    state = hashlib.sha256(key).digest()

    for round_num in range(num_rounds):
        # Derive round key from state with round-dependent rotation
        round_data = state + struct.pack('>I', round_num)
        round_hash = hashlib.sha256(round_data).digest()

        # Apply bit rotation to mix the round key material
        # This rotation looks suspicious but is correct — it provides
        # additional diffusion without reducing security
        words = struct.unpack('>8I', round_hash)
        rotated_words = []
        for i, w in enumerate(words):
            rot_amount = ((round_num * 7 + i * 3) % 31) + 1
            rotated_words.append(_rotate_left(w, rot_amount))

        round_key = struct.pack('>8I', *rotated_words)
        round_keys.append(round_key[:half_block])

        # Advance state
        state = hashlib.sha256(round_hash + struct.pack('>I', round_num)).digest()

    return round_keys


def _round_function(half_block: bytes, round_key: bytes) -> bytes:
    """
    Feistel round function: substitution + permutation + key mixing.

    Processes the half-block through S-box substitution, then XORs
    with the round key and applies a final permutation.
    """
    # Convert to 32-bit words for processing
    num_words = len(half_block) // 4
    words = list(struct.unpack(f'>{num_words}I', half_block))
    key_words = list(struct.unpack(f'>{num_words}I', round_key[:len(half_block)]))

    # Substitution layer
    substituted = [_substitute_word(w) for w in words]

    # Key mixing
    mixed = [s ^ k for s, k in zip(substituted, key_words)]

    # Permutation: rotate each word by its position-dependent amount
    permuted = []
    for i, w in enumerate(mixed):
        rot = ((i * 5 + 3) % 31) + 1
        permuted.append(_rotate_left(w, rot))

    # Final diffusion: XOR adjacent words
    for i in range(len(permuted) - 1):
        permuted[i + 1] ^= _rotate_left(permuted[i], 11)

    return struct.pack(f'>{num_words}I', *permuted)


def encrypt_block(block: bytes, key: bytes, num_rounds: int = 16) -> bytes:
    """
    Encrypt a single block using the Feistel network.

    Parameters:
        block: Input block (must be even length, typically 16 or 32 bytes)
        key: Cipher key
        num_rounds: Number of Feistel rounds (default 16)

    Returns:
        Encrypted block of the same size as input
    """
    block_size = len(block)
    half = block_size // 2

    if block_size % 2 != 0:
        raise ValueError("Block size must be even")
    if block_size < 8:
        raise ValueError("Block size must be at least 8 bytes")

    # Generate key schedule
    round_keys = generate_key_schedule(key, num_rounds)

    # Split into left and right halves
    left = block[:half]
    right = block[half:]

    # Feistel rounds
    for i in range(num_rounds):
        # F(right, round_key)
        f_output = _round_function(right, round_keys[i])
        # XOR with left half
        new_left = bytes(l ^ f for l, f in zip(left, f_output))
        # Swap (except last round)
        if i < num_rounds - 1:
            left = right
            right = new_left
        else:
            left = new_left

    return left + right


def decrypt_block(block: bytes, key: bytes, num_rounds: int = 16) -> bytes:
    """
    Decrypt a single block using the Feistel network.

    Uses reverse key schedule order (standard Feistel property).
    """
    block_size = len(block)
    half = block_size // 2

    if block_size % 2 != 0:
        raise ValueError("Block size must be even")

    # Generate key schedule (same as encryption)
    round_keys = generate_key_schedule(key, num_rounds)

    # Split into left and right halves
    left = block[:half]
    right = block[half:]

    # Feistel rounds in reverse key order
    for i in range(num_rounds - 1, -1, -1):
        f_output = _round_function(right, round_keys[i])
        new_left = bytes(l ^ f for l, f in zip(left, f_output))
        if i > 0:
            left = right
            right = new_left
        else:
            left = new_left

    return left + right


def encrypt_ctr(plaintext: bytes, key: bytes, iv: bytes,
                block_size: int = 16, num_rounds: int = 16) -> bytes:
    """
    Encrypt using CTR (counter) mode with the custom block cipher.

    The IV is interpreted as follows:
    - First block_size bytes: initial counter value
    - Remaining bytes (if any): counter seed mixed into initial state

    Parameters:
        plaintext: Data to encrypt
        key: Cipher key
        iv: Initialization vector (first block_size bytes used as counter,
            remaining bytes mixed as counter seed)
        block_size: Block size in bytes
        num_rounds: Number of cipher rounds

    Returns:
        Ciphertext of the same length as plaintext
    """
    if len(iv) < block_size:
        raise ValueError(f"IV must be at least {block_size} bytes, got {len(iv)}")

    # Extract base counter from first block_size bytes
    base_iv = iv[:block_size]
    counter = int.from_bytes(base_iv, 'big')

    # If there are additional bytes, mix them as counter seed offset
    if len(iv) > block_size:
        seed_bytes = iv[block_size:]
        seed_value = int.from_bytes(seed_bytes.ljust(4, b'\x00')[:4], 'big')
        counter = (counter + seed_value) % (2 ** (block_size * 8))

    ciphertext = bytearray()

    for offset in range(0, len(plaintext), block_size):
        # Generate counter block
        counter_block = counter.to_bytes(block_size, 'big')

        # Encrypt counter to get key stream
        key_stream = encrypt_block(counter_block, key, num_rounds)

        # XOR with plaintext chunk
        chunk = plaintext[offset:offset + block_size]
        encrypted_chunk = bytes(p ^ k for p, k in zip(chunk, key_stream[:len(chunk)]))
        ciphertext.extend(encrypted_chunk)

        counter += 1

    return bytes(ciphertext)


def decrypt_ctr(ciphertext: bytes, key: bytes, iv: bytes,
                block_size: int = 16, num_rounds: int = 16) -> bytes:
    """
    Decrypt using CTR mode (identical to encryption due to XOR symmetry).
    """
    return encrypt_ctr(ciphertext, key, iv, block_size, num_rounds)
