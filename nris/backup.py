"""
Backup and data protection functions for NRIS.

This module provides functionality for creating, managing, and restoring
database backups, as well as verifying database integrity.

Features:
    - Automatic backup creation with timestamping
    - Backup rotation to manage disk space
    - Database integrity verification
    - Safe restore operations with pre-restore backup

Dependencies:
    - sqlite3: For database operations
    - pathlib: For path handling

Example:
    >>> from nris.backup import create_backup, list_backups
    >>> backup_path = create_backup("manual")
    >>> backups = list_backups()
"""

import os
import sqlite3
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .config import DB_FILE, BACKUP_DIR, MAX_BACKUPS

# Set up module logger
logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Exception raised for backup-related errors."""
    pass


class RestoreError(Exception):
    """Exception raised for restore-related errors."""
    pass


def ensure_backup_dir() -> Path:
    """Ensure backup directory exists and return its path.

    Creates the backup directory if it doesn't exist.

    Returns:
        Path object pointing to the backup directory.

    Raises:
        OSError: If directory creation fails due to permissions or disk issues.
    """
    backup_path = Path(BACKUP_DIR)
    backup_path.mkdir(exist_ok=True, parents=True)
    return backup_path


def create_backup(reason: str = "manual") -> Optional[str]:
    """Create a timestamped backup of the database.

    Uses SQLite's backup API for safe, consistent backups even while
    the database is in use.

    Args:
        reason: Why backup was created. Common values:
            - "startup": Created on application startup
            - "manual": User-initiated backup
            - "pre_import": Before batch import
            - "pre_restore": Before restore operation
            - "periodic": Scheduled backup

    Returns:
        Path to backup file as string, or None if backup failed.

    Note:
        Returns None (doesn't raise) if database doesn't exist or
        backup fails, to allow graceful degradation.

    Example:
        >>> path = create_backup("manual")
        >>> if path:
        ...     print(f"Backup created: {path}")
    """
    if not os.path.exists(DB_FILE):
        logger.debug("No database file to backup")
        return None

    source_conn = None
    dest_conn = None

    try:
        backup_path = ensure_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nris_backup_{timestamp}_{reason}.db"
        backup_file = backup_path / backup_filename

        # Use SQLite's backup API for safe copying
        source_conn = sqlite3.connect(DB_FILE)
        dest_conn = sqlite3.connect(str(backup_file))
        source_conn.backup(dest_conn)

        logger.info(f"Backup created: {backup_file}")

        # Rotate old backups
        rotate_backups()

        return str(backup_file)

    except sqlite3.Error as e:
        logger.error(f"SQLite error during backup: {e}")
        return None
    except OSError as e:
        logger.error(f"OS error during backup: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during backup: {e}")
        return None
    finally:
        if source_conn:
            source_conn.close()
        if dest_conn:
            dest_conn.close()


def rotate_backups() -> int:
    """Remove old backups, keeping only the most recent MAX_BACKUPS.

    Returns:
        Number of backups deleted.

    Note:
        Silently handles errors when deleting individual backup files,
        logging warnings instead of raising exceptions.
    """
    deleted_count = 0

    try:
        backup_path = ensure_backup_dir()
        backups = sorted(
            [f for f in backup_path.glob("nris_backup_*.db")],
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )

        for old_backup in backups[MAX_BACKUPS:]:
            try:
                old_backup.unlink()
                deleted_count += 1
                logger.debug(f"Deleted old backup: {old_backup.name}")
            except PermissionError:
                logger.warning(f"Permission denied deleting backup: {old_backup.name}")
            except OSError as e:
                logger.warning(f"Could not delete backup {old_backup.name}: {e}")

    except OSError as e:
        logger.warning(f"Error during backup rotation: {e}")

    return deleted_count


def list_backups() -> List[Dict[str, Any]]:
    """List all available backups with metadata.

    Returns:
        List of dictionaries, each containing:
            - filename: Name of the backup file
            - path: Full path to the backup file
            - size_mb: File size in megabytes (rounded to 2 decimal places)
            - created: Creation timestamp as formatted string

        Returns empty list if no backups exist or on error.

    Example:
        >>> backups = list_backups()
        >>> for b in backups:
        ...     print(f"{b['filename']}: {b['size_mb']} MB")
    """
    try:
        backup_path = ensure_backup_dir()
        backups = []

        for backup_file in sorted(
            backup_path.glob("nris_backup_*.db"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        ):
            try:
                stat = backup_file.stat()
                backups.append({
                    'filename': backup_file.name,
                    'path': str(backup_file),
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
            except OSError as e:
                logger.warning(f"Could not stat backup {backup_file.name}: {e}")
                continue

        return backups

    except OSError as e:
        logger.error(f"Error listing backups: {e}")
        return []


def restore_backup(backup_path: str) -> Tuple[bool, str]:
    """Restore database from a backup file.

    Creates a pre-restore backup of the current database before
    restoring, allowing recovery if the restore causes issues.

    Args:
        backup_path: Path to the backup file to restore from.

    Returns:
        Tuple of (success: bool, message: str).
        On success, message is "Database restored successfully".
        On failure, message describes the error.

    Note:
        This operation will replace the entire current database.
        All current data will be lost (but saved in pre-restore backup).

    Example:
        >>> success, msg = restore_backup("/path/to/backup.db")
        >>> if success:
        ...     print("Restore complete!")
        ... else:
        ...     print(f"Restore failed: {msg}")
    """
    if not os.path.exists(backup_path):
        return False, "Backup file not found"

    if not backup_path.endswith('.db'):
        return False, "Invalid backup file format (must be .db file)"

    source_conn = None
    dest_conn = None

    try:
        # First, create a backup of current state
        pre_restore_backup = create_backup("pre_restore")
        if not pre_restore_backup and os.path.exists(DB_FILE):
            logger.warning("Could not create pre-restore backup, proceeding anyway")

        # Restore using SQLite backup API
        source_conn = sqlite3.connect(backup_path)
        dest_conn = sqlite3.connect(DB_FILE)
        source_conn.backup(dest_conn)

        logger.info(f"Database restored from: {backup_path}")
        return True, "Database restored successfully"

    except sqlite3.DatabaseError as e:
        logger.error(f"Database error during restore: {e}")
        return False, f"Invalid or corrupted backup file: {e}"
    except sqlite3.Error as e:
        logger.error(f"SQLite error during restore: {e}")
        return False, f"Restore failed: {e}"
    except OSError as e:
        logger.error(f"OS error during restore: {e}")
        return False, f"File access error: {e}"
    except Exception as e:
        logger.error(f"Unexpected error during restore: {e}")
        return False, f"Restore failed: {e}"
    finally:
        if source_conn:
            source_conn.close()
        if dest_conn:
            dest_conn.close()


def verify_database_integrity() -> Tuple[bool, str]:
    """Run SQLite integrity check on the database.

    Performs SQLite's built-in integrity_check PRAGMA to verify
    the database structure and detect corruption.

    Returns:
        Tuple of (is_ok: bool, message: str).
        is_ok is True if database passes integrity check.
        message provides details about the check result.

    Example:
        >>> ok, msg = verify_database_integrity()
        >>> if not ok:
        ...     print(f"Database corruption detected: {msg}")
    """
    if not os.path.exists(DB_FILE):
        return True, "Database does not exist yet (will be created)"

    conn = None
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]

        if result == "ok":
            logger.debug("Database integrity check passed")
            return True, "Database integrity verified"
        else:
            logger.warning(f"Database integrity issues: {result}")
            return False, f"Integrity issues found: {result}"

    except sqlite3.DatabaseError as e:
        logger.error(f"Database error during integrity check: {e}")
        return False, f"Database is corrupted or invalid: {e}"
    except sqlite3.Error as e:
        logger.error(f"SQLite error during integrity check: {e}")
        return False, f"Integrity check failed: {e}"
    except Exception as e:
        logger.error(f"Unexpected error during integrity check: {e}")
        return False, f"Integrity check failed: {e}"
    finally:
        if conn:
            conn.close()


def startup_data_protection() -> Dict[str, Any]:
    """Perform startup data protection tasks.

    Called during application startup to ensure data safety:
    1. Verifies database integrity
    2. Creates a startup backup

    Returns:
        Dictionary containing:
            - backup_created (bool): Whether backup was successfully created
            - backup_path (str|None): Path to backup file if created
            - integrity_ok (bool): Whether integrity check passed
            - integrity_message (str): Details about integrity check
            - warnings (List[str]): Any warnings encountered

    Example:
        >>> status = startup_data_protection()
        >>> if status['warnings']:
        ...     for warning in status['warnings']:
        ...         print(f"Warning: {warning}")
    """
    status: Dict[str, Any] = {
        'backup_created': False,
        'backup_path': None,
        'integrity_ok': False,
        'integrity_message': '',
        'warnings': []
    }

    # Check integrity first
    is_ok, message = verify_database_integrity()
    status['integrity_ok'] = is_ok
    status['integrity_message'] = message

    if not is_ok:
        status['warnings'].append(f"Database integrity issue: {message}")

    # Create startup backup (only if database exists)
    if os.path.exists(DB_FILE):
        backup_path = create_backup("startup")
        if backup_path:
            status['backup_created'] = True
            status['backup_path'] = backup_path
        else:
            status['warnings'].append("Failed to create startup backup")

    return status


def get_backup_stats() -> Dict[str, Any]:
    """Get statistics about current backups.

    Returns:
        Dictionary containing:
            - count (int): Number of backup files
            - total_size_mb (float): Total size of all backups
            - oldest (str|None): Timestamp of oldest backup
            - newest (str|None): Timestamp of newest backup
    """
    backups = list_backups()

    if not backups:
        return {
            'count': 0,
            'total_size_mb': 0.0,
            'oldest': None,
            'newest': None
        }

    return {
        'count': len(backups),
        'total_size_mb': round(sum(b['size_mb'] for b in backups), 2),
        'oldest': backups[-1]['created'] if backups else None,
        'newest': backups[0]['created'] if backups else None
    }
