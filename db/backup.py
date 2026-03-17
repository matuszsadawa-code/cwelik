#!/usr/bin/env python3
"""
Database backup and restore utility for OpenClaw Trading System.

Usage:
    python db/backup.py                          # Create a backup
    python db/backup.py --restore <backup_file>  # Restore from backup
    python db/backup.py --keep 7                 # Keep last N backups (default: 7)
"""

import argparse
import logging
import os
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Paths
DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "trading_system.db"
BACKUP_DIR = DB_DIR / "backups"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_backup(db_path: Path = DB_PATH, backup_dir: Path = BACKUP_DIR, keep: int = 7) -> Path:
    """
    Create a timestamped backup of the SQLite database using the online backup API.

    Args:
        db_path: Path to the source database file.
        backup_dir: Directory where backups are stored.
        keep: Maximum number of backups to retain.

    Returns:
        Path to the created backup file.

    Raises:
        FileNotFoundError: If the source database does not exist.
        RuntimeError: If the backup fails.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Source database not found: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"trading_system_{timestamp}.db"
    backup_path = backup_dir / backup_filename

    logger.info("Starting backup: %s -> %s", db_path, backup_path)

    try:
        # Use SQLite's built-in online backup API for safe hot backup
        src_conn = sqlite3.connect(str(db_path))
        dst_conn = sqlite3.connect(str(backup_path))
        try:
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
        except Exception:
            dst_conn.close()
            src_conn.close()
            raise
    except Exception as exc:
        # Clean up partial backup file if it was created
        if backup_path.exists():
            backup_path.unlink()
        raise RuntimeError(f"Backup failed: {exc}") from exc

    size_kb = backup_path.stat().st_size / 1024
    logger.info("Backup created successfully: %s (%.1f KB)", backup_path.name, size_kb)

    _prune_old_backups(backup_dir, keep)

    return backup_path


def _prune_old_backups(backup_dir: Path, keep: int) -> None:
    """Remove oldest backups when the count exceeds `keep`."""
    backups = sorted(backup_dir.glob("trading_system_*.db"))
    excess = len(backups) - keep
    if excess > 0:
        for old_backup in backups[:excess]:
            old_backup.unlink()
            logger.info("Removed old backup: %s", old_backup.name)


def restore_backup(backup_file: Path, db_path: Path = DB_PATH) -> None:
    """
    Restore the database from a backup file.

    The current database is replaced atomically: a temporary copy is written
    first, then swapped into place so the original is never left in a partial
    state.

    Args:
        backup_file: Path to the backup file to restore from.
        db_path: Path to the target database file.

    Raises:
        FileNotFoundError: If the backup file does not exist.
        RuntimeError: If the restore fails.
    """
    backup_file = Path(backup_file)
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    logger.info("Starting restore: %s -> %s", backup_file, db_path)

    # Write to a temp file first, then replace atomically
    tmp_path = db_path.with_suffix(".db.restoring")
    try:
        src_conn = sqlite3.connect(str(backup_file))
        dst_conn = sqlite3.connect(str(tmp_path))
        try:
            src_conn.backup(dst_conn)
            dst_conn.close()
            src_conn.close()
        except Exception:
            dst_conn.close()
            src_conn.close()
            raise

        shutil.move(str(tmp_path), str(db_path))
    except Exception as exc:
        if tmp_path.exists():
            tmp_path.unlink()
        raise RuntimeError(f"Restore failed: {exc}") from exc

    logger.info("Restore completed successfully from: %s", backup_file.name)


def verify_backup(backup_path: Path) -> bool:
    """
    Verify backup integrity by opening it and running a quick integrity check.

    Args:
        backup_path: Path to the backup file to verify.

    Returns:
        True if the backup is valid, False otherwise.
    """
    try:
        conn = sqlite3.connect(str(backup_path))
        cursor = conn.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        conn.close()
        ok = result is not None and result[0] == "ok"
        if ok:
            logger.info("Backup integrity check passed: %s", backup_path.name)
        else:
            logger.error("Backup integrity check FAILED: %s (result: %s)", backup_path.name, result)
        return ok
    except Exception as exc:
        logger.error("Backup integrity check error for %s: %s", backup_path, exc)
        return False


def list_backups(backup_dir: Path = BACKUP_DIR) -> list:
    """Return a sorted list of backup files (oldest first)."""
    if not backup_dir.exists():
        return []
    return sorted(backup_dir.glob("trading_system_*.db"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenClaw database backup and restore utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--restore",
        metavar="BACKUP_FILE",
        help="Restore database from the specified backup file",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=7,
        metavar="N",
        help="Number of backups to keep (default: 7)",
    )
    parser.add_argument(
        "--db",
        default=str(DB_PATH),
        metavar="DB_PATH",
        help=f"Path to the database file (default: {DB_PATH})",
    )
    parser.add_argument(
        "--backup-dir",
        default=str(BACKUP_DIR),
        metavar="DIR",
        help=f"Directory for backup files (default: {BACKUP_DIR})",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available backups",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    backup_dir = Path(args.backup_dir)

    if args.list:
        backups = list_backups(backup_dir)
        if not backups:
            print("No backups found.")
        else:
            print(f"Available backups in {backup_dir}:")
            for b in backups:
                size_kb = b.stat().st_size / 1024
                print(f"  {b.name}  ({size_kb:.1f} KB)")
        return 0

    if args.restore:
        try:
            restore_backup(Path(args.restore), db_path)
            return 0
        except (FileNotFoundError, RuntimeError) as exc:
            logger.error("Restore error: %s", exc)
            return 1

    # Default action: create a backup
    try:
        backup_path = create_backup(db_path, backup_dir, keep=args.keep)
        verify_backup(backup_path)
        return 0
    except (FileNotFoundError, RuntimeError) as exc:
        logger.error("Backup error: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
