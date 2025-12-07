"""
Video Ingestion Service
Orchestrates all video ingestion methods (iCloud, USB, AirDrop, File Watcher)
"""
import asyncio
from pathlib import Path
from typing import Optional, Callable, List, Dict
from loguru import logger
from concurrent.futures import ThreadPoolExecutor

from .icloud_monitor import iCloudPhotosMonitor
from .file_watcher import VideoFileWatcher, AirDropMonitor
from .image_capture import ImageCaptureImporter
from .video_validator import VideoValidator


class VideoIngestionService:
    """
    Main service that coordinates all video ingestion methods
    Provides unified interface for video detection from iPhone
    """
    
    def __init__(
        self,
        enable_icloud: bool = True,
        enable_usb: bool = True,
        enable_airdrop: bool = True,
        enable_file_watcher: bool = True,
        watch_directories: Optional[List[str]] = None,
        callback: Optional[Callable[[Path, Dict], None]] = None
    ):
        """
        Initialize video ingestion service
        
        Args:
            enable_icloud: Monitor iCloud Photos library
            enable_usb: Monitor for USB iPhone connections
            enable_airdrop: Monitor AirDrop directory
            enable_file_watcher: Watch additional directories
            watch_directories: List of directories to watch
            callback: Function to call when new video is detected (path, metadata)
        """
        self.callback = callback or self._default_callback
        self.validator = VideoValidator()
        
        # Initialize components
        self.icloud_monitor = iCloudPhotosMonitor() if enable_icloud else None
        self.image_capture = ImageCaptureImporter() if enable_usb else None
        self.airdrop_monitor = AirDropMonitor() if enable_airdrop else None
        
        if enable_file_watcher and watch_directories:
            self.file_watcher = VideoFileWatcher(watch_directories)
        else:
            self.file_watcher = None
        
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.running = False
        
        logger.info("Video Ingestion Service initialized")
        logger.info(f"  iCloud: {'✓' if enable_icloud else '✗'}")
        logger.info(f"  USB: {'✓' if enable_usb else '✗'}")
        logger.info(f"  AirDrop: {'✓' if enable_airdrop else '✗'}")
        logger.info(f"  File Watcher: {'✓' if enable_file_watcher else '✗'}")
    
    def _default_callback(self, file_path: Path, metadata: Dict):
        """Default callback that just logs the detection"""
        logger.info(f"✓ New video ingested: {file_path.name}")
        logger.debug(f"  Duration: {metadata.get('duration', 0):.1f}s")
        logger.debug(f"  Size: {metadata.get('file_size_bytes', 0) / (1024*1024):.2f}MB")
        logger.debug(f"  Resolution: {metadata.get('width')}x{metadata.get('height')}")
    
    def process_video(self, file_path: Path, source: str = "unknown"):
        """
        Process a detected video file
        
        Args:
            file_path: Path to video file
            source: Source of the video (icloud, usb, airdrop, file_watcher)
        """
        logger.info(f"Processing video from {source}: {file_path.name}")
        
        # Validate video
        is_valid, error, metadata = self.validator.validate(file_path)
        
        if not is_valid:
            logger.warning(f"Invalid video: {error}")
            return
        
        # Add source to metadata
        metadata['source'] = source
        metadata['ingestion_timestamp'] = logger.opt(colors=True).info().__self__._core.now().isoformat()
        
        # Call user callback
        try:
            self.callback(file_path, metadata)
        except Exception as e:
            logger.error(f"Error in user callback: {e}")
    
    def start_all(self):
        """Start all enabled ingestion methods"""
        if self.running:
            logger.warning("Ingestion service already running")
            return
        
        self.running = True
        logger.info("Starting all ingestion methods...")
        
        # Start iCloud monitoring
        if self.icloud_monitor:
            self.executor.submit(self._run_icloud_monitor)
        
        # Start USB monitoring
        if self.image_capture:
            self.executor.submit(self._run_usb_monitor)
        
        # Start AirDrop monitoring
        if self.airdrop_monitor:
            self.airdrop_monitor.start(lambda p: self.process_video(p, "airdrop"))
        
        # Start file watcher
        if self.file_watcher:
            self.file_watcher.start(lambda p: self.process_video(p, "file_watcher"))
        
        logger.info("✓ All ingestion methods started")
    
    def _run_icloud_monitor(self):
        """Run iCloud monitor in thread"""
        try:
            self.icloud_monitor.watch(lambda p: self.process_video(p, "icloud"))
        except Exception as e:
            logger.error(f"iCloud monitor error: {e}")
    
    def _run_usb_monitor(self):
        """Run USB device monitor in thread"""
        try:
            def usb_callback(files: List[Path]):
                for file_path in files:
                    self.process_video(file_path, "usb")
            
            self.image_capture.watch_for_device_connection(usb_callback)
        except Exception as e:
            logger.error(f"USB monitor error: {e}")
    
    def stop_all(self):
        """Stop all ingestion methods"""
        if not self.running:
            return
        
        logger.info("Stopping all ingestion methods...")
        
        self.running = False
        
        if self.airdrop_monitor:
            self.airdrop_monitor.stop()
        
        if self.file_watcher:
            self.file_watcher.stop()
        
        self.executor.shutdown(wait=False)
        
        logger.info("✓ All ingestion methods stopped")
    
    def scan_existing_videos(self, hours: int = 24):
        """
        Scan for existing videos in all watch locations
        
        Args:
            hours: Look back this many hours
        """
        logger.info(f"Scanning for existing videos (last {hours} hours)...")
        count = 0
        
        # Scan iCloud
        if self.icloud_monitor:
            videos = self.icloud_monitor.get_recent_videos(since_hours=hours)
            for video in videos:
                # Export and process
                exported = self.icloud_monitor.export_video(
                    video['uuid'],
                    Path("/tmp/mediaposter_scan")
                )
                if exported:
                    self.process_video(exported, "icloud")
                    count += 1
        
        # Scan file watcher directories
        if self.file_watcher:
            found = self.file_watcher.scan_existing_files(
                lambda p: self.process_video(p, "file_watcher"),
                max_age_hours=hours
            )
            count += found
        
        logger.info(f"✓ Scan complete: processed {count} videos")
        return count
    
    def get_status(self) -> Dict:
        """Get status of all ingestion methods"""
        status = {
            'running': self.running,
            'icloud': {
                'enabled': self.icloud_monitor is not None,
                'available': self.icloud_monitor.is_photos_library_available() if self.icloud_monitor else False
            },
            'usb': {
                'enabled': self.image_capture is not None,
                'devices_connected': len(self.image_capture.list_connected_devices()) if self.image_capture else 0
            },
            'airdrop': {
                'enabled': self.airdrop_monitor is not None,
                'running': self.airdrop_monitor.is_running() if self.airdrop_monitor else False
            },
            'file_watcher': {
                'enabled': self.file_watcher is not None,
                'running': self.file_watcher.is_running() if self.file_watcher else False
            }
        }
        
        return status
    
    def __enter__(self):
        """Context manager entry"""
        self.start_all()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_all()


# Convenience function for simple usage
def watch_for_videos(
    callback: Callable[[Path, Dict], None],
    enable_all: bool = True,
    watch_dirs: Optional[List[str]] = None
) -> VideoIngestionService:
    """
    Simple function to start watching for videos
    
    Args:
        callback: Function to call with (path, metadata) when video detected
        enable_all: Enable all ingestion methods
        watch_dirs: Additional directories to watch
        
    Returns:
        VideoIngestionService instance
    
    Example:
        def on_video(path, metadata):
            print(f"New video: {path}")
        
        service = watch_for_videos(on_video)
        # Service runs until stopped
    """
    if watch_dirs is None:
        watch_dirs = [
            str(Path.home() / "Desktop"),
            str(Path.home() / "Downloads"),
            str(Path.home() / "Movies")
        ]
    
    service = VideoIngestionService(
        enable_icloud=enable_all,
        enable_usb=enable_all,
        enable_airdrop=enable_all,
        enable_file_watcher=enable_all,
        watch_directories=watch_dirs,
        callback=callback
    )
    
    service.start_all()
    return service
