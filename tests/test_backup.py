"""
Unit tests for backup module.
"""

import os
import sqlite3
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from nris.backup import (
    ensure_backup_dir,
    create_backup,
    rotate_backups,
    list_backups,
    restore_backup,
    verify_database_integrity,
    startup_data_protection,
    get_backup_stats,
    BackupError,
    RestoreError,
)


@pytest.fixture
def temp_db_dir(tmp_path):
    """Create a temporary directory structure for testing."""
    db_file = tmp_path / "test.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return {
        'db_file': str(db_file),
        'backup_dir': str(backup_dir),
        'tmp_path': tmp_path
    }


@pytest.fixture
def test_database(temp_db_dir):
    """Create a test database with sample data."""
    db_file = temp_db_dir['db_file']
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
    cursor.execute("INSERT INTO test (name) VALUES ('test_value')")
    conn.commit()
    conn.close()
    return db_file


class TestEnsureBackupDir:
    """Test cases for ensure_backup_dir function."""

    def test_creates_directory(self, tmp_path):
        """Should create directory if it doesn't exist."""
        new_dir = tmp_path / "new_backup_dir"
        with patch('nris.backup.BACKUP_DIR', str(new_dir)):
            result = ensure_backup_dir()
            assert result.exists()
            assert result.is_dir()

    def test_existing_directory(self, tmp_path):
        """Should handle existing directory."""
        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()
        with patch('nris.backup.BACKUP_DIR', str(existing_dir)):
            result = ensure_backup_dir()
            assert result.exists()


class TestCreateBackup:
    """Test cases for create_backup function."""

    def test_creates_backup_file(self, temp_db_dir, test_database):
        """Should create a backup file."""
        with patch('nris.backup.DB_FILE', test_database), \
             patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):
            result = create_backup("test")
            assert result is not None
            assert os.path.exists(result)
            assert "nris_backup_" in result
            assert "_test.db" in result

    def test_returns_none_if_no_database(self, temp_db_dir):
        """Should return None if database doesn't exist."""
        nonexistent = temp_db_dir['tmp_path'] / "nonexistent.db"
        with patch('nris.backup.DB_FILE', str(nonexistent)), \
             patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):
            result = create_backup("test")
            assert result is None

    def test_backup_contains_data(self, temp_db_dir, test_database):
        """Backup should contain the original data."""
        with patch('nris.backup.DB_FILE', test_database), \
             patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):
            backup_path = create_backup("test")

            # Verify backup has the data
            conn = sqlite3.connect(backup_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM test WHERE id = 1")
            result = cursor.fetchone()
            conn.close()

            assert result is not None
            assert result[0] == "test_value"

    def test_different_reasons(self, temp_db_dir, test_database):
        """Should include reason in filename."""
        with patch('nris.backup.DB_FILE', test_database), \
             patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):
            for reason in ["startup", "manual", "pre_import"]:
                result = create_backup(reason)
                assert f"_{reason}.db" in result


class TestRotateBackups:
    """Test cases for rotate_backups function."""

    def test_keeps_max_backups(self, temp_db_dir):
        """Should keep only MAX_BACKUPS files."""
        backup_dir = Path(temp_db_dir['backup_dir'])

        # Create more than MAX_BACKUPS backup files
        for i in range(15):
            (backup_dir / f"nris_backup_2024010{i:02d}_000000_test.db").touch()

        with patch('nris.backup.BACKUP_DIR', str(backup_dir)), \
             patch('nris.backup.MAX_BACKUPS', 10):
            deleted = rotate_backups()
            remaining = list(backup_dir.glob("nris_backup_*.db"))

            assert len(remaining) == 10
            assert deleted == 5

    def test_does_nothing_under_limit(self, temp_db_dir):
        """Should not delete anything if under limit."""
        backup_dir = Path(temp_db_dir['backup_dir'])

        # Create fewer than MAX_BACKUPS
        for i in range(3):
            (backup_dir / f"nris_backup_2024010{i}_000000_test.db").touch()

        with patch('nris.backup.BACKUP_DIR', str(backup_dir)), \
             patch('nris.backup.MAX_BACKUPS', 10):
            deleted = rotate_backups()
            remaining = list(backup_dir.glob("nris_backup_*.db"))

            assert len(remaining) == 3
            assert deleted == 0


class TestListBackups:
    """Test cases for list_backups function."""

    def test_lists_backup_files(self, temp_db_dir):
        """Should list all backup files with metadata."""
        backup_dir = Path(temp_db_dir['backup_dir'])

        # Create test backup files
        for i in range(3):
            backup_file = backup_dir / f"nris_backup_2024010{i}_000000_test.db"
            backup_file.write_bytes(b"test data " * 100)

        with patch('nris.backup.BACKUP_DIR', str(backup_dir)):
            backups = list_backups()

            assert len(backups) == 3
            for backup in backups:
                assert 'filename' in backup
                assert 'path' in backup
                assert 'size_mb' in backup
                assert 'created' in backup

    def test_empty_backup_dir(self, temp_db_dir):
        """Should return empty list if no backups."""
        with patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):
            backups = list_backups()
            assert backups == []

    def test_sorted_by_date(self, temp_db_dir):
        """Backups should be sorted newest first."""
        backup_dir = Path(temp_db_dir['backup_dir'])

        # Create files with different timestamps
        import time
        for i in range(3):
            backup_file = backup_dir / f"nris_backup_file{i}.db"
            backup_file.touch()
            time.sleep(0.1)

        with patch('nris.backup.BACKUP_DIR', str(backup_dir)):
            backups = list_backups()
            # Newest should be first
            assert "file2" in backups[0]['filename']


