#!/usr/bin/env python3
"""
Database Backup Script
======================
Creates a backup of the PostgreSQL database before analysis runs.
Saves backups to Backend/backups/ with timestamps.

Usage:
    python scripts/backup_database.py
    
Or via API:
    POST /api/media-db/backup
"""

import os
import subprocess
from datetime import datetime
from pathlib import Path
from loguru import logger

# Backup directory
BACKUP_DIR = Path(__file__).parent.parent / "backups"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Database connection from environment
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


def parse_database_url(url: str) -> dict:
    """Parse DATABASE_URL into components."""
    # postgresql://user:password@host:port/database
    url = url.replace("postgresql://", "").replace("postgres://", "")
    
    # Split user:password from host:port/database
    if "@" in url:
        auth, rest = url.split("@", 1)
        if ":" in auth:
            user, password = auth.split(":", 1)
        else:
            user, password = auth, ""
    else:
        user, password = "postgres", "postgres"
        rest = url
    
    # Split host:port from database
    if "/" in rest:
        host_port, database = rest.split("/", 1)
    else:
        host_port, database = rest, "postgres"
    
    if ":" in host_port:
        host, port = host_port.split(":", 1)
    else:
        host, port = host_port, "5432"
    
    return {
        "user": user,
        "password": password,
        "host": host,
        "port": port,
        "database": database
    }


def create_backup(reason: str = "manual") -> dict:
    """
    Create a database backup using pg_dump.
    
    Args:
        reason: Why the backup is being created (e.g., "pre_analysis", "manual")
    
    Returns:
        dict with backup info or error
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{reason}_{timestamp}.sql"
    backup_path = BACKUP_DIR / backup_filename
    
    db_config = parse_database_url(DATABASE_URL)
    
    logger.info(f"📦 Creating database backup: {backup_filename}")
    logger.info(f"   Database: {db_config['database']}@{db_config['host']}:{db_config['port']}")
    
    try:
        # Set password in environment for pg_dump
        env = os.environ.copy()
        env["PGPASSWORD"] = db_config["password"]
        
        # Find pg_dump - check common locations (prefer newer versions first)
        pg_dump_paths = [
            "pg_dump",  # In PATH
            "/opt/homebrew/Cellar/postgresql@17/17.7/bin/pg_dump",  # Homebrew PostgreSQL 17
            "/opt/homebrew/Cellar/postgresql@16/16.11/bin/pg_dump",  # Homebrew PostgreSQL 16
            "/opt/homebrew/bin/pg_dump",
            "/usr/local/bin/pg_dump",
            "/usr/bin/pg_dump",
        ]
        pg_dump_cmd = None
        for path in pg_dump_paths:
            if path == "pg_dump":
                # Check if in PATH
                import shutil
                if shutil.which("pg_dump"):
                    pg_dump_cmd = "pg_dump"
                    break
            elif os.path.exists(path):
                pg_dump_cmd = path
                break
        
        if not pg_dump_cmd:
            raise FileNotFoundError("pg_dump not found")
        
        # Run pg_dump
        cmd = [
            pg_dump_cmd,
            "-h", db_config["host"],
            "-p", db_config["port"],
            "-U", db_config["user"],
            "-d", db_config["database"],
            "-f", str(backup_path),
            "--no-owner",
            "--no-acl",
        ]
        
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        
        if result.returncode != 0:
            logger.error(f"❌ Backup failed: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr,
                "filename": None
            }
        
        # Get file size
        file_size = backup_path.stat().st_size
        file_size_mb = file_size / (1024 * 1024)
        
        logger.success(f"✅ Backup created: {backup_filename} ({file_size_mb:.2f} MB)")
        
        # Clean up old backups (keep last 10)
        cleanup_old_backups(keep=10)
        
        return {
            "success": True,
            "filename": backup_filename,
            "path": str(backup_path),
            "size_bytes": file_size,
            "size_mb": round(file_size_mb, 2),
            "timestamp": timestamp,
            "reason": reason
        }
        
    except subprocess.TimeoutExpired:
        logger.error("❌ Backup timed out after 5 minutes")
        return {
            "success": False,
            "error": "Backup timed out",
            "filename": None
        }
    except FileNotFoundError:
        logger.error("❌ pg_dump not found. Is PostgreSQL installed?")
        return {
            "success": False,
            "error": "pg_dump not found - PostgreSQL client tools not installed",
            "filename": None
        }
    except Exception as e:
        logger.error(f"❌ Backup error: {e}")
        return {
            "success": False,
            "error": str(e),
            "filename": None
        }


def cleanup_old_backups(keep: int = 10):
    """Remove old backups, keeping the most recent ones."""
    backups = sorted(BACKUP_DIR.glob("backup_*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if len(backups) > keep:
        for old_backup in backups[keep:]:
            logger.info(f"🗑️ Removing old backup: {old_backup.name}")
            old_backup.unlink()


def list_backups() -> list:
    """List all available backups."""
    backups = []
    for backup_file in sorted(BACKUP_DIR.glob("backup_*.sql"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = backup_file.stat()
        backups.append({
            "filename": backup_file.name,
            "path": str(backup_file),
            "size_bytes": stat.st_size,
            "size_mb": round(stat.st_size / (1024 * 1024), 2),
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat()
        })
    return backups


if __name__ == "__main__":
    import sys
    
    reason = sys.argv[1] if len(sys.argv) > 1 else "manual"
    result = create_backup(reason)
    
    if result["success"]:
        print(f"\n✅ Backup created successfully!")
        print(f"   File: {result['filename']}")
        print(f"   Size: {result['size_mb']} MB")
    else:
        print(f"\n❌ Backup failed: {result['error']}")
        sys.exit(1)
