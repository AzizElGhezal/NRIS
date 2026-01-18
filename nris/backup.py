"""
Backup and data protection functions for NRIS.
"""

import os
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from .config import DB_FILE, BACKUP_DIR, MAX_BACKUPS


def ensure_backup_dir() -> Path:
    """Ensure backup directory exists and return its path."""
    backup_path = Path(BACKUP_DIR)
    backup_path.mkdir(exist_ok=True)
    return backup_path


def create_backup(reason: str = "manual") -> Optional[str]:
    """Create a timestamped backup of the database.

    Args:
        reason: Why backup was created (startup, periodic, manual, pre_import)

    Returns:
        Path to backup file or None if backup failed
    """
    if not os.path.exists(DB_FILE):
        return None

    try:
        backup_path = ensure_backup_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"nris_backup_{timestamp}_{reason}.db"
        backup_file = backup_path / backup_filename

        # Use SQLite's backup API for safe copying
        source_conn = sqlite3.connect(DB_FILE)
        dest_conn = sqlite3.connect(str(backup_file))
        source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()

        # Rotate old backups
        rotate_backups()

        return str(backup_file)
    except Exception as e:
        print(f"Backup failed: {e}")
        return None


def rotate_backups() -> None:
    """Remove old backups, keeping only the most recent MAX_BACKUPS."""
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
            except Exception:
                pass
    except Exception:
        pass


def list_backups() -> List[Dict[str, Any]]:
    """List all available backups with metadata."""
    try:
        backup_path = ensure_backup_dir()
        backups = []
        for backup_file in sorted(backup_path.glob("nris_backup_*.db"),
                                   key=lambda x: x.stat().st_mtime,
                                   reverse=True):
            stat = backup_file.stat()
            backups.append({
                'filename': backup_file.name,
                'path': str(backup_file),
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })
        return backups
    except Exception:
        return []


def restore_backup(backup_path: str) -> Tuple[bool, str]:
    """Restore database from a backup file.

    Args:
        backup_path: Path to the backup file

    Returns:
        Tuple of (success, message)
    """
    if not os.path.exists(backup_path):
        return False, "Backup file not found"

    try:
        # First, create a backup of current state
        create_backup("pre_restore")

        # Restore using SQLite backup API
        source_conn = sqlite3.connect(backup_path)
        dest_conn = sqlite3.connect(DB_FILE)
        source_conn.backup(dest_conn)
        source_conn.close()
        dest_conn.close()

        return True, "Database restored successfully"
    except Exception as e:
        return False, f"Restore failed: {e}"


def verify_database_integrity() -> Tuple[bool, str]:
    """Run SQLite integrity check on the database.

    Returns:
        Tuple of (is_ok, message)
    """
    if not os.path.exists(DB_FILE):
        return True, "Database does not exist yet (will be created)"

    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()[0]
        conn.close()

        if result == "ok":
            return True, "Database integrity verified"
        else:
            return False, f"Integrity issues found: {result}"
    except Exception as e:
        return False, f"Integrity check failed: {e}"


def startup_data_protection() -> Dict[str, Any]:
    """Perform startup data protection tasks.

    Creates a backup and verifies database integrity.

    Returns:
        Dictionary with status information
    """
    status = {
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