class TestRestoreBackup:
    """Test cases for restore_backup function."""

    def test_successful_restore(self, temp_db_dir, test_database):
        """Should restore database from backup."""
        backup_dir = temp_db_dir['backup_dir']

        with patch('nris.backup.DB_FILE', test_database), \
             patch('nris.backup.BACKUP_DIR', backup_dir):

            # Create a backup
            backup_path = create_backup("test")

            # Modify the original database
            conn = sqlite3.connect(test_database)
            cursor = conn.cursor()
            cursor.execute("UPDATE test SET name = 'modified' WHERE id = 1")
            conn.commit()
            conn.close()

            # Restore from backup
            success, msg = restore_backup(backup_path)

            assert success is True
            assert "successfully" in msg.lower()

            # Verify data was restored
            conn = sqlite3.connect(test_database)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM test WHERE id = 1")
            result = cursor.fetchone()
            conn.close()

            assert result[0] == "test_value"

    def test_nonexistent_backup(self, temp_db_dir):
        """Should fail for nonexistent backup file."""
        success, msg = restore_backup("/nonexistent/backup.db")
        assert success is False
        assert "not found" in msg.lower()

    def test_invalid_file_format(self, temp_db_dir):
        """Should fail for non-.db files."""
        txt_file = temp_db_dir['tmp_path'] / "backup.txt"
        txt_file.touch()

        success, msg = restore_backup(str(txt_file))
        assert success is False
        assert "invalid" in msg.lower()


class TestVerifyDatabaseIntegrity:
    """Test cases for verify_database_integrity function."""

    def test_valid_database(self, temp_db_dir, test_database):
        """Should pass for valid database."""
        with patch('nris.backup.DB_FILE', test_database):
            is_ok, msg = verify_database_integrity()
            assert is_ok is True
            assert "verified" in msg.lower()

    def test_nonexistent_database(self, temp_db_dir):
        """Should return True for nonexistent database."""
        nonexistent = temp_db_dir['tmp_path'] / "nonexistent.db"
        with patch('nris.backup.DB_FILE', str(nonexistent)):
            is_ok, msg = verify_database_integrity()
            assert is_ok is True
            assert "does not exist" in msg.lower()

    def test_corrupted_database(self, temp_db_dir):
        """Should fail for corrupted database."""
        corrupt_db = temp_db_dir['tmp_path'] / "corrupt.db"
        corrupt_db.write_bytes(b"not a valid sqlite database")

        with patch('nris.backup.DB_FILE', str(corrupt_db)):
            is_ok, msg = verify_database_integrity()
            assert is_ok is False


class TestStartupDataProtection:
    """Test cases for startup_data_protection function."""

    def test_with_existing_database(self, temp_db_dir, test_database):
        """Should create backup and verify integrity."""
        with patch('nris.backup.DB_FILE', test_database), \
             patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):

            status = startup_data_protection()

            assert status['integrity_ok'] is True
            assert status['backup_created'] is True
            assert status['backup_path'] is not None
            assert len(status['warnings']) == 0

    def test_without_database(self, temp_db_dir):
        """Should handle missing database gracefully."""
        nonexistent = temp_db_dir['tmp_path'] / "nonexistent.db"

        with patch('nris.backup.DB_FILE', str(nonexistent)), \
             patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):

            status = startup_data_protection()

            assert status['integrity_ok'] is True
            assert status['backup_created'] is False
            assert status['backup_path'] is None


class TestGetBackupStats:
    """Test cases for get_backup_stats function."""

    def test_with_backups(self, temp_db_dir):
        """Should return correct statistics."""
        backup_dir = Path(temp_db_dir['backup_dir'])

        # Create test backup files
        for i in range(3):
            backup_file = backup_dir / f"nris_backup_2024010{i}_000000_test.db"
            backup_file.write_bytes(b"x" * 1024 * 1024)  # 1 MB each

        with patch('nris.backup.BACKUP_DIR', str(backup_dir)):
            stats = get_backup_stats()

            assert stats['count'] == 3
            assert stats['total_size_mb'] >= 2.9  # ~3 MB
            assert stats['oldest'] is not None
            assert stats['newest'] is not None

    def test_empty_backup_dir(self, temp_db_dir):
        """Should return zeros for empty backup dir."""
        with patch('nris.backup.BACKUP_DIR', temp_db_dir['backup_dir']):
            stats = get_backup_stats()

            assert stats['count'] == 0
            assert stats['total_size_mb'] == 0.0
            assert stats['oldest'] is None
            assert stats['newest'] is None
