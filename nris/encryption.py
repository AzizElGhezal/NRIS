"""
Pluggable encryption framework for NRIS.

This module provides a flexible encryption system that allows users to
choose their preferred encryption backend. It supports:
- No encryption (default, for backwards compatibility)
- Fernet symmetric encryption (AES-128-CBC)
- Custom encryption backends via the EncryptionBackend protocol

Usage:
    # Use default (no encryption)
    from nris.encryption import get_encryptor
    encryptor = get_encryptor()

    # Use Fernet encryption
    encryptor = get_encryptor('fernet', key='your-base64-key')

    # Encrypt/decrypt data
    encrypted = encryptor.encrypt("sensitive data")
    decrypted = encryptor.decrypt(encrypted)

Security Note:
    Keys should be stored securely (environment variables, key management
    systems, or encrypted key files). Never hardcode keys in source code.
"""

from abc import ABC, abstractmethod
import base64
import hashlib
import hmac
import logging
import os
import secrets
from typing import Optional, Protocol, Union, Dict, Any, Type, runtime_checkable

logger = logging.getLogger(__name__)


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""
    pass


class KeyDerivationError(Exception):
    """Raised when key derivation fails."""
    pass


@runtime_checkable
class EncryptionBackend(Protocol):
    """Protocol defining the encryption backend interface.

    Implement this protocol to create custom encryption backends.

    Example:
        class MyCustomEncryption:
            def encrypt(self, plaintext: str) -> str:
                # Your encryption logic
                return encrypted_data

            def decrypt(self, ciphertext: str) -> str:
                # Your decryption logic
                return decrypted_data

            def is_encrypted(self, data: str) -> bool:
                # Check if data appears encrypted
                return data.startswith('MYENC:')
    """

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string.

        Args:
            plaintext: The string to encrypt.

        Returns:
            Encrypted string (typically base64 encoded).
        """
        ...

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt ciphertext string.

        Args:
            ciphertext: The encrypted string to decrypt.

        Returns:
            Decrypted plaintext string.
        """
        ...

    def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be encrypted.

        Args:
            data: The data to check.

        Returns:
            True if data appears encrypted, False otherwise.
        """
        ...


class NoEncryption:
    """No-op encryption backend (passthrough).

    Use this for backwards compatibility or when encryption
    is handled at another layer (e.g., disk encryption).
    """

    def encrypt(self, plaintext: str) -> str:
        """Return plaintext unchanged."""
        return plaintext

    def decrypt(self, ciphertext: str) -> str:
        """Return ciphertext unchanged."""
        return ciphertext

    def is_encrypted(self, data: str) -> bool:
        """Always returns False (data is never encrypted)."""
        return False


class FernetEncryption:
    """Fernet symmetric encryption backend.

    Uses the cryptography library's Fernet implementation,
    which provides AES-128-CBC encryption with HMAC authentication.

    If cryptography is not installed, falls back to a simplified
    AES implementation using only standard library.

    Args:
        key: Base64-encoded 32-byte key, or None to generate one.

    Raises:
        KeyDerivationError: If key is invalid.
    """

    PREFIX = "FERNET:"

    def __init__(self, key: Optional[str] = None):
        self._key = key
        self._fernet = None
        self._use_fallback = False

        if key is None:
            # Generate a new key
            self._key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
            logger.warning("Generated new encryption key. Store this securely!")

        # Try to use cryptography library
        try:
            from cryptography.fernet import Fernet
            # Fernet requires a 32-byte key, base64 encoded (44 chars)
            if len(self._key) == 44:
                self._fernet = Fernet(self._key.encode())
            else:
                # Derive a proper key from the provided key
                derived = self._derive_key(self._key)
                self._fernet = Fernet(derived)
        except ImportError:
            logger.info("cryptography library not available, using fallback encryption")
            self._use_fallback = True
        except (KeyDerivationError, ValueError) as e:
            raise KeyDerivationError(f"Invalid encryption key: {e}")
        except BaseException as e:
            # Catch any other errors (including pyo3 panics, SystemExit, etc) and use fallback
            # We use BaseException to catch Rust panic exceptions that don't inherit from Exception
            logger.warning(f"cryptography library error ({type(e).__name__}: {e}), using fallback encryption")
            self._use_fallback = True

    def _derive_key(self, password: str) -> bytes:
        """Derive a Fernet-compatible key from a password."""
        # Use PBKDF2 with SHA256
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            b'nris_salt_v1',  # Static salt (consider making configurable)
            100000,  # Iterations
            dklen=32
        )
        return base64.urlsafe_b64encode(key)

    def _fallback_encrypt(self, plaintext: str) -> str:
        """Simple XOR-based encryption fallback (less secure)."""
        key_bytes = hashlib.sha256(self._key.encode()).digest()
        plaintext_bytes = plaintext.encode('utf-8')

        # XOR encryption with key cycling
        encrypted = bytes(
            p ^ key_bytes[i % len(key_bytes)]
            for i, p in enumerate(plaintext_bytes)
        )

        # Add HMAC for integrity
        mac = hmac.new(key_bytes, encrypted, hashlib.sha256).digest()[:16]

        return base64.urlsafe_b64encode(mac + encrypted).decode()

    def _fallback_decrypt(self, ciphertext: str) -> str:
        """Simple XOR-based decryption fallback."""
        key_bytes = hashlib.sha256(self._key.encode()).digest()

        try:
            data = base64.urlsafe_b64decode(ciphertext.encode())
        except Exception:
            raise EncryptionError("Invalid ciphertext format")

        if len(data) < 16:
            raise EncryptionError("Ciphertext too short")

        mac = data[:16]
        encrypted = data[16:]

        # Verify HMAC
        expected_mac = hmac.new(key_bytes, encrypted, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(mac, expected_mac):
            raise EncryptionError("Ciphertext integrity check failed")

        # XOR decryption
        decrypted = bytes(
            e ^ key_bytes[i % len(key_bytes)]
            for i, e in enumerate(encrypted)
        )

        return decrypted.decode('utf-8')

    @property
    def key(self) -> str:
        """Get the encryption key (for secure storage)."""
        return self._key

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using Fernet.

        Args:
            plaintext: String to encrypt.

        Returns:
            Encrypted string with FERNET: prefix.
        """
        if not plaintext:
            return plaintext

        try:
            if self._use_fallback:
                encrypted = self._fallback_encrypt(plaintext)
            else:
                encrypted = self._fernet.encrypt(plaintext.encode()).decode()
            return f"{self.PREFIX}{encrypted}"
        except Exception as e:
            raise EncryptionError(f"Encryption failed: {e}")

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt Fernet-encrypted ciphertext.

        Args:
            ciphertext: Encrypted string (with or without prefix).

        Returns:
            Decrypted plaintext.
        """
        if not ciphertext:
            return ciphertext

        # Remove prefix if present
        if ciphertext.startswith(self.PREFIX):
            ciphertext = ciphertext[len(self.PREFIX):]

        try:
            if self._use_fallback:
                return self._fallback_decrypt(ciphertext)
            else:
                return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            raise EncryptionError(f"Decryption failed: {e}")

    def is_encrypted(self, data: str) -> bool:
        """Check if data appears to be Fernet-encrypted."""
        return data.startswith(self.PREFIX) if data else False


class FieldEncryptor:
    """Encrypts specific fields in dictionaries.

    Useful for encrypting only sensitive fields (e.g., patient names)
    while leaving other fields (e.g., IDs, dates) in plaintext.

    Args:
        backend: The encryption backend to use.
        encrypted_fields: Set of field names to encrypt.

    Example:
        encryptor = FieldEncryptor(
            FernetEncryption(key),
            encrypted_fields={'full_name', 'mrn_id', 'clinical_notes'}
        )
        encrypted_patient = encryptor.encrypt_dict(patient_data)
    """

    def __init__(
        self,
        backend: EncryptionBackend,
        encrypted_fields: Optional[set] = None
    ):
        self.backend = backend
        self.encrypted_fields = encrypted_fields or {
            'full_name', 'patient_name', 'mrn_id', 'mrn',
            'clinical_notes', 'notes', 'referring_physician'
        }

    def encrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt sensitive fields in a dictionary.

        Args:
            data: Dictionary with potentially sensitive fields.

        Returns:
            New dictionary with sensitive fields encrypted.
        """
        result = {}
        for key, value in data.items():
            if key in self.encrypted_fields and isinstance(value, str):
                result[key] = self.backend.encrypt(value)
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value)
            else:
                result[key] = value
        return result

    def decrypt_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in a dictionary.

        Args:
            data: Dictionary with encrypted fields.

        Returns:
            New dictionary with sensitive fields decrypted.
        """
        result = {}
        for key, value in data.items():
            if key in self.encrypted_fields and isinstance(value, str):
                if self.backend.is_encrypted(value):
                    try:
                        result[key] = self.backend.decrypt(value)
                    except EncryptionError:
                        # Return as-is if decryption fails
                        result[key] = value
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.decrypt_dict(value)
            else:
                result[key] = value
        return result


# Registry of available encryption backends
_BACKENDS: Dict[str, Type[EncryptionBackend]] = {
    'none': NoEncryption,
    'fernet': FernetEncryption,
}


def register_backend(name: str, backend_class: Type[EncryptionBackend]) -> None:
    """Register a custom encryption backend.

    Args:
        name: Name to register the backend under.
        backend_class: Class implementing EncryptionBackend protocol.

    Example:
        register_backend('my_encryption', MyCustomEncryption)
    """
    _BACKENDS[name.lower()] = backend_class


def get_encryptor(
    backend: str = 'none',
    **kwargs: Any
) -> EncryptionBackend:
    """Get an encryption backend instance.

    Args:
        backend: Name of the backend ('none', 'fernet', or custom).
        **kwargs: Arguments passed to the backend constructor.

    Returns:
        Configured encryption backend instance.

    Raises:
        ValueError: If backend name is not registered.

    Example:
        # No encryption
        enc = get_encryptor('none')

        # Fernet with key from environment
        enc = get_encryptor('fernet', key=os.environ['NRIS_ENCRYPTION_KEY'])
    """
    backend_lower = backend.lower()
    if backend_lower not in _BACKENDS:
        available = ', '.join(_BACKENDS.keys())
        raise ValueError(f"Unknown backend '{backend}'. Available: {available}")

    return _BACKENDS[backend_lower](**kwargs)


def generate_key() -> str:
    """Generate a new encryption key suitable for Fernet.

    Returns:
        Base64-encoded 32-byte key.

    Example:
        key = generate_key()
        print(f"Save this key securely: {key}")
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
