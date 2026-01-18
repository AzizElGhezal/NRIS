"""
Unit tests for encryption module.
"""

import pytest
from nris.encryption import (
    NoEncryption,
    FernetEncryption,
    FieldEncryptor,
    get_encryptor,
    generate_key,
    register_backend,
    EncryptionError,
    KeyDerivationError,
)


class TestNoEncryption:
    """Test cases for NoEncryption backend."""

    def test_encrypt_passthrough(self):
        """Encrypt should return plaintext unchanged."""
        enc = NoEncryption()
        assert enc.encrypt("test data") == "test data"

    def test_decrypt_passthrough(self):
        """Decrypt should return ciphertext unchanged."""
        enc = NoEncryption()
        assert enc.decrypt("test data") == "test data"

    def test_is_encrypted_always_false(self):
        """is_encrypted should always return False."""
        enc = NoEncryption()
        assert enc.is_encrypted("any data") is False
        assert enc.is_encrypted("") is False

    def test_empty_string(self):
        """Should handle empty strings."""
        enc = NoEncryption()
        assert enc.encrypt("") == ""
        assert enc.decrypt("") == ""


class TestFernetEncryption:
    """Test cases for FernetEncryption backend."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data should decrypt to original."""
        enc = FernetEncryption()
        plaintext = "sensitive patient data"
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypted_has_prefix(self):
        """Encrypted data should have FERNET: prefix."""
        enc = FernetEncryption()
        encrypted = enc.encrypt("test")
        assert encrypted.startswith("FERNET:")

    def test_is_encrypted_detects_prefix(self):
        """is_encrypted should detect FERNET: prefix."""
        enc = FernetEncryption()
        encrypted = enc.encrypt("test")
        assert enc.is_encrypted(encrypted) is True
        assert enc.is_encrypted("plain text") is False

    def test_decrypt_without_prefix(self):
        """Should handle encrypted data without prefix."""
        enc = FernetEncryption()
        encrypted = enc.encrypt("test")
        # Remove prefix manually
        without_prefix = encrypted[len("FERNET:"):]
        decrypted = enc.decrypt(without_prefix)
        assert decrypted == "test"

    def test_empty_string_passthrough(self):
        """Empty string should pass through unchanged."""
        enc = FernetEncryption()
        assert enc.encrypt("") == ""
        assert enc.decrypt("") == ""

    def test_different_keys_incompatible(self):
        """Data encrypted with one key shouldn't decrypt with another."""
        enc1 = FernetEncryption()
        enc2 = FernetEncryption()

        encrypted = enc1.encrypt("secret")

        with pytest.raises(EncryptionError):
            # Remove prefix first since prefix is same
            enc2.decrypt(encrypted[len("FERNET:"):])

    def test_unicode_support(self):
        """Should handle unicode characters."""
        enc = FernetEncryption()
        plaintext = "患者名: 山田太郎 émojis: 🧬🔬"
        encrypted = enc.encrypt(plaintext)
        decrypted = enc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_key_property(self):
        """Should expose the encryption key."""
        enc = FernetEncryption()
        key = enc.key
        assert key is not None
        assert len(key) > 0

    def test_custom_key(self):
        """Should work with provided key."""
        key = generate_key()
        enc = FernetEncryption(key=key)
        encrypted = enc.encrypt("test")
        decrypted = enc.decrypt(encrypted)
        assert decrypted == "test"

    def test_key_reuse(self):
        """Same key should decrypt data across instances."""
        key = generate_key()
        enc1 = FernetEncryption(key=key)
        enc2 = FernetEncryption(key=key)

        encrypted = enc1.encrypt("shared secret")
        decrypted = enc2.decrypt(encrypted)
        assert decrypted == "shared secret"


