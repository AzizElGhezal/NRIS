"""
Database migration framework for NRIS.

This module provides a simple but robust migration system for managing
database schema changes. Migrations are versioned and tracked to ensure
consistent database state across deployments.

Features:
- Automatic migration tracking with version table
- Forward migrations with rollback support
- Migration history and status reporting
- Safe transaction handling

Usage:
    from nris.migrations import MigrationManager

    manager = MigrationManager()
    manager.migrate()  # Apply all pending migrations

    # Check migration status
    status = manager.get_status()
    print(f"Current version: {status['current_version']}")
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass, field

from .config import DB_FILE

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a database migration.

    Attributes:
        version: Unique version identifier (e.g., "001", "002").
        description: Human-readable description of the migration.
        up: SQL statements or callable to apply the migration.
        down: SQL statements or callable to rollback the migration.
    """
    version: str
    description: str
    up: List[str] = field(default_factory=list)
    down: List[str] = field(default_factory=list)
    up_callable: Optional[Callable[[sqlite3.Connection], None]] = None
    down_callable: Optional[Callable[[sqlite3.Connection], None]] = None


class MigrationError(Exception):
    """Raised when a migration fails."""
    pass


class MigrationManager:
    """Manages database migrations.

    Tracks applied migrations in a version table and provides methods
    to apply pending migrations or rollback to a specific version.

    Args:
        db_path: Path to the SQLite database file.

    Example:
        manager = MigrationManager()

        # Apply all pending migrations
        applied = manager.migrate()
        print(f"Applied {len(applied)} migrations")

        # Rollback to specific version
        manager.rollback_to("002")
    """

    VERSION_TABLE = "_schema_migrations"

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or DB_FILE
        self._migrations: List[Migration] = []
        self._register_migrations()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _ensure_version_table(self, conn: sqlite3.Connection) -> None:
        """Create the migrations tracking table if it doesn't exist."""
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.VERSION_TABLE} (
                version TEXT PRIMARY KEY,
                description TEXT,
                applied_at TEXT NOT NULL,
                checksum TEXT
            )
        """)
        conn.commit()

    def _get_applied_versions(self, conn: sqlite3.Connection) -> set:
        """Get set of already applied migration versions."""
        self._ensure_version_table(conn)
        cursor = conn.execute(
            f"SELECT version FROM {self.VERSION_TABLE} ORDER BY version"
        )
        return {row[0] for row in cursor.fetchall()}

    def _record_migration(
        self,
        conn: sqlite3.Connection,
        migration: Migration
    ) -> None:
        """Record that a migration was applied."""
        conn.execute(
            f"""INSERT INTO {self.VERSION_TABLE}
                (version, description, applied_at, checksum)
                VALUES (?, ?, ?, ?)""",
            (
                migration.version,
                migration.description,
                datetime.now().isoformat(),
                self._compute_checksum(migration)
            )
        )

    def _remove_migration_record(
        self,
        conn: sqlite3.Connection,
        version: str
    ) -> None:
        """Remove a migration record (for rollback)."""
        conn.execute(
            f"DELETE FROM {self.VERSION_TABLE} WHERE version = ?",
            (version,)
        )

    def _compute_checksum(self, migration: Migration) -> str:
        """Compute a checksum for migration verification."""
        import hashlib
        content = f"{migration.version}:{migration.description}:{migration.up}"
        return hashlib.md5(content.encode()).hexdigest()[:8]

    def _register_migrations(self) -> None:
        """Register all available migrations."""
        # Migration 001: Add performance indexes
        self._migrations.append(Migration(
            version="001",
            description="Add performance indexes for common queries",
            up=[
                "CREATE INDEX IF NOT EXISTS idx_results_final_summary ON results(final_summary)",
                "CREATE INDEX IF NOT EXISTS idx_results_test_number ON results(test_number)",
                "CREATE INDEX IF NOT EXISTS idx_patients_full_name ON patients(full_name)",
                "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)",
            ],
            down=[
                "DROP INDEX IF EXISTS idx_results_final_summary",
                "DROP INDEX IF EXISTS idx_results_test_number",
                "DROP INDEX IF EXISTS idx_patients_full_name",
                "DROP INDEX IF EXISTS idx_audit_action",
            ]
        ))

        # Migration 002: Add encryption metadata columns
        self._migrations.append(Migration(
            version="002",
            description="Add encryption metadata support",
            up=[
                """ALTER TABLE patients ADD COLUMN encryption_version TEXT DEFAULT NULL""",
                """ALTER TABLE results ADD COLUMN encryption_version TEXT DEFAULT NULL""",
            ],
            down=[
                # SQLite doesn't support DROP COLUMN in older versions
                # These are no-ops for safety
            ]
        ))

        # Migration 003: Add query optimization columns
        self._migrations.append(Migration(
            version="003",
            description="Add columns for query optimization",
            up=[
                """ALTER TABLE results ADD COLUMN has_anomaly INTEGER DEFAULT 0""",
                """UPDATE results SET has_anomaly = 1 WHERE
                    final_summary LIKE '%POSITIVE%' OR
                    final_summary LIKE '%HIGH RISK%' OR
                    t21_res LIKE '%POSITIVE%' OR
                    t18_res LIKE '%POSITIVE%' OR
                    t13_res LIKE '%POSITIVE%'""",
                "CREATE INDEX IF NOT EXISTS idx_results_has_anomaly ON results(has_anomaly)",
            ],
            down=[
                "DROP INDEX IF EXISTS idx_results_has_anomaly",
            ]
        ))

        # Migration 004: Add caching support table
        self._migrations.append(Migration(
            version="004",
            description="Add analytics cache table",
            up=[
                """CREATE TABLE IF NOT EXISTS _analytics_cache (
                    cache_key TEXT PRIMARY KEY,
                    cache_value TEXT,
                    created_at TEXT,
                    expires_at TEXT
                )""",
                "CREATE INDEX IF NOT EXISTS idx_cache_expires ON _analytics_cache(expires_at)",
            ],
            down=[
                "DROP TABLE IF EXISTS _analytics_cache",
            ]
        ))

        # Migration 005: Add composite indexes for common queries
        self._migrations.append(Migration(
            version="005",
            description="Add composite indexes for registry queries",
            up=[
                "CREATE INDEX IF NOT EXISTS idx_results_patient_created ON results(patient_id, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_results_qc_created ON results(qc_status, created_at DESC)",
            ],
            down=[
                "DROP INDEX IF EXISTS idx_results_patient_created",
                "DROP INDEX IF EXISTS idx_results_qc_created",
            ]
        ))

    def register(self, migration: Migration) -> None:
        """Register a custom migration.

        Args:
            migration: Migration to register.
        """
        # Insert in version order
        for i, m in enumerate(self._migrations):
            if migration.version < m.version:
                self._migrations.insert(i, migration)
                return
        self._migrations.append(migration)

    def get_pending(self) -> List[Migration]:
        """Get list of pending (not yet applied) migrations.

        Returns:
            List of migrations that haven't been applied yet.
        """
        conn = self._get_connection()
        try:
            applied = self._get_applied_versions(conn)
            return [m for m in self._migrations if m.version not in applied]
        finally:
            conn.close()

    def migrate(self, target_version: Optional[str] = None) -> List[str]:
        """Apply pending migrations.

        Args:
            target_version: Stop after applying this version (optional).

        Returns:
            List of applied migration versions.

        Raises:
            MigrationError: If a migration fails.
        """
        conn = self._get_connection()
        applied_versions: List[str] = []

        try:
            applied = self._get_applied_versions(conn)

            for migration in self._migrations:
                if migration.version in applied:
                    continue

                if target_version and migration.version > target_version:
                    break

                logger.info(f"Applying migration {migration.version}: {migration.description}")

                try:
                    # Start transaction
                    conn.execute("BEGIN TRANSACTION")

                    # Apply SQL statements
                    for sql in migration.up:
                        try:
                            conn.execute(sql)
                        except sqlite3.OperationalError as e:
                            # Handle "duplicate column" errors gracefully
                            if "duplicate column" in str(e).lower():
                                logger.debug(f"Column already exists, skipping: {e}")
                            else:
                                raise

                    # Apply callable if present
                    if migration.up_callable:
                        migration.up_callable(conn)

                    # Record migration
                    self._record_migration(conn, migration)

                    conn.commit()
                    applied_versions.append(migration.version)
                    logger.info(f"Migration {migration.version} applied successfully")

                except Exception as e:
                    conn.rollback()
                    raise MigrationError(
                        f"Migration {migration.version} failed: {e}"
                    ) from e

            return applied_versions

        finally:
            conn.close()

    def rollback(self, steps: int = 1) -> List[str]:
        """Rollback the most recent migrations.

        Args:
            steps: Number of migrations to rollback.

        Returns:
            List of rolled back migration versions.
        """
        conn = self._get_connection()
        rolled_back: List[str] = []

        try:
            # Get applied migrations in reverse order
            cursor = conn.execute(
                f"SELECT version FROM {self.VERSION_TABLE} ORDER BY version DESC LIMIT ?",
                (steps,)
            )
            versions_to_rollback = [row[0] for row in cursor.fetchall()]

            for version in versions_to_rollback:
                migration = next(
                    (m for m in self._migrations if m.version == version),
                    None
                )
                if not migration:
                    logger.warning(f"Migration {version} not found, skipping")
                    continue

                logger.info(f"Rolling back migration {version}")

                try:
                    conn.execute("BEGIN TRANSACTION")

                    # Apply down SQL
                    for sql in migration.down:
                        conn.execute(sql)

                    # Apply down callable
                    if migration.down_callable:
                        migration.down_callable(conn)

                    self._remove_migration_record(conn, version)

                    conn.commit()
                    rolled_back.append(version)

                except Exception as e:
                    conn.rollback()
                    raise MigrationError(
                        f"Rollback of {version} failed: {e}"
                    ) from e

            return rolled_back

        finally:
            conn.close()

    def rollback_to(self, target_version: str) -> List[str]:
        """Rollback to a specific version.

        Args:
            target_version: Version to rollback to (this version stays applied).

        Returns:
            List of rolled back migration versions.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"SELECT version FROM {self.VERSION_TABLE} WHERE version > ? ORDER BY version DESC",
                (target_version,)
            )
            count = len(cursor.fetchall())
            return self.rollback(count) if count > 0 else []
        finally:
            conn.close()

    def get_status(self) -> Dict[str, Any]:
        """Get current migration status.

        Returns:
            Dictionary containing:
            - current_version: Latest applied migration version
            - applied_count: Number of applied migrations
            - pending_count: Number of pending migrations
            - applied: List of applied migration info
            - pending: List of pending migration info
        """
        conn = self._get_connection()
        try:
            self._ensure_version_table(conn)

            cursor = conn.execute(
                f"SELECT version, description, applied_at FROM {self.VERSION_TABLE} ORDER BY version"
            )
            applied_rows = cursor.fetchall()

            applied_versions = {row[0] for row in applied_rows}
            pending = [m for m in self._migrations if m.version not in applied_versions]

            return {
                'current_version': applied_rows[-1][0] if applied_rows else None,
                'applied_count': len(applied_rows),
                'pending_count': len(pending),
                'applied': [
                    {'version': row[0], 'description': row[1], 'applied_at': row[2]}
                    for row in applied_rows
                ],
                'pending': [
                    {'version': m.version, 'description': m.description}
                    for m in pending
                ]
            }
        finally:
            conn.close()

    def get_history(self) -> List[Dict[str, Any]]:
        """Get migration history.

        Returns:
            List of applied migrations with timestamps.
        """
        conn = self._get_connection()
        try:
            self._ensure_version_table(conn)
            cursor = conn.execute(
                f"SELECT version, description, applied_at, checksum FROM {self.VERSION_TABLE} ORDER BY version"
            )
            return [
                {
                    'version': row[0],
                    'description': row[1],
                    'applied_at': row[2],
                    'checksum': row[3]
                }
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()


def run_migrations(db_path: Optional[str] = None) -> List[str]:
    """Convenience function to run all pending migrations.

    Args:
        db_path: Optional database path override.

    Returns:
        List of applied migration versions.
    """
    manager = MigrationManager(db_path)
    return manager.migrate()
