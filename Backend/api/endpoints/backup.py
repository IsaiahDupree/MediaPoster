"""
Database Backup API Endpoints
==============================
Provides endpoints for creating, listing, and restoring database backups.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from loguru import logger
import os

from scripts.backup_database import (
    create_backup,
    list_backups,
    cleanup_old_backups,
    BACKUP_DIR,
    parse_database_url
)

router = APIRouter(prefix="/api/backup", tags=["Database Backup"])


class BackupRequest(BaseModel):
    reason: Optional[str] = "manual"
    wait: Optional[bool] = False  # Wait for backup to complete (vs async)


class BackupResponse(BaseModel):
    success: bool
    filename: Optional[str] = None
    path: Optional[str] = None
    size_bytes: Optional[int] = None
    size_mb: Optional[float] = None
    timestamp: Optional[str] = None
    reason: Optional[str] = None
    error: Optional[str] = None


@router.post("/create", response_model=BackupResponse)
async def create_database_backup(
    request: BackupRequest = BackupRequest(),
    background_tasks: BackgroundTasks = None
):
    """
    Create a database backup.
    
    Args:
        reason: Reason for backup (e.g., "manual", "pre_analysis", "scheduled")
        wait: If True, wait for backup to complete. If False, run in background.
    
    Returns:
        Backup information or error
    """
    try:
        if request.wait:
            # Synchronous backup - run in thread pool to avoid blocking
            import asyncio
            from concurrent.futures import ThreadPoolExecutor
            
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                result = await loop.run_in_executor(
                    executor,
                    create_backup,
                    request.reason
                )
        else:
            # Asynchronous backup
            def run_backup():
                return create_backup(request.reason)
            
            if background_tasks:
                background_tasks.add_task(run_backup)
            else:
                # If no background tasks, run synchronously
                result = create_backup(request.reason)
                return BackupResponse(**result)
            
            result = {
                "success": True,
                "filename": None,
                "path": None,
                "size_bytes": None,
                "size_mb": None,
                "timestamp": None,
                "reason": request.reason,
                "error": None,
                "message": "Backup started in background"
            }
        
        return BackupResponse(**result)
        
    except Exception as e:
        logger.error(f"Backup endpoint error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def list_database_backups():
    """
    List all available database backups.
    
    Returns:
        List of backup files with metadata
    """
    try:
        backups = list_backups()
        return {
            "backups": backups,
            "count": len(backups),
            "backup_dir": str(BACKUP_DIR)
        }
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{filename}")
async def download_backup(filename: str):
    """
    Download a backup file.
    
    Args:
        filename: Name of the backup file
    
    Returns:
        File download
    """
    # Security: Only allow backup files
    if not filename.startswith("backup_") or not filename.endswith(".sql"):
        raise HTTPException(status_code=400, detail="Invalid backup filename")
    
    backup_path = BACKUP_DIR / filename
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    return FileResponse(
        str(backup_path),
        media_type="application/sql",
        filename=filename,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.delete("/{filename}")
async def delete_backup(filename: str):
    """
    Delete a backup file.
    
    Args:
        filename: Name of the backup file to delete
    """
    # Security: Only allow backup files
    if not filename.startswith("backup_") or not filename.endswith(".sql"):
        raise HTTPException(status_code=400, detail="Invalid backup filename")
    
    backup_path = BACKUP_DIR / filename
    
    if not backup_path.exists():
        raise HTTPException(status_code=404, detail="Backup file not found")
    
    try:
        backup_path.unlink()
        logger.info(f"Deleted backup: {filename}")
        return {"success": True, "message": f"Backup {filename} deleted"}
    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup")
async def cleanup_backups(keep: int = 10):
    """
    Clean up old backups, keeping only the most recent ones.
    
    Args:
        keep: Number of recent backups to keep (default: 10)
    """
    try:
        cleanup_old_backups(keep=keep)
        backups = list_backups()
        return {
            "success": True,
            "message": f"Cleanup complete. {len(backups)} backups remaining.",
            "backups_remaining": len(backups)
        }
    except Exception as e:
        logger.error(f"Error cleaning up backups: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def backup_stats():
    """
    Get backup statistics.
    
    Returns:
        Statistics about backups (total size, count, etc.)
    """
    try:
        backups = list_backups()
        total_size_bytes = sum(b["size_bytes"] for b in backups)
        total_size_mb = total_size_bytes / (1024 * 1024)
        
        return {
            "total_backups": len(backups),
            "total_size_bytes": total_size_bytes,
            "total_size_mb": round(total_size_mb, 2),
            "backup_dir": str(BACKUP_DIR),
            "oldest_backup": backups[-1]["filename"] if backups else None,
            "newest_backup": backups[0]["filename"] if backups else None
        }
    except Exception as e:
        logger.error(f"Error getting backup stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

