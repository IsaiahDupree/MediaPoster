"""
iOS Import API Endpoints
Import media from iOS devices with duplicate detection and smart filtering.
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

router = APIRouter(prefix="/api/import/ios", tags=["iOS Import"])

# Storage paths
from config.paths import get_iphone_import_dir
IMPORT_HISTORY_FILE = Path("/tmp/mediaposter/ios_import_history.json")
IMPORT_JOBS_FILE = Path("/tmp/mediaposter/ios_import_jobs.json")
DEFAULT_IMPORT_PATH = get_iphone_import_dir()

# Ensure directories exist
IMPORT_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

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


class StartImportRequest(BaseModel):
    path: str
    filters: ImportFilter


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


@router.get("/device")
async def check_device():
    """
    Check if an iOS device is connected (USB or WiFi sync).
    
    This endpoint performs a fresh check each time it's called - no caching.
    It checks USB first (more reliable for physical disconnection), then Finder.
    """
    logger.debug("🔍 Checking iOS device connection...")
    
    # Method 1: Check via system_profiler for USB connection FIRST
    # This is more reliable for USB connections and updates immediately on disconnection
    # USB check takes priority because it's more accurate for physical disconnection
    try:
        result = subprocess.run(
            ["system_profiler", "SPUSBDataType", "-json"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                usb_data = data.get("SPUSBDataType", [])
                
                # Search through USB tree for iOS devices
                for controller in usb_data:
                    items = controller.get("_items", [])
                    for item in items:
                        name = item.get("_name", "").lower()
                        if "iphone" in name or "ipad" in name or "apple mobile" in name:
                            logger.info(f"✅ Device found via USB: {item.get('_name')}")
                            return {
                                "connected": True,
                                "name": item.get("_name", "iOS Device"),
                                "serial": item.get("serial_num", ""),
                                "product_id": item.get("product_id", ""),
                                "connection_type": "usb"
                            }
                        # Check nested items (devices connected through hubs)
                        nested = item.get("_items", [])
                        for nested_item in nested:
                            nested_name = nested_item.get("_name", "").lower()
                            if "iphone" in nested_name or "ipad" in nested_name or "apple mobile" in nested_name:
                                logger.info(f"✅ Device found via USB (nested): {nested_item.get('_name')}")
                                return {
                                    "connected": True,
                                    "name": nested_item.get("_name", "iOS Device"),
                                    "serial": nested_item.get("serial_num", ""),
                                    "product_id": nested_item.get("product_id", ""),
                                    "connection_type": "usb"
                                }
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse USB data as JSON: {e}")
        else:
            logger.debug("system_profiler returned non-zero exit code")
    except subprocess.TimeoutExpired:
        logger.warning("USB check timed out")
    except Exception as e:
        logger.warning(f"USB check failed: {e}")
    
    # Method 2: Check via Finder/AFC (works for WiFi sync too)
    # Only check Finder if USB check found nothing
    # Note: Finder may show stale mounts after disconnection, so we validate accessibility
    try:
        result = subprocess.run(
            ["osascript", "-e", '''
            tell application "Finder"
                set deviceList to {}
                repeat with d in (get every disk)
                    set diskName to name of d as string
                    if diskName contains "iPhone" or diskName contains "iPad" or diskName contains "iOS" then
                        -- Verify the disk is actually accessible (not stale mount)
                        try
                            set diskPath to POSIX path of d
                            set end of deviceList to diskName
                        end try
                    end if
                end repeat
                return deviceList
            end tell
            '''],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            device_name = result.stdout.strip()
            if device_name:
                # Additional validation: Check if we can actually access the mount point
                # This helps filter out stale mounts that macOS hasn't cleaned up yet
                try:
                    # Try to list contents of the mount (quick check)
                    mount_path = f"/Volumes/{device_name}"
                    if os.path.exists(mount_path):
                        # Try to access the mount point
                        test_result = subprocess.run(
                            ["test", "-d", mount_path],
                            capture_output=True,
                            timeout=2
                        )
                        if test_result.returncode == 0:
                            logger.info(f"✅ Device found via Finder (accessible): {device_name}")
                            return {
                                "connected": True,
                                "name": "Isaiah's iPhone" if "iOS" in device_name else device_name,
                                "serial": device_name,
                                "connection_type": "finder"
                            }
                        else:
                            logger.debug(f"Finder mount exists but is not accessible: {device_name}")
                    else:
                        logger.debug(f"Finder mount path does not exist: {mount_path}")
                except Exception as e:
                    logger.debug(f"Could not validate Finder mount: {e}")
        else:
            logger.debug("No device found via Finder")
    except subprocess.TimeoutExpired:
        logger.warning("Finder check timed out")
    except Exception as e:
        logger.warning(f"Finder check failed: {e}")
    
    # No device found
    logger.debug("❌ No iOS device connected")
    return {"connected": False}


@router.get("/stats")
async def get_import_stats():
    """Get import statistics"""
    load_import_history()
    
    total_size = sum(item.get("size_bytes", 0) for item in _import_history.values())
    videos = sum(1 for item in _import_history.values() if get_media_type(Path(item.get("source_path", ""))) == "video")
    images = sum(1 for item in _import_history.values() if get_media_type(Path(item.get("source_path", ""))) == "image")
    
    # Get last import time
    last_import = None
    for item in _import_history.values():
        imported_at = item.get("imported_at")
        if imported_at and (not last_import or imported_at > last_import):
            last_import = imported_at
    
    return {
        "total_imports": len(_import_history),
        "total_size_gb": round(total_size / (1024**3), 2),
        "duplicates_skipped": 0,  # Would need separate tracking
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
    """Scan directory for importable files"""
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
        
        # Apply media type filter
        if media_type not in filters.media_types:
            continue
        
        # Get file info
        stat = file_path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        
        # Apply size filters
        if size_mb < filters.min_size_mb or size_mb > filters.max_size_mb:
            continue
        
        # Check if duplicate
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
    
    # Sort by modified date (newest first)
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


@router.post("/start")
async def start_import(request: StartImportRequest, background_tasks: BackgroundTasks):
    """Start import job
    
    IMPORTANT: Duplicates are assessed BEFORE import starts in run_import_job.
    The scan endpoint already marks files as duplicates, but we re-check here
    to ensure accuracy (in case files were imported between scan and start).
    """
    global _current_job
    
    if _current_job and _current_job.get("status") in ["scanning", "importing", "analyzing"]:
        raise HTTPException(status_code=400, detail="Import already in progress")
    
    path = Path(request.path).expanduser()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {path}")
    
    # Load import history to ensure we have latest duplicate info
    load_import_history()
    
    # Create job
    job_id = f"ios-import-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
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
    
    # Start background import (duplicates will be assessed in run_import_job)
    background_tasks.add_task(run_import_job, path, request.filters)
    
    return {"job": _current_job}


async def run_import_job(path: Path, filters: ImportFilter):
    """Background task to run the import
    
    IMPORTANT: Duplicates are assessed BEFORE adding files to import list.
    This ensures accurate counts and prevents importing duplicates.
    """
    global _current_job
    
    try:
        # Load import history to get latest duplicate information
        load_import_history()
        logger.info(f"Starting import job with filters: skip_duplicates={filters.skip_duplicates}")
        
        # Scan for files and assess duplicates BEFORE import
        files_to_import = []
        duplicate_count = 0
        
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
            
            # ASSESS DUPLICATES BEFORE IMPORT
            is_dup = is_duplicate(file_path)
            if is_dup:
                duplicate_count += 1
                logger.debug(f"Duplicate detected: {file_path.name} (hash: {get_file_hash(file_path)})")
            
            if filters.skip_duplicates and is_dup:
                _current_job["skipped_duplicates"] += 1
                logger.info(f"Skipping duplicate: {file_path.name}")
                continue
            
            files_to_import.append(file_path)
        
        logger.info(f"Import assessment complete: {len(files_to_import)} files to import, {duplicate_count} duplicates detected")
        
        _current_job["total_files"] = len(files_to_import)
        _current_job["status"] = "importing"
        
        # Emit job started event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.IMPORT_JOB_STARTED, {
                "job_id": _current_job["id"],
                "source": "ios",
                "path": str(path),
                "total_files": len(files_to_import),
                "duplicates_skipped": duplicate_count,
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
                            # Mark as imported to prevent future duplicates
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
                await asyncio.sleep(0.05)  # Small delay to prevent overwhelming
        
        _current_job["status"] = "completed"
        _current_job["completed_at"] = datetime.now().isoformat()
        _current_job["current_file"] = None
        
        logger.info(f"Import completed: {_current_job['success_count']} success, {_current_job['failed_count']} failed, {_current_job['skipped_duplicates']} duplicates skipped")
        
        # Emit job completed event
        try:
            event_bus = EventBus.get_instance()
            await event_bus.publish(Topics.IMPORT_JOB_COMPLETED, {
                "job_id": _current_job["id"],
                "source": "ios",
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


@router.post("/open-image-capture")
async def open_image_capture():
    """Open macOS Image Capture app"""
    try:
        subprocess.Popen(["open", "-a", "Image Capture"])
        return {"status": "opened"}
    except Exception as e:
        logger.error(f"Failed to open Image Capture: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transfer-files-direct")
async def transfer_files_direct(
    background_tasks: BackgroundTasks,
    media_types: Optional[List[str]] = None,
    max_files: Optional[int] = None
):
    """
    Direct file transfer from iPhone using pymobiledevice3.
    
    Uses AFC (Apple File Conduit) to access files directly without Image Capture.
    Includes duplicate detection via fingerprinting.
    
    Args:
        media_types: List of media types to transfer (default: ["video", "image"])
        max_files: Maximum number of files to transfer (None = all)
    
    Returns:
        Transfer result with imported/skipped counts
    """
    try:
        from services.iphone_direct_import import iPhoneDirectImporter, PYMOBILEDEVICE3_AVAILABLE
        
        if not PYMOBILEDEVICE3_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="pymobiledevice3 not available. Install with: pip install pymobiledevice3"
            )
        
        if media_types is None:
            media_types = ["video", "image"]
        
        import_dir = DEFAULT_IMPORT_PATH
        importer = iPhoneDirectImporter(import_dir)
        
        # Connect to device
        if not importer.connect():
            raise HTTPException(
                status_code=400,
                detail="Failed to connect to iPhone. Make sure it's unlocked and 'Trust This Computer' is accepted."
            )
        
        try:
            # Import files
            result = importer.import_files(
                media_types=media_types,
                max_files=max_files
            )
            
            return {
                "status": "success",
                "imported": result["imported"],
                "skipped": result["skipped"],
                "errors": result.get("errors", 0),
                "total_found": result.get("total_found", 0),
                "destination": str(import_dir)
            }
        finally:
            importer.disconnect()
            
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="pymobiledevice3 not available. Install with: pip install pymobiledevice3"
        )
    except Exception as e:
        logger.error(f"Direct transfer error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transfer error: {str(e)}")


@router.post("/transfer-files")
async def transfer_files_from_device(
    background_tasks: BackgroundTasks,
    media_types: Optional[List[str]] = None,
    delete_after_transfer: bool = False
):
    """
    Automatically transfer files from connected iPhone to import folder.
    
    Uses AppleScript to control Image Capture for automated file transfer.
    After transfer, applies fingerprinting to detect and skip duplicates.
    
    Args:
        media_types: List of media types to transfer (default: ["video", "image"])
        delete_after_transfer: Whether to delete files from iPhone after successful transfer
    
    Returns:
        Transfer job information with duplicate detection results
    """
    if media_types is None:
        media_types = ["video", "image"]
    
    # Check if device is connected
    device_check = await check_device()
    if not device_check.get("connected"):
        raise HTTPException(
            status_code=400,
            detail="No iOS device connected. Please connect your iPhone via USB."
        )
    
    import_dir = DEFAULT_IMPORT_PATH
    import_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"📱 Starting automated file transfer from iPhone to {import_dir}")
    logger.info(f"   Media types: {media_types}")
    logger.info(f"   Delete after transfer: {delete_after_transfer}")
    
    # Use AppleScript to automate Image Capture
    # Build media type checks for AppleScript
    include_video = "video" in media_types
    include_image = "image" in media_types
    
    script = f'''
    tell application "Image Capture"
        activate
        
        set deviceList to devices
        if (count of deviceList) is 0 then
            return "ERROR: No devices connected"
        end if
        
        set targetDevice to item 1 of deviceList
        set allItems to items of targetDevice
        set itemsToTransfer to {{}}
        
        repeat with anItem in allItems
            set itemType to type of anItem
            if itemType is "video" and {str(include_video).lower()} then
                set end of itemsToTransfer to anItem
            else if itemType is "image" and {str(include_image).lower()} then
                set end of itemsToTransfer to anItem
            end if
        end repeat
        
        if (count of itemsToTransfer) is 0 then
            return "ERROR: No matching files found"
        end if
        
        -- Download files
        download itemsToTransfer to POSIX file "{import_dir}"
        
        -- Delete from device if requested
        if {str(delete_after_transfer).lower()} then
            repeat with anItem in itemsToTransfer
                delete anItem
            end repeat
        end if
        
        return "SUCCESS: Transferred " & (count of itemsToTransfer) & " files"
    end tell
    '''
    
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout for large transfers
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            if "ERROR" in output:
                logger.error(f"Transfer failed: {output}")
                raise HTTPException(status_code=500, detail=output)
            
            # After transfer, apply duplicate detection via fingerprinting
            from services.iphone_direct_import import iPhoneDirectImporter
            import time
            
            # Get list of files before transfer (for comparison)
            files_before = set(import_dir.rglob("*"))
            files_before = {f for f in files_before if f.is_file()}
            
            # Wait a moment for Image Capture to finish writing
            time.sleep(2)
            
            # Build index of existing files (for duplicate detection)
            importer = iPhoneDirectImporter(import_dir)
            existing_index = importer.load_index()
            if not existing_index:
                existing_index = importer.build_index_from_destination()
            
            # Find newly transferred files and check for duplicates
            files_after = set(import_dir.rglob("*"))
            files_after = {f for f in files_after if f.is_file()}
            newly_transferred_files = files_after - files_before
            
            newly_transferred = []
            duplicates_removed = 0
            
            for file_path in newly_transferred_files:
                if file_path.suffix.lower() in {".mov", ".mp4", ".m4v", ".jpg", ".jpeg", ".png", ".heic"}:
                    try:
                        fp = importer.fingerprint(file_path)
                        if fp in existing_index:
                            # Duplicate found - remove it
                            logger.info(f"Removing duplicate: {file_path.name}")
                            file_path.unlink()
                            duplicates_removed += 1
                        else:
                            # New file - add to index and manifest
                            existing_index[fp] = str(file_path)
                            newly_transferred.append(file_path)
                            
                            # Log to manifest
                            manifest_entry = {
                                "src": f"iPhone/{file_path.name}",
                                "dst": str(file_path),
                                "fp": fp,
                                "size": file_path.stat().st_size,
                                "imported_at": datetime.now().isoformat()
                            }
                            manifest_file = import_dir / ".import_manifest.jsonl"
                            manifest_file.parent.mkdir(parents=True, exist_ok=True)
                            with open(manifest_file, 'a', encoding='utf-8') as f:
                                f.write(json.dumps(manifest_entry) + '\n')
                    except Exception as e:
                        logger.warning(f"Error processing {file_path}: {e}")
            
            # Save updated index
            importer.save_index(existing_index)
            
            transferred_count = len(newly_transferred)
            
            logger.info(f"✅ Transfer complete: {transferred_count} new files, {duplicates_removed} duplicates removed")
            
            return {
                "status": "success",
                "message": output,
                "destination": str(import_dir),
                "transferred_count": transferred_count,
                "duplicates_removed": duplicates_removed,
                "delete_after_transfer": delete_after_transfer
            }
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.error(f"Transfer failed: {error_msg}")
            raise HTTPException(status_code=500, detail=f"Transfer failed: {error_msg}")
            
    except subprocess.TimeoutExpired:
        logger.error("Transfer timed out")
        raise HTTPException(status_code=500, detail="Transfer timed out (max 10 minutes)")
    except Exception as e:
        logger.error(f"Transfer error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Transfer error: {str(e)}")


@router.get("/history")
async def get_import_history():
    """Get full import history"""
    load_import_history()
    return {
        "count": len(_import_history),
        "history": list(_import_history.values())[-100:]  # Last 100 entries
    }


@router.delete("/history")
async def clear_import_history():
    """Clear import history (allows re-importing all files)"""
    global _import_history
    _import_history = {}
    save_import_history()
    return {"status": "cleared"}
