"""
Unit tests for migrations module.
"""

import sqlite3
import pytest
from unittest.mock import patch

from nris.migrations import (
    Migration,
    MigrationManager,
    MigrationError,
    run_migrations,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing with full schema."""
    db_file = tmp_path / "test_migrations.db"
    # Create tables with full schema matching production
    conn = sqlite3.connect(str(db_file))
    conn.execute("""
        CREATE TABLE patients (
            id INTEGER PRIMARY KEY,
            full_name TEXT,
            mrn_id TEXT,
            age INTEGER,
            weight_kg REAL,
            height_cm INTEGER,
            bmi REAL,
            weeks INTEGER,
            clinical_notes TEXT,
            created_at TEXT,
            created_by INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE results (
            id INTEGER PRIMARY KEY,
            patient_id INTEGER,
            panel_type TEXT,
            qc_status TEXT,
            qc_details TEXT,
            qc_advice TEXT,
            qc_metrics_json TEXT,
            t21_res TEXT,
            t18_res TEXT,
            t13_res TEXT,
            sca_res TEXT,
            cnv_json TEXT,
            rat_json TEXT,
            full_z_json TEXT,
            final_summary TEXT,
            created_at TEXT,
            created_by INTEGER,
            test_number INTEGER DEFAULT 1
        )
    """)
    conn.execute("""
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()
    return str(db_file)


class TestMigration:
    """Test cases for Migration dataclass."""

    def test_migration_creation(self):
        """Should create migration with required fields."""
        migration = Migration(
            version="001",
            description="Test migration",
            up=["CREATE TABLE test (id INTEGER)"],
            down=["DROP TABLE test"]
        )
        assert migration.version == "001"
        assert migration.description == "Test migration"
        assert len(migration.up) == 1
        assert len(migration.down) == 1

    def test_migration_default_values(self):
        """Should have empty lists as defaults."""
        migration = Migration(version="001", description="Test")
        assert migration.up == []
        assert migration.down == []
        assert migration.up_callable is None
        assert migration.down_callable is None


class TestMigrationManager:
    """Test cases for MigrationManager."""

    def test_creates_version_table(self, temp_db):
        """Should create version tracking table."""
        manager = MigrationManager(temp_db)
        manager.get_status()

        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='_schema_migrations'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_migrate_applies_migrations(self, temp_db):
        """Should apply pending migrations."""
        manager = MigrationManager(temp_db)
        applied = manager.migrate()

        assert len(applied) > 0
        status = manager.get_status()
        assert status['applied_count'] > 0

    def test_migrate_is_idempotent(self, temp_db):
        """Running migrate twice should not reapply migrations."""
        manager = MigrationManager(temp_db)

        first_run = manager.migrate()
        second_run = manager.migrate()

        assert len(first_run) > 0
        assert len(second_run) == 0

    def test_get_pending(self, temp_db):
        """Should list pending migrations."""
        manager = MigrationManager(temp_db)
        pending_before = manager.get_pending()

        assert len(pending_before) > 0

        manager.migrate()
        pending_after = manager.get_pending()

        assert len(pending_after) == 0

    def test_get_status(self, temp_db):
        """Should return comprehensive status."""
        manager = MigrationManager(temp_db)
        manager.migrate()

        status = manager.get_status()

        assert 'current_version' in status
        assert 'applied_count' in status
        assert 'pending_count' in status
        assert 'applied' in status
        assert 'pending' in status
        assert isinstance(status['applied'], list)

    def test_get_history(self, temp_db):
        """Should return migration history."""
        manager = MigrationManager(temp_db)
        manager.migrate()

        history = manager.get_history()

        assert len(history) > 0
        assert 'version' in history[0]
        assert 'description' in history[0]
        assert 'applied_at' in history[0]
        assert 'checksum' in history[0]

    def test_rollback_single(self, temp_db):
        """Should rollback single migration."""
        manager = MigrationManager(temp_db)
        manager.migrate()

        status_before = manager.get_status()
        rolled_back = manager.rollback(steps=1)

        status_after = manager.get_status()
        assert status_after['applied_count'] == status_before['applied_count'] - 1
        assert len(rolled_back) == 1

    def test_rollback_to_version(self, temp_db):
        """Should rollback to specific version."""
        manager = MigrationManager(temp_db)
        manager.migrate()

        # Get first applied version
        history = manager.get_history()
        if len(history) >= 2:
            target = history[0]['version']
            manager.rollback_to(target)

            status = manager.get_status()
            assert status['current_version'] == target

    def test_register_custom_migration(self, temp_db):
        """Should register and apply custom migration."""
        manager = MigrationManager(temp_db)
        manager.migrate()  # Apply built-in first

        custom = Migration(
            version="999",
            description="Custom test migration",
            up=["CREATE TABLE custom_test (id INTEGER PRIMARY KEY)"],
            down=["DROP TABLE custom_test"]
        )
        manager.register(custom)

        applied = manager.migrate()
        assert "999" in applied

        # Verify table was created
        conn = sqlite3.connect(temp_db)
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='custom_test'"
        )
        assert cursor.fetchone() is not None
        conn.close()

    def test_migrate_to_target_version(self, temp_db):
        """Should stop at target version."""
        manager = MigrationManager(temp_db)

        # Migrate only to version 001
        applied = manager.migrate(target_version="001")

        status = manager.get_status()
        assert status['current_version'] == "001"
        assert status['pending_count'] > 0

    def test_handles_duplicate_column_error(self, temp_db):
        """Should handle 'duplicate column' errors gracefully."""
        manager = MigrationManager(temp_db)
        manager.migrate()

        # Try to add same column again
        duplicate = Migration(
            version="998",
            description="Duplicate column test",
            up=["ALTER TABLE patients ADD COLUMN full_name TEXT"],  # Already exists
            down=[]
        )
        manager.register(duplicate)

        # Should not raise
        applied = manager.migrate()
        assert "998" in applied


class TestRunMigrations:
    """Test cases for run_migrations convenience function."""

    def test_run_migrations(self, temp_db):
        """Should apply migrations via convenience function."""
        applied = run_migrations(temp_db)
        assert len(applied) > 0

    def test_run_migrations_idempotent(self, temp_db):
        """Should be idempotent."""
        first = run_migrations(temp_db)
        second = run_migrations(temp_db)

        assert len(first) > 0
        assert len(second) == 0
