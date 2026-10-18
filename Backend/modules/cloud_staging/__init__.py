"""
Cloud Staging Module - Phase 4
Upload and manage clips in cloud storage
"""
from .google_drive import GoogleDriveUploader
from .storage_manager import StorageManager

__all__ = [
    "GoogleDriveUploader",
    "StorageManager",
]
