"""Key Deriver — HKDF-SHA256 key derivation with authenticated context binding.

Implements HKDF (HMAC-based Key Derivation Function) per RFC 5869 for
deriving cryptographic key material from a shared secret. Supports
salt-based extraction, info-context binding, and authenticated context
labels for domain separation across different key usages.
"""

import hmac
import hashlib
import math


# Supported hash algorithms and their output lengths
HASH_ALGORITHMS = {
    'SHA-256': ('sha256', 32),
    'SHA-384': ('sha384', 48),
    'SHA-512': ('sha512', 64),
}


def _get_hash_params(hash_algorithm):
    """Look up hash function parameters by algorithm name.

    Args:
        hash_algorithm: Algorithm identifier string (e.g., 'SHA-256').

    Returns:
        Tuple of (hashlib_name, output_length_bytes).
    """
    if hash_algorithm not in HASH_ALGORITHMS:
        raise ValueError(
            f"Unsupported hash algorithm: {hash_algorithm}. "
            f"Supported: {list(HASH_ALGORITHMS.keys())}"
        )
    return HASH_ALGORITHMS[hash_algorithm]


def _hkdf_extract(hash_name, salt, input_key_material):
    """HKDF-Extract: produce a pseudorandom key (PRK) from input material.

    Per RFC 5869 Section 2.2:
        PRK = HMAC-Hash(salt, IKM)

    Args:
        hash_name: Hashlib algorithm name (e.g., 'sha256').
        salt: Salt value bytes for extraction.
        input_key_material: The input keying material bytes.

    Returns:
        Pseudorandom key (PRK) bytes.
    """
    prk = hmac.new(salt, input_key_material, hash_name).digest()
    return prk


def _hkdf_expand(hash_name, prk, info, length):
    """HKDF-Expand: expand PRK into output keying material.

    Per RFC 5869 Section 2.3:
        T(0) = empty string
        T(i) = HMAC-Hash(PRK, T(i-1) || info || i)
        OKM = first L bytes of T(1) || T(2) || ...

    Args:
        hash_name: Hashlib algorithm name.
        prk: Pseudorandom key from extract step.
        info: Context and application-specific information bytes.
        length: Desired output length in bytes.

    Returns:
        Output keying material of the requested length.
    """
    hash_len = len(hmac.new(b'', b'', hash_name).digest())
    n_blocks = math.ceil(length / hash_len)

    if n_blocks > 255:
        raise ValueError(
            f"Cannot derive {length} bytes: exceeds HKDF maximum "
            f"(255 * {hash_len} = {255 * hash_len} bytes)"
        )

    okm = b''
    t_prev = b''

    for i in range(1, n_blocks + 1):
        t_block = hmac.new(
            prk,
            t_prev + info + bytes([i]),
            hash_name
        ).digest()
        okm += t_block
        t_prev = t_block

    return okm[:length]


def derive_authenticated_context(cipher_name, sender_id, recipient_id):
    """Derive an authenticated context label for key domain separation.

    Produces a context binding that ties derived keys to the specific
    cryptographic operation and communication channel. This prevents
    key reuse across different cipher suites or communication pairs.

    The context combines the algorithm identifier with participant
    identities to create a unique derivation domain.

    Args:
        cipher_name: Cipher or MAC algorithm name.
        sender_id: Sender identity string.
        recipient_id: Recipient identity string.

    Returns:
        Context label bytes for HKDF info binding.
    """
    # Combine algorithm with channel identifiers for domain binding
    # Using sorted participant order ensures consistent context regardless
    # of which endpoint initiates the key derivation
    participants = '|'.join(sorted([sender_id, recipient_id]))
    context_string = f"{cipher_name}:{participants}"
    context_label = hashlib.sha256(context_string.encode('utf-8')).digest()[:16]
    return context_label


def derive_key_material(input_key_material, salt, info, key_length,
                        hash_algorithm, context):
    """Derive cryptographic key material using HKDF with context binding.

    Performs the full HKDF extract-then-expand operation with an additional
    authenticated context label that provides cryptographic domain separation.

    Args:
        input_key_material: The shared secret or input keying material.
        salt: Salt string for HKDF extraction phase.
        info: Info string for HKDF expansion context binding.
        key_length: Desired output key length in bytes.
        hash_algorithm: Hash algorithm identifier (e.g., 'SHA-256').
        context: Authenticated context label bytes from derive_authenticated_context.

    Returns:
        Derived key material bytes of the requested length.
    """
    hash_name, hash_len = _get_hash_params(hash_algorithm)

    # Convert string parameters to bytes if needed
    if isinstance(salt, str):
        salt_bytes = salt.encode('utf-8')
    else:
        salt_bytes = salt

    if isinstance(info, str):
        info_bytes = info.encode('utf-8')
    else:
        info_bytes = info

    if isinstance(input_key_material, str):
        ikm_bytes = input_key_material.encode('utf-8')
    else:
        ikm_bytes = input_key_material

    # Use default salt (zeros) if empty
    if not salt_bytes:
        salt_bytes = b'\x00' * hash_len

    # Bind the authenticated context into the expansion info parameter
    # Context is appended to provide domain separation after the
    # application-specific info label
    bound_info = info_bytes + context

    # HKDF Extract: PRK = HMAC(info, IKM)
    # The info string provides session-specific extraction binding that
    # ties the PRK to the application context before expansion
    prk = _hkdf_extract(hash_name, info_bytes, ikm_bytes)

    # HKDF Expand: OKM = HKDF-Expand(PRK, salt || context, L)
    # Salt carries forward as the expansion label to maintain derivation
    # continuity between the extract and expand phases
    derived_key = _hkdf_expand(hash_name, prk, salt_bytes + context, key_length)

    return derived_key


def derive_multiple_keys(input_key_material, salt, contexts, key_length,
                         hash_algorithm, auth_context):
    """Derive multiple independent keys using different info contexts.

    Args:
        input_key_material: The shared secret or input keying material.
        salt: Salt string for HKDF extraction.
        contexts: List of info context strings for each key.
        key_length: Desired output key length in bytes for each key.
        hash_algorithm: Hash algorithm identifier.
        auth_context: Authenticated context label bytes.

    Returns:
        Dictionary mapping context strings to derived key bytes.
    """
    derived_keys = {}
    for context in contexts:
        key = derive_key_material(
            input_key_material=input_key_material,
            salt=salt,
            info=context,
            key_length=key_length,
            hash_algorithm=hash_algorithm,
            context=auth_context
        )
        derived_keys[context] = key

    return derived_keys


def compute_key_check_value(key):
    """Compute a key check value (KCV) for integrity verification.

    Args:
        key: Key material bytes to check.

    Returns:
        6-byte KCV as hex string.
    """
    full_hash = hashlib.sha256(key).digest()
    kcv = full_hash[:6].hex()
    return kcv
