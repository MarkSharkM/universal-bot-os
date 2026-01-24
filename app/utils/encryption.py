"""
Encryption utilities for sensitive data (bot tokens, API keys, etc.)
Uses Fernet (symmetric encryption) from cryptography library.
"""
import os
import logging
import hashlib
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_encryption_key() -> bytes:
    """
    Get or generate encryption key from SECRET_KEY.
    Uses PBKDF2HMAC to derive a 32-byte key from SECRET_KEY.
    
    Returns:
        32-byte encryption key suitable for Fernet
    """
    # Use SECRET_KEY as password (must be consistent)
    password = settings.SECRET_KEY.encode()
    
    # Use a fixed salt (stored in code - acceptable for this use case)
    # In production with multiple keys, store salt in env var
    salt = b'universal_bot_os_encryption_salt_v1'
    
    # Derive 32-byte key using PBKDF2HMAC
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return key


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a token (e.g., bot token, API key).
    
    Args:
        plaintext: Plain text token
    
    Returns:
        Encrypted token (base64 encoded)
    
    Example:
        encrypted = encrypt_token("123456:ABC-DEF...")
        # Returns: "gAAAAABhK3..."
    """
    if not plaintext:
        return plaintext
    
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted_bytes = f.encrypt(plaintext.encode())
        return encrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Error encrypting token: {e}")
        raise ValueError(f"Failed to encrypt token: {str(e)}")


def decrypt_token(encrypted: str) -> str:
    """
    Decrypt a token.
    
    Args:
        encrypted: Encrypted token (base64 encoded)
    
    Returns:
        Decrypted plain text token
    
    Raises:
        ValueError: If decryption fails (invalid key or corrupted data)
    
    Example:
        plaintext = decrypt_token("gAAAAABhK3...")
        # Returns: "123456:ABC-DEF..."
    """
    if not encrypted:
        return encrypted
    
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        decrypted_bytes = f.decrypt(encrypted.encode())
        return decrypted_bytes.decode()
    except Exception as e:
        logger.error(f"Error decrypting token: {e}")
        raise ValueError(f"Failed to decrypt token: {str(e)}")


def is_encrypted(token: str) -> bool:
    """
    Check if a token is already encrypted (heuristic check).
    
    Args:
        token: Token to check
    
    Returns:
        True if token appears to be encrypted, False otherwise
    
    Note:
        This is a heuristic check based on Fernet token format.
        Fernet tokens start with "gAAAAA" (base64 of version + timestamp).
    """
    if not token:
        return False
    
    # Check length (encrypted tokens are longer)
    if len(token) < 50:
        return False
    
    # Check if starts with Fernet prefix
    if token.startswith('gAAAAA'):
        return True
    
    # Try to decrypt (if successful, it's encrypted)
    try:
        decrypt_token(token)
        return True
    except:
        return False


def hash_token(token: str) -> str:
    """
    Create SHA-256 hash of a token for fast lookup without decryption.
    
    Security benefits:
    - O(1) database lookup instead of O(N) with decryption loop
    - Reduces attack surface by minimizing decryption operations
    - Standard practice for credential lookup (like password hashing)
    
    Args:
        token: Plain text token (e.g., Telegram bot token)
    
    Returns:
        Hex string of SHA-256 hash (64 characters)
    
    Example:
        >>> hash_token("123456:ABC-DEF")
        "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
    
    Note:
        This is a one-way hash. Cannot retrieve original token from hash.
        Use in combination with encryption: hash for lookup, encryption for storage.
    """
    if not token:
        return ""
    
    return hashlib.sha256(token.encode()).hexdigest()
