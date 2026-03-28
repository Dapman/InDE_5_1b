"""
InDE MVP v5.1b.0 - Connector Token Encryption

AES-256-GCM encryption for storing connector access tokens.
Tokens are encrypted before storage and decrypted only when needed for API calls.
The encryption key is read from CONNECTOR_ENCRYPTION_KEY environment variable.

SECURITY:
- Never log plaintext tokens
- Key must be 32 bytes (64 hex characters)
- Uses unique nonce for each encryption
- Includes authentication tag for integrity
"""

import os
import logging
from base64 import b64encode, b64decode
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

logger = logging.getLogger("inde.connectors.crypto")

# Cache the key instance (read once at startup)
_aesgcm_instance = None


def _get_aesgcm() -> AESGCM:
    """Get or create the AESGCM cipher instance."""
    global _aesgcm_instance

    if _aesgcm_instance is None:
        key_hex = os.getenv("CONNECTOR_ENCRYPTION_KEY")
        if not key_hex:
            raise ValueError("CONNECTOR_ENCRYPTION_KEY not set")

        try:
            key_bytes = bytes.fromhex(key_hex)
        except ValueError:
            raise ValueError("CONNECTOR_ENCRYPTION_KEY must be valid hex string")

        if len(key_bytes) != 32:
            raise ValueError(
                f"CONNECTOR_ENCRYPTION_KEY must be 32 bytes (64 hex chars), "
                f"got {len(key_bytes)} bytes"
            )

        _aesgcm_instance = AESGCM(key_bytes)

    return _aesgcm_instance


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a token using AES-256-GCM.

    Args:
        plaintext: The token to encrypt

    Returns:
        Base64-encoded ciphertext (nonce + ciphertext + tag)

    Raises:
        ValueError: If encryption key is not configured or invalid
    """
    if not plaintext:
        raise ValueError("Cannot encrypt empty token")

    aesgcm = _get_aesgcm()

    # Generate a unique 12-byte nonce for each encryption
    nonce = os.urandom(12)

    # Encrypt (returns ciphertext with appended authentication tag)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Combine nonce + ciphertext for storage
    combined = nonce + ciphertext

    # Base64 encode for safe storage in MongoDB
    return b64encode(combined).decode("ascii")


def decrypt_token(ciphertext: str) -> str:
    """
    Decrypt a token encrypted with encrypt_token.

    Args:
        ciphertext: Base64-encoded encrypted token

    Returns:
        The decrypted plaintext token

    Raises:
        ValueError: If decryption fails (invalid key, tampered data, etc.)
    """
    if not ciphertext:
        raise ValueError("Cannot decrypt empty ciphertext")

    aesgcm = _get_aesgcm()

    try:
        # Decode from base64
        combined = b64decode(ciphertext.encode("ascii"))

        # Extract nonce (first 12 bytes) and ciphertext+tag (rest)
        if len(combined) < 28:  # 12 (nonce) + 16 (min tag)
            raise ValueError("Invalid ciphertext: too short")

        nonce = combined[:12]
        encrypted_data = combined[12:]

        # Decrypt and verify authentication tag
        plaintext = aesgcm.decrypt(nonce, encrypted_data, None)

        return plaintext.decode("utf-8")

    except InvalidTag:
        logger.error("Token decryption failed: authentication tag invalid")
        raise ValueError("Token decryption failed: data may be corrupted or key incorrect")
    except Exception as e:
        logger.error(f"Token decryption failed: {e}")
        raise ValueError(f"Token decryption failed: {e}")


def validate_encryption_key() -> bool:
    """
    Validate that the encryption key is properly configured.

    Returns:
        True if key is valid, False otherwise
    """
    try:
        _get_aesgcm()
        return True
    except ValueError as e:
        logger.error(f"Encryption key validation failed: {e}")
        return False


def test_encryption_roundtrip() -> bool:
    """
    Test that encryption/decryption works correctly.

    Returns:
        True if roundtrip succeeds, False otherwise
    """
    try:
        test_token = "test_token_" + os.urandom(16).hex()
        encrypted = encrypt_token(test_token)
        decrypted = decrypt_token(encrypted)
        return decrypted == test_token
    except Exception as e:
        logger.error(f"Encryption roundtrip test failed: {e}")
        return False
