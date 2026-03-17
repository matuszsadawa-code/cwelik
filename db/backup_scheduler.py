#!/usr/bin/env python3
"""
Daily backup scheduler for the OpenClaw Trading System database.

Runs as a long-lived background process and triggers a backup once per day
at a configurable UTC time (default: 02:00).

Usage:
    python db/backup_scheduler.py                    # Run at 02:00 UTC daily
    python db/backup_scheduler.py --time 03:30       # Run at 03:30 UTC daily
    python db/backup_scheduler.py --keep 14          # Keep last 14 backups
    python db/backup_scheduler.py --once             # Run one backup immediately and exit

To run as a background process:
    nohup python db/backup_scheduler.py &

Alternatively, use a cron job (recommended for production):
    0 2 * * * /path/to/venv/bin/python /path/to/db/backup_scheduler.py --once
"""

import argparse
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Allow running from any working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from db.backup import BACKUP_DIR, DB_PATH, create_backup, verify_backup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def _seconds_until(hour: int, minute: int) -> float:
    """Return the number of seconds until the next occurrence of HH:MM UTC."""
    now = datetime.now(timezone.utc)
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        # Already past today's target — schedule for tomorrow
        from datetime import timedelta
        target += timedelta(days=1)
    return (target - now).total_seconds()


def run_backup(db_path: Path, backup_dir: Path, keep: int) -> bool:
    """Execute a single backup and verify it. Returns True on success."""
    try:
        backup_path = create_backup(db_path, backup_dir, keep=keep)
        ok = verify_backup(backup_path)
        if not ok:
            logger.warning("Backup created but integrity check failed: %s", backup_path)
        return ok
    except Exception as exc:
        logger.error("Scheduled backup failed: %s", exc)
        return False


def run_scheduler(
    hour: int,
    minute: int,
    db_path: Path,
    backup_dir: Path,
    keep: int,
) -> None:
    """
    Loop forever, sleeping until the next scheduled backup time.

    Args:
        hour: UTC hour to run the backup (0-23).
        minute: UTC minute to run the backup (0-59).
        db_path: Path to the SQLite database.
        backup_dir: Directory to store backups.
        keep: Number of backups to retain.
    """
    logger.info(
        "Backup scheduler started. Daily backup at %02d:%02d UTC. "
        "Database: %s  Backup dir: %s  Keep: %d",
        hour,
        minute,
        db_path,
        backup_dir,
        keep,
    )

    while True:
        wait_seconds = _seconds_until(hour, minute)
        next_run = datetime.now(timezone.utc)
        from datetime import timedelta
        next_run_dt = datetime.now(timezone.utc) + timedelta(seconds=wait_seconds)
        logger.info(
            "Next scheduled backup at %s UTC (in %.0f seconds)",
            next_run_dt.strftime("%Y-%m-%d %H:%M:%S"),
            wait_seconds,
        )

        # Sleep in chunks so the process stays responsive to signals
        _interruptible_sleep(wait_seconds)

        logger.info("Running scheduled backup...")
        run_backup(db_path, backup_dir, keep)


def _interruptible_sleep(seconds: float, chunk: float = 60.0) -> None:
    """Sleep for `seconds` total, waking every `chunk` seconds."""
    remaining = seconds
    while remaining > 0:
        time.sleep(min(chunk, remaining))
        remaining -= chunk


def main() -> int:
    parser = argparse.ArgumentParser(
        description="OpenClaw daily database backup scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--time",
        default="02:00",
        metavar="HH:MM",
        help="UTC time to run the daily backup (default: 02:00)",
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
        "--once",
        action="store_true",
        help="Run one backup immediately and exit (useful for cron jobs)",
    )
    args = parser.parse_args()

    # Parse --time
    try:
        hour_str, minute_str = args.time.split(":")
        hour, minute = int(hour_str), int(minute_str)
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except ValueError:
        logger.error("Invalid --time value '%s'. Expected HH:MM (e.g. 02:00).", args.time)
        return 1

    db_path = Path(args.db)
    backup_dir = Path(args.backup_dir)

    if args.once:
        logger.info("Running one-off backup...")
        success = run_backup(db_path, backup_dir, args.keep)
        return 0 if success else 1

    try:
        run_scheduler(hour, minute, db_path, backup_dir, args.keep)
    except KeyboardInterrupt:
        logger.info("Backup scheduler stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
