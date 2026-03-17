"""
Database migration runner for OpenClaw Trading System.

Usage:
    python -m db.migrate
"""

import sqlite3
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import DATABASE_PATH

# Simple logger
class SimpleLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

log = SimpleLogger()


def run_migration(db_path: str, migration_file: Path):
    """Run a single migration file."""
    log.info(f"Running migration: {migration_file.name}")
    
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    conn = sqlite3.connect(db_path)
    try:
        # Use executescript which handles multiple statements
        conn.executescript(sql)
        conn.commit()
        log.info(f"✓ Migration completed: {migration_file.name}")
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        # Ignore "duplicate column" errors (column already exists)
        if "duplicate column" in error_msg:
            log.warning(f"Some columns already exist, continuing: {e}")
            conn.commit()
        else:
            conn.rollback()
            log.error(f"✗ Migration failed: {migration_file.name} - {e}")
            raise
    except Exception as e:
        conn.rollback()
        log.error(f"✗ Migration failed: {migration_file.name} - {e}")
        raise
    finally:
        conn.close()


def run_all_migrations(db_path: str = DATABASE_PATH):
    """Run all pending migrations in order."""
    migrations_dir = Path(__file__).parent / "migrations"
    
    if not migrations_dir.exists():
        log.error(f"Migrations directory not found: {migrations_dir}")
        return
    
    # Get all .sql files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))
    
    if not migration_files:
        log.info("No migrations found")
        return
    
    log.info(f"Found {len(migration_files)} migration(s)")
    
    for migration_file in migration_files:
        run_migration(db_path, migration_file)
    
    log.info("All migrations completed successfully")


if __name__ == "__main__":
    run_all_migrations()
