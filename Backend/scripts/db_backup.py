#!/usr/bin/env python3
"""
Database Backup Script
======================
Backs up MediaPoster PostgreSQL database to external drive.
Runs weekly via launchd or manually.

Backup includes:
- All table data (NOT media files - just metadata)
- Schema structure
- Compressed with gzip

Usage:
    python db_backup.py              # Run backup now
    python db_backup.py --restore    # Restore latest backup
    python db_backup.py --list       # List available backups
    python db_backup.py --cleanup    # Remove backups older than 30 days
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import gzip
import shutil
import argparse

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from config.paths import MY_PASSPORT_BASE, is_external_drive_connected
except ImportError:
    MY_PASSPORT_BASE = Path("/Volumes/My Passport/MediaPoster")
    def is_external_drive_connected():
        return MY_PASSPORT_BASE.exists()

# Configuration
BACKUP_DIR = MY_PASSPORT_BASE / "backups" / "database"
LOCAL_BACKUP_DIR = Path.home() / "Documents" / "MediaPoster_Backups"
DB_CONNECTION = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
RETENTION_DAYS = 30
MAX_BACKUPS = 12  # Keep at least 12 weekly backups (3 months)


def get_backup_dir() -> Path:
    """Get the backup directory, preferring external drive."""
    if is_external_drive_connected():
        backup_dir = BACKUP_DIR
    else:
        backup_dir = LOCAL_BACKUP_DIR
        print(f"⚠️  External drive not connected. Using local backup: {backup_dir}")
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def run_backup() -> bool:
    """
    Run database backup using pg_dump.
    Returns True if successful.
    """
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"mediaposter_db_{timestamp}.sql"
    compressed_file = backup_dir / f"mediaposter_db_{timestamp}.sql.gz"
    
    print(f"🗄️  Starting database backup...")
    print(f"📁 Backup location: {backup_dir}")
    print(f"📅 Timestamp: {timestamp}")
    
    try:
        # Run pg_dump
        print("📤 Dumping database...")
        result = subprocess.run(
            [
                "pg_dump",
                DB_CONNECTION,
                "--no-owner",
                "--no-acl",
                "--clean",
                "--if-exists",
                "-f", str(backup_file)
            ],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            print(f"❌ pg_dump failed: {result.stderr}")
            return False
        
        # Check file was created
        if not backup_file.exists():
            print("❌ Backup file was not created")
            return False
        
        # Get uncompressed size
        uncompressed_size = backup_file.stat().st_size
        print(f"📊 Uncompressed size: {uncompressed_size / 1024 / 1024:.2f} MB")
        
        # Compress with gzip
        print("🗜️  Compressing backup...")
        with open(backup_file, 'rb') as f_in:
            with gzip.open(compressed_file, 'wb', compresslevel=9) as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Remove uncompressed file
        backup_file.unlink()
        
        # Get compressed size
        compressed_size = compressed_file.stat().st_size
        compression_ratio = (1 - compressed_size / uncompressed_size) * 100
        print(f"📊 Compressed size: {compressed_size / 1024 / 1024:.2f} MB ({compression_ratio:.1f}% reduction)")
        
        print(f"✅ Backup complete: {compressed_file.name}")
        
        # Log backup
        log_backup(compressed_file, compressed_size)
        
        return True
        
    except subprocess.TimeoutExpired:
        print("❌ Backup timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False


def log_backup(backup_file: Path, size: int):
    """Log backup to manifest file."""
    manifest_file = backup_file.parent / "backup_manifest.txt"
    
    with open(manifest_file, 'a') as f:
        f.write(f"{datetime.now().isoformat()},{backup_file.name},{size}\n")


def list_backups():
    """List all available backups."""
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("mediaposter_db_*.sql.gz"), reverse=True)
    
    if not backups:
        print("📭 No backups found")
        return
    
    print(f"📦 Available backups in {backup_dir}:\n")
    print(f"{'#':<4} {'Filename':<40} {'Size':<12} {'Date':<20}")
    print("-" * 80)
    
    for i, backup in enumerate(backups, 1):
        size = backup.stat().st_size
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        size_str = f"{size / 1024 / 1024:.2f} MB"
        print(f"{i:<4} {backup.name:<40} {size_str:<12} {mtime.strftime('%Y-%m-%d %H:%M')}")
    
    print(f"\nTotal: {len(backups)} backups")


def restore_backup(backup_file: str = None):
    """
    Restore database from backup.
    
    Args:
        backup_file: Specific backup file name, or None for latest
    """
    backup_dir = get_backup_dir()
    
    if backup_file:
        backup_path = backup_dir / backup_file
    else:
        # Get latest backup
        backups = sorted(backup_dir.glob("mediaposter_db_*.sql.gz"), reverse=True)
        if not backups:
            print("❌ No backups found")
            return False
        backup_path = backups[0]
    
    if not backup_path.exists():
        print(f"❌ Backup file not found: {backup_path}")
        return False
    
    print(f"⚠️  WARNING: This will overwrite the current database!")
    print(f"📁 Restoring from: {backup_path.name}")
    
    confirm = input("Type 'RESTORE' to confirm: ")
    if confirm != "RESTORE":
        print("❌ Restore cancelled")
        return False
    
    try:
        # Decompress to temp file
        print("🗜️  Decompressing backup...")
        temp_file = backup_dir / "restore_temp.sql"
        
        with gzip.open(backup_path, 'rb') as f_in:
            with open(temp_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Restore using psql
        print("📥 Restoring database...")
        result = subprocess.run(
            [
                "psql",
                DB_CONNECTION,
                "-f", str(temp_file)
            ],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        # Clean up temp file
        temp_file.unlink()
        
        if result.returncode != 0:
            print(f"⚠️  psql warnings/errors: {result.stderr}")
        
        print("✅ Database restored successfully")
        return True
        
    except Exception as e:
        print(f"❌ Restore failed: {e}")
        return False


def cleanup_old_backups():
    """Remove backups older than RETENTION_DAYS, keeping at least MAX_BACKUPS."""
    backup_dir = get_backup_dir()
    backups = sorted(backup_dir.glob("mediaposter_db_*.sql.gz"), reverse=True)
    
    if len(backups) <= MAX_BACKUPS:
        print(f"📦 Only {len(backups)} backups exist, keeping all (minimum: {MAX_BACKUPS})")
        return
    
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    removed = 0
    
    for backup in backups[MAX_BACKUPS:]:  # Skip the most recent MAX_BACKUPS
        mtime = datetime.fromtimestamp(backup.stat().st_mtime)
        if mtime < cutoff_date:
            print(f"🗑️  Removing old backup: {backup.name}")
            backup.unlink()
            removed += 1
    
    if removed:
        print(f"✅ Removed {removed} old backups")
    else:
        print("📦 No old backups to remove")


def check_prerequisites() -> bool:
    """Check that required tools are available."""
    try:
        subprocess.run(["pg_dump", "--version"], capture_output=True, check=True)
        subprocess.run(["psql", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ pg_dump and psql are required. Install PostgreSQL client tools.")
        print("   brew install postgresql")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="MediaPoster Database Backup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python db_backup.py              Run backup now
  python db_backup.py --list       List available backups
  python db_backup.py --restore    Restore latest backup
  python db_backup.py --cleanup    Remove old backups
        """
    )
    
    parser.add_argument("--restore", nargs="?", const="latest", 
                        help="Restore from backup (default: latest)")
    parser.add_argument("--list", action="store_true", 
                        help="List available backups")
    parser.add_argument("--cleanup", action="store_true", 
                        help="Remove backups older than 30 days")
    
    args = parser.parse_args()
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    if args.list:
        list_backups()
    elif args.restore:
        backup_file = None if args.restore == "latest" else args.restore
        success = restore_backup(backup_file)
        sys.exit(0 if success else 1)
    elif args.cleanup:
        cleanup_old_backups()
    else:
        # Default: run backup
        success = run_backup()
        if success:
            cleanup_old_backups()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
