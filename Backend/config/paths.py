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
IPHONE_SOURCE_ARCHIVE_DIR = MY_PASSPORT_BASE.parent / "iPhone" / "MediaPosterSources"

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


def resolve_iphone_source(path: Path) -> Path:
    """Resolve an exact Passport import path from a source receipt."""
    from config.source_receipts import import_replacements

    if path.parent != IPHONE_IMPORT_DIR:
        return path
    return import_replacements(IPHONE_IMPORT_DIR, path.name).get(path, path)


def list_iphone_import_files() -> list[Path]:
    """List unique import paths, including retained sources from receipts."""
    from config.source_receipts import archived_import_sources, import_replacements

    directory = get_iphone_import_dir()
    replacements = import_replacements(IPHONE_IMPORT_DIR)
    paths = set(replacements.values())
    paths.update(archived_import_sources(IPHONE_SOURCE_ARCHIVE_DIR))
    if directory.is_dir():
        paths.update(replacements.get(path, path) for path in directory.iterdir() if path.is_file())
    return sorted(paths)

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
