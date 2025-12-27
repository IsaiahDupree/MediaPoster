"""
Video Ingestion API Endpoints
Control and monitor video ingestion
"""
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from pathlib import Path
from loguru import logger

from modules.video_ingestion import VideoIngestionService
from services.event_bus import EventBus, Topics

router = APIRouter()

# Global ingestion service
ingestion_service: Optional[VideoIngestionService] = None


class IngestionConfig(BaseModel):
    enable_icloud: bool = True
    enable_usb: bool = True
    enable_airdrop: bool = True
    enable_file_watcher: bool = True
    watch_directories: Optional[List[str]] = None


class IngestionStatus(BaseModel):
    running: bool
    icloud: dict
    usb: dict
    airdrop: dict
    file_watcher: dict


@router.post("/start")
async def start_ingestion(config: IngestionConfig, background_tasks: BackgroundTasks):
    """Start video ingestion service"""
    global ingestion_service
    
    if ingestion_service and ingestion_service.running:
        return {"message": "Ingestion service already running"}
    
    # Create callback - auto-ingest to media-db when video detected
    async def on_video_detected(path, metadata):
        """Handle newly detected video - automatically ingest to media-db"""
        import httpx
        from datetime import datetime
        
        print(f"[INGESTION] 🔵 CALLBACK TRIGGERED: {path.name}")
        logger.info(f"[INGESTION] 🔵 CALLBACK TRIGGERED: {path.name}")
        
        event_bus = EventBus.get_instance()
        file_name = path.name
        
        # Emit detection event
        print(f"[INGESTION] 📡 Publishing ingestion.detected event for {file_name}")
        logger.info(f"[INGESTION] 📡 Publishing ingestion.detected event for {file_name}")
        try:
            await event_bus.publish("ingestion.detected", {
                "file_name": file_name,
                "file_path": str(path),
                "timestamp": datetime.now().isoformat(),
            })
            print(f"[INGESTION] ✅ Successfully published ingestion.detected")
            logger.info(f"[INGESTION] ✅ Successfully published ingestion.detected")
        except Exception as e:
            print(f"[INGESTION] ❌ Failed to publish ingestion.detected: {e}")
            logger.error(f"[INGESTION] ❌ Failed to publish ingestion.detected: {e}")
        
        logger.info(f"📥 New video detected: {file_name}")
        print(f"[INGESTION] 📥 New video detected: {file_name}")
        
        try:
            # Emit processing event
            print(f"[INGESTION] ⚙️  Publishing ingestion.processing event")
            logger.info(f"[INGESTION] ⚙️  Publishing ingestion.processing event")
            try:
                await event_bus.publish("ingestion.processing", {
                    "file_name": file_name,
                    "file_path": str(path),
                    "timestamp": datetime.now().isoformat(),
                })
                print(f"[INGESTION] ✅ Successfully published ingestion.processing")
                logger.info(f"[INGESTION] ✅ Successfully published ingestion.processing")
            except Exception as e:
                print(f"[INGESTION] ❌ Failed to publish ingestion.processing: {e}")
                logger.error(f"[INGESTION] ❌ Failed to publish ingestion.processing: {e}")
            
            # Auto-ingest using media-db endpoint
            ingest_url = f"http://localhost:5555/api/media-db/ingest/file"
            print(f"[INGESTION] 🌐 Calling ingestion endpoint: {ingest_url}")
            print(f"[INGESTION] 📁 File path: {path}")
            logger.info(f"[INGESTION] 🌐 Calling ingestion endpoint: {ingest_url}")
            logger.info(f"[INGESTION] 📁 File path: {path}")
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                print(f"[INGESTION] ⏳ Sending POST request...")
                logger.info(f"[INGESTION] ⏳ Sending POST request...")
                response = await client.post(
                    ingest_url,
                    params={"file_path": str(path)}
                )
                print(f"[INGESTION] 📥 Response received: {response.status_code}")
                logger.info(f"[INGESTION] 📥 Response received: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    media_id = result.get('media_id')
                    status = result.get('status', 'ingested')
                    
                    if media_id:
                        if status == 'exists':
                            logger.info(f"✅ Video already in database: {media_id}")
                            # Emit already exists event
                            try:
                                await event_bus.publish("ingestion.exists", {
                                    "file_name": file_name,
                                    "media_id": media_id,
                                    "timestamp": datetime.now().isoformat(),
                                })
                            except Exception:
                                pass
                        else:
                            logger.success(f"✅ Auto-ingested video: {media_id}")
                            
                            # Emit success event
                            try:
                                await event_bus.publish("ingestion.completed", {
                                    "file_name": file_name,
                                    "media_id": media_id,
                                    "file_path": str(path),
                                    "source": metadata.get('source', 'file_watcher'),
                                    "timestamp": datetime.now().isoformat(),
                                })
                            except Exception:
                                pass
                            
                            # Emit MEDIA_INGESTED event
                            try:
                                await event_bus.publish(Topics.MEDIA_INGESTED, {
                                    "media_id": media_id,
                                    "file_path": str(path),
                                    "file_name": path.name,
                                    "source": metadata.get('source', 'file_watcher'),
                                    "duration": metadata.get('duration'),
                                })
                                logger.info(f"[PubSub] Emitted MEDIA_INGESTED for {media_id}")
                            except Exception as e:
                                logger.warning(f"[PubSub] Failed to emit ingestion event: {e}")
                    else:
                        logger.error(f"❌ Failed to get media_id from ingestion response")
                        # Emit error event
                        try:
                            await event_bus.publish("ingestion.error", {
                                "file_name": file_name,
                                "error": "Failed to get media_id from response",
                                "timestamp": datetime.now().isoformat(),
                            })
                        except Exception:
                            pass
                else:
                    error_msg = response.text[:200] if hasattr(response, 'text') else "Unknown error"
                    logger.error(f"❌ Auto-ingestion failed ({response.status_code}): {error_msg}")
                    # Emit error event
                    try:
                        await event_bus.publish("ingestion.error", {
                            "file_name": file_name,
                            "error": f"HTTP {response.status_code}: {error_msg}",
                            "timestamp": datetime.now().isoformat(),
                        })
                    except Exception:
                        pass
        except Exception as e:
            logger.error(f"❌ Error auto-ingesting video {path}: {e}", exc_info=True)
            # Emit error event
            try:
                await event_bus.publish("ingestion.error", {
                    "file_name": file_name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception:
                pass
    
    # Create service - default to iPhone import directory (My Passport or local fallback)
    from config.paths import get_iphone_import_dir
    watch_dirs = config.watch_directories or [
        str(get_iphone_import_dir())
    ]
    
    ingestion_service = VideoIngestionService(
        enable_icloud=config.enable_icloud,
        enable_usb=config.enable_usb,
        enable_airdrop=config.enable_airdrop,
        enable_file_watcher=config.enable_file_watcher,
        watch_directories=watch_dirs,
        callback=on_video_detected
    )
    
    # Start in background with auto-sync
    async def start_service_with_sync():
        print(f"[INGESTION_API] 🚀 Starting ingestion service...")
        logger.info(f"[INGESTION_API] 🚀 Starting ingestion service...")
        print(f"[INGESTION_API] 📂 Watch directories: {watch_dirs}")
        logger.info(f"[INGESTION_API] 📂 Watch directories: {watch_dirs}")
        
        # Start watching for new files
        ingestion_service.start_all()
        print(f"[INGESTION_API] ✅ Ingestion service started")
        logger.info(f"[INGESTION_API] ✅ Ingestion service started")
        
        # Trigger auto-sync to ingest any files not yet in DB
        print(f"[INGESTION_API] 🔄 Starting auto-sync of existing files...")
        logger.info(f"[INGESTION_API] 🔄 Starting auto-sync of existing files...")
    
    background_tasks.add_task(start_service_with_sync)
    print(f"[INGESTION_API] 📋 Background task scheduled (with auto-sync)")
    logger.info(f"[INGESTION_API] 📋 Background task scheduled (with auto-sync)")
    
    return {
        "message": "Ingestion service starting",
        "config": config.dict()
    }


@router.post("/stop")
async def stop_ingestion():
    """Stop video ingestion service"""
    global ingestion_service
    
    if not ingestion_service or not ingestion_service.running:
        return {"message": "Ingestion service not running"}
    
    ingestion_service.stop_all()
    
    return {"message": "Ingestion service stopped"}


@router.get("/status", response_model=IngestionStatus)
async def get_ingestion_status():
    """Get ingestion service status"""
    global ingestion_service
    
    if not ingestion_service:
        return IngestionStatus(
            running=False,
            icloud={"enabled": False, "available": False},
            usb={"enabled": False, "devices_connected": 0},
            airdrop={"enabled": False, "running": False},
            file_watcher={"enabled": False, "running": False}
        )
    
    status = ingestion_service.get_status()
    return IngestionStatus(**status)


@router.post("/scan")
async def scan_existing_videos(hours: int = 24):
    """Scan for existing videos in watch directories"""
    global ingestion_service
    
    if not ingestion_service:
        return {"error": "Ingestion service not initialized"}
    
    count = ingestion_service.scan_existing_videos(hours=hours)
    
    return {
        "message": f"Scan complete",
        "videos_found": count,
        "hours_scanned": hours
    }


@router.post("/auto-sync")
async def auto_sync_iphone_import(background_tasks: BackgroundTasks, limit: int = 50):
    """
    Auto-sync: Check all files in IphoneImport and ingest any not already in DB.
    This runs on startup or can be triggered manually.
    """
    from sqlalchemy import create_engine, text
    from config.paths import get_iphone_import_dir
    import os
    
    iphone_import_dir = get_iphone_import_dir()
    
    if not iphone_import_dir.exists():
        return {"error": "Media import directory not found", "path": str(iphone_import_dir)}
    
    # Get all video files
    video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
    all_videos = []
    for f in iphone_import_dir.iterdir():
        if f.is_file() and f.suffix.lower() in video_extensions:
            try:
                if f.stat().st_size > 0:  # Skip empty files
                    all_videos.append(f)
            except Exception:
                continue
    
    logger.info(f"[AUTO-SYNC] Found {len(all_videos)} video files in IphoneImport")
    
    # Check which are already in DB
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
    engine = create_engine(db_url)
    
    existing_paths = set()
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT source_uri FROM videos WHERE source_uri IS NOT NULL"))
            for row in result:
                existing_paths.add(row[0])
    except Exception as e:
        logger.warning(f"[AUTO-SYNC] Could not query DB: {e}")
    
    # Find videos not in DB
    new_videos = [v for v in all_videos if str(v) not in existing_paths]
    
    logger.info(f"[AUTO-SYNC] {len(existing_paths)} already in DB, {len(new_videos)} new to ingest")
    
    # Limit to avoid overwhelming the system
    videos_to_ingest = new_videos[:limit]
    
    async def ingest_batch():
        import httpx
        from datetime import datetime
        
        event_bus = EventBus.get_instance()
        ingested = 0
        skipped = 0
        errors = 0
        
        for video_path in videos_to_ingest:
            try:
                # Emit detection event
                await event_bus.publish("ingestion.detected", {
                    "file_name": video_path.name,
                    "file_path": str(video_path),
                    "timestamp": datetime.now().isoformat(),
                    "source": "auto-sync"
                })
                
                # Call ingest endpoint (file_path is a query parameter)
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        "http://localhost:5555/api/media-db/ingest/file",
                        params={"file_path": str(video_path)}
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("status") == "exists":
                            skipped += 1
                            await event_bus.publish("ingestion.exists", {
                                "file_name": video_path.name,
                                "timestamp": datetime.now().isoformat()
                            })
                        else:
                            ingested += 1
                            await event_bus.publish("ingestion.completed", {
                                "file_name": video_path.name,
                                "media_id": result.get("media_id"),
                                "timestamp": datetime.now().isoformat()
                            })
                    else:
                        errors += 1
                        await event_bus.publish("ingestion.error", {
                            "file_name": video_path.name,
                            "error": f"HTTP {response.status_code}",
                            "timestamp": datetime.now().isoformat()
                        })
                        
            except Exception as e:
                errors += 1
                logger.error(f"[AUTO-SYNC] Error ingesting {video_path.name}: {e}")
        
        logger.info(f"[AUTO-SYNC] Complete: {ingested} ingested, {skipped} already existed, {errors} errors")
    
    background_tasks.add_task(ingest_batch)
    
    return {
        "message": "Auto-sync started",
        "total_videos": len(all_videos),
        "already_in_db": len(existing_paths),
        "new_to_ingest": len(new_videos),
        "ingesting_now": len(videos_to_ingest),
        "limit": limit
    }


@router.get("/iphone-import-stats")
async def get_iphone_import_stats():
    """Get stats about the media import directory (My Passport or local fallback)"""
    from config.paths import get_iphone_import_dir
    iphone_import_dir = get_iphone_import_dir()
    
    if not iphone_import_dir.exists():
        return {
            "exists": False,
            "path": str(iphone_import_dir),
            "error": "IphoneImport directory not found"
        }
    
    # Count video files
    video_extensions = {'.mp4', '.mov', '.m4v', '.avi', '.mkv'}
    video_files = []
    total_size = 0
    
    try:
        for f in iphone_import_dir.iterdir():
            if f.is_file() and f.suffix.lower() in video_extensions:
                video_files.append({
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime
                })
                total_size += f.stat().st_size
    except Exception as e:
        return {
            "exists": True,
            "path": str(iphone_import_dir),
            "error": str(e)
        }
    
    return {
        "exists": True,
        "path": str(iphone_import_dir),
        "video_count": len(video_files),
        "total_size_gb": round(total_size / (1024**3), 2),
        "recent_videos": sorted(video_files, key=lambda x: x["modified"], reverse=True)[:10]
    }
@router.post("/import-iphone")
async def trigger_iphone_import(background_tasks: BackgroundTasks):
    """Trigger iPhone import via Image Capture automation"""
    from import_via_imagecapture import ImageCaptureImporter
    import asyncio
    
    def run_import():
        try:
            importer = ImageCaptureImporter()
            udid = importer.get_device_udid()
            
            if not udid:
                logger.warning("No iPhone detected for import")
                return
                
            logger.info(f"Starting iPhone import for device: {udid}")
            importer.open_image_capture_to_device()
            
            # Watch for a bit to catch immediate imports
            importer.watch_for_imports(duration=60)
            
        except Exception as e:
            logger.error(f"Error during iPhone import: {e}")

    background_tasks.add_task(run_import)
    
    return {"message": "iPhone import sequence started. Check Image Capture on your Mac."}
