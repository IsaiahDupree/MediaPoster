"""
Video Ingestion Module
Handles automatic syncing of videos from iPhone to Mac
Supports: iCloud Photos, Image Capture, AirDrop, File System watching
"""
from .icloud_monitor import iCloudPhotosMonitor
from .file_watcher import VideoFileWatcher
from .image_capture import ImageCaptureImporter
from .video_validator import VideoValidator
from .ingestion_service import VideoIngestionService

__all__ = [
    "iCloudPhotosMonitor",
    "VideoFileWatcher",
    "ImageCaptureImporter",
    "VideoValidator",
    "VideoIngestionService",
]