class TestFieldEncryptor:
    """Test cases for FieldEncryptor."""

    def test_encrypts_specified_fields(self):
        """Should encrypt only specified fields."""
        backend = FernetEncryption()
        encryptor = FieldEncryptor(backend, encrypted_fields={'name', 'ssn'})

        data = {'name': 'John Doe', 'ssn': '123-45-6789', 'age': 35}
        encrypted = encryptor.encrypt_dict(data)

        assert encrypted['name'].startswith('FERNET:')
        assert encrypted['ssn'].startswith('FERNET:')
        assert encrypted['age'] == 35  # Not encrypted

    def test_decrypts_specified_fields(self):
        """Should decrypt only encrypted fields."""
        backend = FernetEncryption()
        encryptor = FieldEncryptor(backend, encrypted_fields={'name'})

        original = {'name': 'Jane Doe', 'age': 30}
        encrypted = encryptor.encrypt_dict(original)
        decrypted = encryptor.decrypt_dict(encrypted)

        assert decrypted['name'] == 'Jane Doe'
        assert decrypted['age'] == 30

    def test_handles_nested_dicts(self):
        """Should handle nested dictionaries."""
        backend = FernetEncryption()
        encryptor = FieldEncryptor(backend, encrypted_fields={'name'})

        data = {'patient': {'name': 'Test User', 'id': 1}}
        encrypted = encryptor.encrypt_dict(data)

        assert encrypted['patient']['name'].startswith('FERNET:')
        assert encrypted['patient']['id'] == 1

    def test_handles_unencrypted_data(self):
        """decrypt_dict should handle already-decrypted data."""
        backend = FernetEncryption()
        encryptor = FieldEncryptor(backend, encrypted_fields={'name'})

        # Data that was never encrypted
        data = {'name': 'Plain Name', 'age': 25}
        decrypted = encryptor.decrypt_dict(data)

        assert decrypted['name'] == 'Plain Name'

    def test_default_fields(self):
        """Should use default sensitive fields."""
        backend = FernetEncryption()
        encryptor = FieldEncryptor(backend)

        # Default fields include 'full_name', 'mrn_id', etc.
        data = {'full_name': 'Patient Name', 'mrn_id': '12345', 'panel_type': 'Standard'}
        encrypted = encryptor.encrypt_dict(data)

        assert encrypted['full_name'].startswith('FERNET:')
        assert encrypted['mrn_id'].startswith('FERNET:')
        assert encrypted['panel_type'] == 'Standard'


class TestGetEncryptor:
    """Test cases for get_encryptor factory function."""

    def test_get_none_backend(self):
        """Should return NoEncryption for 'none'."""
        enc = get_encryptor('none')
        assert isinstance(enc, NoEncryption)

    def test_get_fernet_backend(self):
        """Should return FernetEncryption for 'fernet'."""
        enc = get_encryptor('fernet')
        assert isinstance(enc, FernetEncryption)

    def test_case_insensitive(self):
        """Backend name should be case-insensitive."""
        enc1 = get_encryptor('NONE')
        enc2 = get_encryptor('None')
        assert isinstance(enc1, NoEncryption)
        assert isinstance(enc2, NoEncryption)

    def test_unknown_backend_raises(self):
        """Unknown backend should raise ValueError."""
        with pytest.raises(ValueError) as excinfo:
            get_encryptor('unknown')
        assert 'unknown' in str(excinfo.value).lower()

    def test_passes_kwargs(self):
        """Should pass kwargs to backend constructor."""
        key = generate_key()
        enc = get_encryptor('fernet', key=key)
        assert enc.key == key


class TestGenerateKey:
    """Test cases for key generation."""

    def test_generates_valid_key(self):
        """Should generate a valid base64 key."""
        key = generate_key()
        assert key is not None
        assert len(key) == 44  # 32 bytes base64 encoded

    def test_keys_are_unique(self):
        """Each call should generate a unique key."""
        keys = [generate_key() for _ in range(10)]
        assert len(set(keys)) == 10  # All unique

    def test_key_works_with_fernet(self):
        """Generated key should work with FernetEncryption."""
        key = generate_key()
        enc = FernetEncryption(key=key)
        encrypted = enc.encrypt("test")
        decrypted = enc.decrypt(encrypted)
        assert decrypted == "test"


class TestRegisterBackend:
    """Test cases for custom backend registration."""

    def test_register_custom_backend(self):
        """Should register and use custom backend."""
        class CustomBackend:
            def encrypt(self, plaintext: str) -> str:
                return f"CUSTOM:{plaintext}"

            def decrypt(self, ciphertext: str) -> str:
                return ciphertext[7:]  # Remove "CUSTOM:"

            def is_encrypted(self, data: str) -> bool:
                return data.startswith("CUSTOM:")

        register_backend('custom_test', CustomBackend)
        enc = get_encryptor('custom_test')

        encrypted = enc.encrypt("test")
        assert encrypted == "CUSTOM:test"
        assert enc.decrypt(encrypted) == "test"
