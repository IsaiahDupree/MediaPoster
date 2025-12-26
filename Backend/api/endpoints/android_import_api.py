"""
Android Import API Endpoints
Import media from Android devices via ADB with duplicate detection.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import os
import json
import hashlib
import subprocess
import asyncio
from loguru import logger

from services.event_bus import EventBus, Topics

router = APIRouter(prefix="/api/import/android", tags=["Android Import"])

# Storage paths
IMPORT_HISTORY_FILE = Path("/tmp/mediaposter/android_import_history.json")
IMPORT_JOBS_FILE = Path("/tmp/mediaposter/android_import_jobs.json")
DEFAULT_IMPORT_PATH = Path.home() / "Documents" / "AndroidImport"
DEFAULT_ADB_PATH = "/opt/homebrew/bin/adb"

# Ensure directories exist
IMPORT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_IMPORT_PATH.mkdir(parents=True, exist_ok=True)

# In-memory job tracking
_current_job: Optional[Dict[str, Any]] = None
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
async def get_current_job():
    """Get current import job status"""
    return {"job": _current_job}


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
async def start_import(request: StartImportRequest, background_tasks: BackgroundTasks):
    """Start import job"""
    global _current_job
    
    if _current_job and _current_job.get("status") in ["scanning", "importing", "analyzing"]:
        raise HTTPException(status_code=400, detail="Import already in progress")
    
    path = Path(request.path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {path}")
    
    job_id = f"android-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    _current_job = {
        "id": job_id,
        "status": "scanning",
        "total_files": 0,
        "processed_files": 0,
        "success_count": 0,
        "failed_count": 0,
        "skipped_duplicates": 0,
        "current_file": None,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "error_message": None,
        "path": str(path),
        "filters": request.filters.dict()
    }
    
    background_tasks.add_task(run_import_job, path, request.filters)
    
    return {"job": _current_job}


async def run_import_job(path: Path, filters: ImportFilter):
    """Background task to run the import"""
    global _current_job
    
    try:
        load_import_history()
        
        files_to_import = []
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
                _current_job["skipped_duplicates"] += 1
                continue
            
            files_to_import.append(file_path)
        
        _current_job["total_files"] = len(files_to_import)
        _current_job["status"] = "importing"
        
        # Emit job started event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.IMPORT_JOB_STARTED, {
                "job_id": _current_job["id"],
                "source": "android",
                "path": str(path),
                "total_files": len(files_to_import),
                "duplicates_skipped": _current_job["skipped_duplicates"],
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to emit IMPORT_JOB_STARTED event: {e}")
        
        # Process files - ingest to media-db and mark as imported
        import httpx
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            for file_path in files_to_import:
                if _current_job.get("status") == "cancelled":
                    break
                
                while _current_job.get("status") == "paused":
                    await asyncio.sleep(0.5)
                
                _current_job["current_file"] = file_path.name
                
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
                            _current_job["success_count"] += 1
                            logger.info(f"Ingested to library: {file_path.name} ({result.get('status')})")
                        else:
                            _current_job["failed_count"] += 1
                            logger.warning(f"Unexpected ingest response for {file_path.name}: {result}")
                    else:
                        _current_job["failed_count"] += 1
                        logger.error(f"Failed to ingest {file_path.name}: HTTP {response.status_code}")
                        
                except Exception as e:
                    _current_job["failed_count"] += 1
                    logger.error(f"Failed to import {file_path.name}: {e}")
                
                _current_job["processed_files"] += 1
                await asyncio.sleep(0.05)
        
        _current_job["status"] = "completed"
        _current_job["completed_at"] = datetime.now().isoformat()
        _current_job["current_file"] = None
        
        logger.info(f"Import completed: {_current_job['success_count']} success, {_current_job['failed_count']} failed, {_current_job['skipped_duplicates']} duplicates skipped")
        
        # Emit job completed event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.IMPORT_JOB_COMPLETED, {
                "job_id": _current_job["id"],
                "source": "android",
                "success_count": _current_job["success_count"],
                "failed_count": _current_job["failed_count"],
                "duplicates_skipped": _current_job["skipped_duplicates"],
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to emit IMPORT_JOB_COMPLETED event: {e}")
        
    except Exception as e:
        logger.error(f"Import job failed: {e}")
        _current_job["status"] = "failed"
        _current_job["error_message"] = str(e)


@router.post("/job/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause import job"""
    global _current_job
    if not _current_job or _current_job.get("id") != job_id:
        raise HTTPException(status_code=404, detail="Job not found")
    
    _current_job["status"] = "paused"
    return {"status": "paused"}


@router.post("/job/{job_id}/resume")
async def resume_job(job_id: str):
    """Resume import job"""
    global _current_job
    if not _current_job or _current_job.get("id") != job_id:
        raise HTTPException(status_code=404, detail="Job not found")
    
    _current_job["status"] = "importing"
    return {"status": "importing"}


@router.post("/job/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Cancel import job"""
    global _current_job
    if not _current_job or _current_job.get("id") != job_id:
        raise HTTPException(status_code=404, detail="Job not found")
    
    _current_job["status"] = "cancelled"
    return {"status": "cancelled"}


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
