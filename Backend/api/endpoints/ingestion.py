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
    
    # Create callback
    async def on_video_detected(path, metadata):
        """Handle newly detected video"""
        from database.connection import async_session_maker
        from database.models import OriginalVideo
        
        logger.info(f"New video detected: {path}")
        
        # Save to database
        if async_session_maker:
            async with async_session_maker() as session:
                video = OriginalVideo(
                    file_path=str(path),
                    file_name=path.name,
                    file_size_bytes=metadata['file_size_bytes'],
                    duration_seconds=metadata['duration'],
                    source=metadata['source'],
                    processing_status="pending",
                    analysis_data=metadata
                )
                
                session.add(video)
                await session.commit()
                
                logger.success(f"Video saved to database: {video.video_id}")
    
    # Create service
    watch_dirs = config.watch_directories or [
        str(Path.home() / "Desktop"),
        str(Path.home() / "Downloads"),
        str(Path.home() / "Movies")
    ]
    
    ingestion_service = VideoIngestionService(
        enable_icloud=config.enable_icloud,
        enable_usb=config.enable_usb,
        enable_airdrop=config.enable_airdrop,
        enable_file_watcher=config.enable_file_watcher,
        watch_directories=watch_dirs,
        callback=on_video_detected
    )
    
    # Start in background
    def start_service():
        ingestion_service.start_all()
    
    background_tasks.add_task(start_service)
    
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
