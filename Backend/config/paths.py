"""
Path Configuration
==================
Centralized path configuration for MediaPoster.
Update paths here when storage locations change.
"""

from pathlib import Path
import os

# =============================================================================
# MY PASSPORT EXTERNAL DRIVE PATHS
# =============================================================================

# Base path for MediaPoster data on external drive
MY_PASSPORT_BASE = Path("/Volumes/My Passport/MediaPoster")

# Workspace paths (multi-user support)
WORKSPACE1_DIR = MY_PASSPORT_BASE / "workspace1"

# iPhone import - PRIMARY SOURCE for user media
# Old: ~/Documents/IphoneImport
# New: /Volumes/My Passport/MediaPoster/workspace1/iphone_import
IPHONE_IMPORT_DIR = WORKSPACE1_DIR / "iphone_import"

# Android import (future)
ANDROID_IMPORT_DIR = WORKSPACE1_DIR / "android_import"

# RapidAPI downloaded media (Instagram, TikTok, etc.)
RAPIDAPI_MEDIA_DIR = MY_PASSPORT_BASE / "rapidapi_media"

# =============================================================================
# FALLBACK PATHS (when external drive not connected)
# =============================================================================

LOCAL_IPHONE_IMPORT = Path.home() / "Documents" / "IphoneImport"

def get_iphone_import_dir() -> Path:
    """
    Get the active iPhone import directory.
    Prefers My Passport if mounted, falls back to local.
    """
    if IPHONE_IMPORT_DIR.exists():
        return IPHONE_IMPORT_DIR
    elif LOCAL_IPHONE_IMPORT.exists():
        return LOCAL_IPHONE_IMPORT
    else:
        # Return the preferred path even if it doesn't exist
        return IPHONE_IMPORT_DIR

def get_rapidapi_media_dir() -> Path:
    """Get the RapidAPI media directory."""
    RAPIDAPI_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    return RAPIDAPI_MEDIA_DIR

def is_external_drive_connected() -> bool:
    """Check if My Passport drive is connected."""
    return MY_PASSPORT_BASE.exists()

# =============================================================================
# EXPORT FOR BACKWARDS COMPATIBILITY
# =============================================================================

# These are the paths that should be imported by other modules
__all__ = [
    'MY_PASSPORT_BASE',
    'WORKSPACE1_DIR', 
    'IPHONE_IMPORT_DIR',
    'ANDROID_IMPORT_DIR',
    'RAPIDAPI_MEDIA_DIR',
    'LOCAL_IPHONE_IMPORT',
    'get_iphone_import_dir',
    'get_rapidapi_media_dir',
    'is_external_drive_connected',
]
