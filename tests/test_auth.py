"""
Unit tests for authentication functions.
"""

import pytest
from datetime import datetime, timedelta
from nris.auth import (
    hash_password,
    verify_password,
    validate_password_strength,
    check_session_timeout,
    SESSION_TIMEOUT_MINUTES
)


class TestHashPassword:
    """Test cases for password hashing."""

    def test_hash_creates_salt_and_hash(self):
        """Hash should contain salt and hash separated by $."""
        hashed = hash_password("test123")
        parts = hashed.split('$')
        assert len(parts) == 2
        assert len(parts[0]) == 32  # Salt is 16 bytes = 32 hex chars
        assert len(parts[1]) == 64  # SHA256 is 64 hex chars

    def test_hash_is_deterministic_with_same_salt(self):
        """Same password with same salt should produce same hash."""
        # We can't directly test this since salt is random,
        # but we can verify through verify_password
        password = "mypassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed)

    def test_different_passwords_different_hashes(self):
        """Different passwords should produce different hashes."""
        hash1 = hash_password("password1")
        hash2 = hash_password("password2")
        # The hashes should be different (salt + hash)
        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Same password should produce different hashes (due to random salt)."""
        password = "samepassword"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2


class TestVerifyPassword:
    """Test cases for password verification."""

    def test_correct_password_verifies(self):
        """Correct password should verify successfully."""
        password = "correctpassword"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        """Wrong password should fail verification."""
        password = "correctpassword"
        hashed = hash_password(password)
        assert verify_password("wrongpassword", hashed) is False

    def test_empty_password_fails(self):
        """Empty password should fail verification."""
        hashed = hash_password("somepassword")
        assert verify_password("", hashed) is False

    def test_invalid_hash_format(self):
        """Invalid hash format should fail gracefully."""
        assert verify_password("password", "invalid_hash") is False
        assert verify_password("password", "") is False
        assert verify_password("password", "no_dollar_sign") is False

    def test_case_sensitive(self):
        """Password verification should be case-sensitive."""
        password = "CaseSensitive"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("casesensitive", hashed) is False
        assert verify_password("CASESENSITIVE", hashed) is False


class TestValidatePasswordStrength:
    """Test cases for password strength validation."""

    def test_valid_password(self):
        """Valid password should pass all checks."""
        is_valid, error = validate_password_strength("ValidPass1")
        assert is_valid is True
        assert error == ""

    def test_too_short(self):
        """Password < 8 chars should fail."""
        is_valid, error = validate_password_strength("Short1")
        assert is_valid is False
        assert "8 characters" in error

    def test_exactly_8_chars(self):
        """Password with exactly 8 chars should pass if other rules met."""
        is_valid, error = validate_password_strength("Abcdefg1")
        assert is_valid is True

    def test_no_uppercase(self):
        """Password without uppercase should fail."""
        is_valid, error = validate_password_strength("lowercase1")
        assert is_valid is False
        assert "uppercase" in error

    def test_no_lowercase(self):
        """Password without lowercase should fail."""
        is_valid, error = validate_password_strength("UPPERCASE1")
        assert is_valid is False
        assert "lowercase" in error

    def test_no_digit(self):
        """Password without digit should fail."""
        is_valid, error = validate_password_strength("NoDigitHere")
        assert is_valid is False
        assert "number" in error

    def test_complex_password(self):
        """Complex password with all requirements should pass."""
        is_valid, error = validate_password_strength("MyP@ssw0rd123!")
        assert is_valid is True

    def test_minimum_requirements(self):
        """Password with bare minimum requirements should pass."""
        is_valid, error = validate_password_strength("Aaaaaaaa1")
        assert is_valid is True


class TestCheckSessionTimeout:
    """Test cases for session timeout checking."""

    def test_recent_activity_valid(self):
        """Recent activity should be valid."""
        last_activity = datetime.now() - timedelta(minutes=5)
        is_valid, new_activity = check_session_timeout(last_activity)
        assert is_valid is True
        # New activity should be close to now
        assert (datetime.now() - new_activity).total_seconds() < 1

    def test_expired_session(self):
        """Expired session should be invalid."""
        last_activity = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MINUTES + 5)
        is_valid, new_activity = check_session_timeout(last_activity)
        assert is_valid is False
        # Last activity should be unchanged
        assert new_activity == last_activity

    def test_at_timeout_boundary(self):
        """Session at exactly timeout should be invalid."""
        last_activity = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MINUTES, seconds=1)
        is_valid, _ = check_session_timeout(last_activity)
        assert is_valid is False

    def test_just_before_timeout(self):
        """Session just before timeout should be valid."""
        last_activity = datetime.now() - timedelta(minutes=SESSION_TIMEOUT_MINUTES - 1)
        is_valid, _ = check_session_timeout(last_activity)
        assert is_valid is True
