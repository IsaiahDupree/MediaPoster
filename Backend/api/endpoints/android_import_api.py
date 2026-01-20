"""
Android Import API Endpoints
Import media from Android devices via ADB with duplicate detection.

JOBS-002: Migrated to use BackgroundJobsService for persistent job tracking
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
import os
import json
import hashlib
import subprocess
import asyncio
from loguru import logger

from services.event_bus import EventBus, Topics
from services.background_jobs_service import BackgroundJobsService
from database.connection import get_db

router = APIRouter(prefix="/api/import/android", tags=["Android Import"])

# Storage paths
IMPORT_HISTORY_FILE = Path("/tmp/mediaposter/android_import_history.json")
DEFAULT_IMPORT_PATH = Path.home() / "Documents" / "AndroidImport"
DEFAULT_ADB_PATH = "/opt/homebrew/bin/adb"

# Ensure directories exist
IMPORT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_IMPORT_PATH.mkdir(parents=True, exist_ok=True)

# Import history (kept as file-based for duplicate detection)
_import_history: Dict[str, Dict[str, Any]] = {}


class ImportFilter(BaseModel):
    media_types: List[str] = ["video", "image"]
    min_size_mb: float = 0
    max_size_mb: float = 10000
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    skip_duplicates: bool = True
    auto_analyze: bool = True


class ScanRequest(BaseModel):
    path: str
    filters: ImportFilter
    adb_path: Optional[str] = None


class StartImportRequest(BaseModel):
    path: str
    filters: ImportFilter
    adb_path: Optional[str] = None


def load_import_history() -> Dict[str, Dict[str, Any]]:
    """Load import history from disk"""
    global _import_history
    if IMPORT_HISTORY_FILE.exists():
        try:
            with open(IMPORT_HISTORY_FILE, 'r') as f:
                _import_history = json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load import history: {e}")
            _import_history = {}
    return _import_history


def save_import_history():
    """Save import history to disk"""
    try:
        with open(IMPORT_HISTORY_FILE, 'w') as f:
            json.dump(_import_history, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save import history: {e}")


def get_file_hash(file_path: Path) -> str:
    """Generate a hash for file identification (using size + name + mtime)"""
    stat = file_path.stat()
    hash_input = f"{file_path.name}:{stat.st_size}:{int(stat.st_mtime)}"
    return hashlib.md5(hash_input.encode()).hexdigest()


def is_duplicate(file_path: Path) -> bool:
    """Check if file has already been imported"""
    load_import_history()
    file_hash = get_file_hash(file_path)
    return file_hash in _import_history


def mark_as_imported(file_path: Path, destination: Optional[str] = None):
    """Mark a file as imported"""
    file_hash = get_file_hash(file_path)
    _import_history[file_hash] = {
        "source_path": str(file_path),
        "filename": file_path.name,
        "size_bytes": file_path.stat().st_size,
        "imported_at": datetime.now().isoformat(),
        "destination": destination
    }
    save_import_history()


def get_media_type(file_path: Path) -> Optional[str]:
    """Determine if file is video or image"""
    ext = file_path.suffix.lower()
    video_exts = {'.mp4', '.mov', '.m4v', '.avi', '.mkv', '.webm', '.3gp'}
    image_exts = {'.jpg', '.jpeg', '.png', '.heic', '.heif', '.gif', '.webp', '.tiff', '.bmp'}
    
    if ext in video_exts:
        return 'video'
    elif ext in image_exts:
        return 'image'
    return None


def run_adb_command(args: List[str], adb_path: str = DEFAULT_ADB_PATH) -> tuple:
    """Run an ADB command and return (success, output)"""
    try:
        result = subprocess.run(
            [adb_path] + args,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except FileNotFoundError:
        return False, f"ADB not found at {adb_path}"
    except Exception as e:
        return False, str(e)


@router.get("/device")
async def check_device(adb_path: str = DEFAULT_ADB_PATH):
    """Check if an Android device is connected via ADB"""
    success, output = run_adb_command(["devices"], adb_path)
    
    if not success:
        return {
            "connected": False,
            "error": output,
            "adb_path": adb_path
        }
    
    # Parse device list
    lines = output.strip().split('\n')
    devices = []
    for line in lines[1:]:  # Skip header
        if '\t' in line:
            serial, status = line.split('\t')
            if status == 'device':
                # Get device model
                _, model = run_adb_command(["-s", serial, "shell", "getprop", "ro.product.model"], adb_path)
                devices.append({
                    "serial": serial,
                    "status": status,
                    "model": model or "Unknown"
                })
    
    if devices:
        return {
            "connected": True,
            "name": devices[0].get("model", "Android Device"),
            "serial": devices[0].get("serial", ""),
            "devices": devices
        }
    
    return {"connected": False}


@router.get("/stats")
async def get_import_stats():
    """Get import statistics"""
    load_import_history()
    
    total_size = sum(item.get("size_bytes", 0) for item in _import_history.values())
    videos = sum(1 for item in _import_history.values() if get_media_type(Path(item.get("source_path", ""))) == "video")
    images = sum(1 for item in _import_history.values() if get_media_type(Path(item.get("source_path", ""))) == "image")
    
    last_import = None
    for item in _import_history.values():
        imported_at = item.get("imported_at")
        if imported_at and (not last_import or imported_at > last_import):
            last_import = imported_at
    
    return {
        "total_imports": len(_import_history),
        "total_size_gb": round(total_size / (1024**3), 2),
        "duplicates_skipped": 0,
        "last_import": last_import,
        "videos_imported": videos,
        "images_imported": images
    }


@router.get("/job/current")
async def get_current_job(db: AsyncSession = Depends(get_db)):
    """Get current import job status"""
    # Get the most recent active import job
    service = BackgroundJobsService(db)
    jobs = await service.get_active_jobs(job_type="import")

    # Return the most recent one
    if jobs:
        job = jobs[0]  # Already sorted by created_at DESC
        return {"job": job}

    return {"job": None}


@router.post("/scan")
async def scan_directory(request: ScanRequest):
    """Scan local directory for importable files (after ADB pull)"""
    path = Path(request.path).expanduser()
    
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {path}")
    
    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {path}")
    
    load_import_history()
    filters = request.filters
    files = []
    
    # Scan directory
    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue
        
        media_type = get_media_type(file_path)
        if not media_type:
            continue
        
        if media_type not in filters.media_types:
            continue
        
        stat = file_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        
        if size_mb < filters.min_size_mb or size_mb > filters.max_size_mb:
            continue
        
        is_dup = is_duplicate(file_path)
        will_import = not (filters.skip_duplicates and is_dup)
        
        files.append({
            "path": str(file_path),
            "filename": file_path.name,
            "type": media_type,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_duplicate": is_dup,
            "will_import": will_import
        })
    
    files.sort(key=lambda x: x["modified_at"], reverse=True)
    
    duplicates_count = sum(1 for f in files if f["is_duplicate"])
    to_import_count = sum(1 for f in files if f["will_import"])
    
    logger.info(f"Scanned {path}: {len(files)} files, {duplicates_count} duplicates, {to_import_count} to import")
    
    return {
        "files": files,
        "total_count": len(files),
        "duplicates_count": duplicates_count,
        "to_import_count": to_import_count
    }


@router.post("/pull-from-device")
async def pull_from_device(
    device_path: str = "/sdcard/DCIM",
    local_path: str = str(DEFAULT_IMPORT_PATH),
    adb_path: str = DEFAULT_ADB_PATH
):
    """Pull files from Android device to local directory"""
    local = Path(local_path).expanduser()
    local.mkdir(parents=True, exist_ok=True)
    
    success, output = run_adb_command(["pull", device_path, str(local)], adb_path)
    
    if success:
        return {
            "status": "completed",
            "device_path": device_path,
            "local_path": str(local),
            "output": output
        }
    else:
        raise HTTPException(status_code=500, detail=f"ADB pull failed: {output}")


@router.post("/start")
async def start_import(
    request: StartImportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Start import job (JOBS-002: uses BackgroundJobsService)"""
    # Check if an import is already running
    service = BackgroundJobsService(db)
    active_jobs = await service.get_active_jobs(job_type="import")
    if active_jobs:
        raise HTTPException(status_code=400, detail="Import already in progress")

    path = Path(request.path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {path}")

    # Create job in database
    job_id = await service.create_job(
        job_type="import",
        input_data={
            "source": "android",
            "path": str(path),
            "filters": request.filters.dict(),
            "adb_path": request.adb_path
        }
    )

    # Start the job
    await service.start_job(job_id)

    # Run import in background
    background_tasks.add_task(run_import_job, job_id, path, request.filters)

    # Return job details
    job = await service.get_job(job_id)
    return {"job": job}


async def run_import_job(job_id: str, path: Path, filters: ImportFilter):
    """Background task to run the import (JOBS-002: uses BackgroundJobsService)"""
    # Get database session
    from database.connection import get_db_context

    async with get_db_context() as db:
        service = BackgroundJobsService(db)

        try:
            load_import_history()

            # Scan for files
            files_to_import = []
            skipped_duplicates = 0

            for file_path in path.rglob("*"):
                if not file_path.is_file():
                    continue

                media_type = get_media_type(file_path)
                if not media_type or media_type not in filters.media_types:
                    continue

                stat = file_path.stat()
                size_mb = stat.st_size / (1024 * 1024)

                if size_mb < filters.min_size_mb or size_mb > filters.max_size_mb:
                    continue

                is_dup = is_duplicate(file_path)
                if filters.skip_duplicates and is_dup:
                    skipped_duplicates += 1
                    continue

                files_to_import.append(file_path)

            # Update job with scan results
            await service.update_progress(
                job_id,
                progress=10.0,
                output_data={
                    "total_files": len(files_to_import),
                    "processed_files": 0,
                    "success_count": 0,
                    "failed_count": 0,
                    "skipped_duplicates": skipped_duplicates
                }
            )

            # Emit job started event
            try:
                event_bus = EventBus.get_instance()
                await event_bus.publish(Topics.IMPORT_JOB_STARTED, {
                    "job_id": job_id,
                    "source": "android",
                    "path": str(path),
                    "total_files": len(files_to_import),
                    "duplicates_skipped": skipped_duplicates,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to emit IMPORT_JOB_STARTED event: {e}")

            # Process files - ingest to media-db and mark as imported
            import httpx

            success_count = 0
            failed_count = 0

            async with httpx.AsyncClient(timeout=60.0) as client:
                for i, file_path in enumerate(files_to_import):
                    # Check if job was cancelled
                    job = await service.get_job(job_id)
                    if job and job.get("status") == "cancelled":
                        break

                    try:
                        # Ingest file to media-db (adds to Library)
                        response = await client.post(
                            "http://localhost:5555/api/media-db/ingest/file",
                            params={"file_path": str(file_path)}
                        )

                        if response.status_code == 200:
                            result = response.json()
                            if result.get("status") in ["ingested", "exists"]:
                                mark_as_imported(file_path)
                                success_count += 1
                                logger.info(f"Ingested to library: {file_path.name} ({result.get('status')})")
                            else:
                                failed_count += 1
                                logger.warning(f"Unexpected ingest response for {file_path.name}: {result}")
                        else:
                            failed_count += 1
                            logger.error(f"Failed to ingest {file_path.name}: HTTP {response.status_code}")

                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Failed to import {file_path.name}: {e}")

                    # Update progress
                    processed = i + 1
                    progress = 10.0 + (90.0 * processed / len(files_to_import))
                    await service.update_progress(
                        job_id,
                        progress=min(progress, 99.0),
                        output_data={
                            "total_files": len(files_to_import),
                            "processed_files": processed,
                            "success_count": success_count,
                            "failed_count": failed_count,
                            "skipped_duplicates": skipped_duplicates,
                            "current_file": file_path.name
                        }
                    )
                    await asyncio.sleep(0.05)

            # Mark job as completed
            await service.complete_job(
                job_id,
                output_data={
                    "total_files": len(files_to_import),
                    "processed_files": len(files_to_import),
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "skipped_duplicates": skipped_duplicates,
                    "source": "android",
                    "path": str(path)
                }
            )

            logger.info(f"Import completed: {success_count} success, {failed_count} failed, {skipped_duplicates} duplicates skipped")

            # Emit job completed event
            try:
                event_bus = EventBus.get_instance()
                await event_bus.publish(Topics.IMPORT_JOB_COMPLETED, {
                    "job_id": job_id,
                    "source": "android",
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "duplicates_skipped": skipped_duplicates,
                    "timestamp": datetime.now().isoformat()
                })
            except Exception as e:
                logger.warning(f"Failed to emit IMPORT_JOB_COMPLETED event: {e}")

        except Exception as e:
            logger.error(f"Import job failed: {e}")
            await service.fail_job(job_id, str(e))


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel import job (JOBS-002: uses BackgroundJobsService)"""
    service = BackgroundJobsService(db)
    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    success = await service.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled")

    return {"status": "cancelled", "job_id": job_id}


@router.get("/job/{job_id}")
async def get_job_status(job_id: str, db: AsyncSession = Depends(get_db)):
    """Get job status by ID (JOBS-002)"""
    service = BackgroundJobsService(db)
    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"job": job}


@router.get("/history")
async def get_import_history():
    """Get full import history"""
    load_import_history()
    return {
        "count": len(_import_history),
        "history": list(_import_history.values())[-100:]
    }


@router.delete("/history")
async def clear_import_history():
    """Clear import history (allows re-importing all files)"""
    global _import_history
    _import_history = {}
    save_import_history()
    return {"status": "cleared"}
