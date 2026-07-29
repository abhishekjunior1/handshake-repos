"""Key Encapsulator — RSA-OAEP key encapsulation mechanism (KEM).

Implements KEM using RSA-OAEP for wrapping a randomly generated shared secret.
The encapsulated key can be transported to the recipient who uses their private
key to recover the shared secret.
"""

import os
import hashlib
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend


# Maximum plaintext lengths for RSA-OAEP with SHA-256
# Formula: key_bytes - 2*hash_bytes - 2
RSA_OAEP_OVERHEAD = 66  # 2*32 + 2 for SHA-256


def generate_kem_keypair(key_bits):
    """Generate an RSA keypair for key encapsulation.

    Args:
        key_bits: RSA key size in bits (2048, 3072, or 4096).

    Returns:
        Tuple of (private_key, public_key) objects.
    """
    if key_bits not in (2048, 3072, 4096):
        raise ValueError(f"Unsupported RSA key size: {key_bits}. Use 2048, 3072, or 4096.")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_bits,
        backend=default_backend()
    )
    public_key = private_key.public_key()

    return private_key, public_key


def _compute_shared_secret_length(key_bits):
    """Determine the length of the random shared secret to generate.

    The shared secret should be long enough to provide sufficient entropy
    for the HKDF step that follows. We use 32 bytes (256 bits) as the
    standard size, which fits within RSA-OAEP capacity for all supported
    key sizes.
    """
    # 32 bytes provides 256 bits of entropy for HKDF input
    return 32


def _create_oaep_padding():
    """Create the RSA-OAEP padding configuration.

    Uses SHA-256 for both the hash function and the MGF1 mask generation
    function, following NIST recommendations for modern RSA-OAEP usage.
    """
    oaep_padding = padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
    return oaep_padding


def encapsulate_key(public_key, key_bits):
    """Perform KEM encapsulation — generate and wrap a shared secret.

    Generates a random shared secret and encrypts it using RSA-OAEP with
    the recipient's public key. The encrypted shared secret (encapsulated key)
    can be safely transmitted.

    Args:
        public_key: RSA public key object for the recipient.
        key_bits: RSA key size in bits (for validation).

    Returns:
        Tuple of (shared_secret_bytes, encapsulated_key_bytes).
    """
    secret_length = _compute_shared_secret_length(key_bits)
    shared_secret = os.urandom(secret_length)

    oaep_pad = _create_oaep_padding()
    encapsulated_key = public_key.encrypt(shared_secret, oaep_pad)

    return shared_secret, encapsulated_key


def decapsulate_key(private_key, encapsulated_key):
    """Perform KEM decapsulation — recover the shared secret.

    Decrypts the encapsulated key using the recipient's private key to
    recover the original shared secret.

    Args:
        private_key: RSA private key object.
        encapsulated_key: The encrypted shared secret bytes.

    Returns:
        The recovered shared secret bytes.
    """
    oaep_pad = _create_oaep_padding()
    shared_secret = private_key.decrypt(encapsulated_key, oaep_pad)

    return shared_secret


def serialize_public_key(public_key):
    """Serialize an RSA public key to PEM format.

    Args:
        public_key: RSA public key object.

    Returns:
        PEM-encoded public key bytes.
    """
    pem_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem_bytes


def serialize_private_key(private_key, password=None):
    """Serialize an RSA private key to PEM format.

    Args:
        private_key: RSA private key object.
        password: Optional password for key encryption.

    Returns:
        PEM-encoded private key bytes.
    """
    encryption = serialization.NoEncryption()
    if password:
        encryption = serialization.BestAvailableEncryption(password.encode('utf-8'))

    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption
    )
    return pem_bytes


def compute_key_fingerprint(public_key):
    """Compute a SHA-256 fingerprint of the public key.

    Used for key identification in envelope headers without exposing
    the full key material.

    Args:
        public_key: RSA public key object.

    Returns:
        Hex-encoded SHA-256 fingerprint string.
    """
    der_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    fingerprint = hashlib.sha256(der_bytes).hexdigest()
    return fingerprint
