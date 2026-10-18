"""
Content Sourcing API (PIPE-001)
================================
API endpoints for Content Sourcing Engine

Endpoints:
- POST /api/content-sourcing/scan - Scan directory for new content
- POST /api/content-sourcing/ingest - Ingest pending content
- GET  /api/content-sourcing/status - Get engine status
- POST /api/content-sourcing/monitor/start - Start monitoring
- POST /api/content-sourcing/monitor/stop - Stop monitoring
- DELETE /api/content-sourcing/discovered - Clear discovered files
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from loguru import logger

from database.connection import get_db
from services.content_sourcing_engine import ContentSourcingEngine, ContentStatus


router = APIRouter(prefix="/api/content-sourcing", tags=["Content Sourcing"])


# ==================== Request/Response Models ====================

class ScanDirectoryRequest(BaseModel):
    """Request model for scanning directory"""
    directory: str = Field(..., description="Directory path to scan")
    recursive: bool = Field(True, description="Scan subdirectories")
    skip_existing: bool = Field(True, description="Skip already discovered files")


class IngestPendingRequest(BaseModel):
    """Request model for ingesting pending content"""
    max_files: Optional[int] = Field(None, description="Maximum files to ingest")
    batch_size: int = Field(10, description="Batch size for commits")


class MonitorStartRequest(BaseModel):
    """Request model for starting monitoring"""
    directories: List[str] = Field(..., description="Directories to monitor")


class ClearDiscoveredRequest(BaseModel):
    """Request model for clearing discovered files"""
    status_filter: Optional[str] = Field(None, description="Filter by status (pending, ingested, failed, duplicate)")


# ==================== Endpoints ====================

@router.post("/scan")
async def scan_directory(
    request: ScanDirectoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scan directory for new media files

    Discovers video and image files in the specified directory,
    computes file hashes for deduplication, and marks new files
    as pending ingestion.

    **Example:**
    ```json
    {
        "directory": "/Volumes/My Passport/MediaPoster/workspace1/iphone_import",
        "recursive": true,
        "skip_existing": true
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "directory": "/path/to/media",
        "discovered": 120,
        "duplicates": 15,
        "errors": 0,
        "total_pending": 120
    }
    ```
    """
    try:
        engine = ContentSourcingEngine(db)

        result = await engine.scan_directory(
            directory=request.directory,
            recursive=request.recursive,
            skip_existing=request.skip_existing
        )

        return result

    except Exception as e:
        logger.error(f"Error scanning directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_pending(
    request: IngestPendingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest pending content files into database

    Takes all pending content files and creates Video records
    for them, making them available for analysis and publishing.

    **Example:**
    ```json
    {
        "max_files": 100,
        "batch_size": 10
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "ingested": 98,
        "failed": 2,
        "total_pending": 0
    }
    ```
    """
    try:
        engine = ContentSourcingEngine(db)

        result = await engine.ingest_pending(
            max_files=request.max_files,
            batch_size=request.batch_size
        )

        return result

    except Exception as e:
        logger.error(f"Error ingesting content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status(db: AsyncSession = Depends(get_db)):
    """
    Get current status of Content Sourcing Engine

    Returns information about discovered files, monitoring status,
    and overall statistics.

    **Response:**
    ```json
    {
        "is_monitoring": false,
        "watch_directories": [],
        "discovered_files": 150,
        "hash_index_size": 8491,
        "status_counts": {
            "pending": 120,
            "ingested": 25,
            "duplicate": 5
        },
        "total_videos_in_db": 8500
    }
    ```
    """
    try:
        engine = ContentSourcingEngine(db)

        # Build hash index if needed
        if not engine.hash_index:
            await engine.build_hash_index()

        status = await engine.get_status()

        return status

    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/start")
async def start_monitoring(
    request: MonitorStartRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Start monitoring directories for new files

    Begins polling the specified directories every 60 seconds
    for new media files. Auto-ingests discovered files.

    **Example:**
    ```json
    {
        "directories": [
            "/Volumes/My Passport/MediaPoster/workspace1/iphone_import",
            "/Users/user/Documents/MediaPoster/uploads"
        ]
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "message": "Monitoring started",
        "directories": ["/path/to/media"]
    }
    ```

    **Note:** This starts a background task. Use `/monitor/stop` to stop it.
    """
    try:
        engine = ContentSourcingEngine(db)

        await engine.start_monitoring(request.directories)

        return {
            "success": True,
            "message": "Monitoring started",
            "directories": request.directories
        }

    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/stop")
async def stop_monitoring(db: AsyncSession = Depends(get_db)):
    """
    Stop monitoring directories

    Stops the background monitoring task.

    **Response:**
    ```json
    {
        "success": true,
        "message": "Monitoring stopped"
    }
    ```
    """
    try:
        engine = ContentSourcingEngine(db)

        await engine.stop_monitoring()

        return {
            "success": True,
            "message": "Monitoring stopped"
        }

    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/discovered")
async def clear_discovered(
    request: ClearDiscoveredRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Clear discovered files from memory

    Clears the in-memory cache of discovered files. Use this to
    reset the engine or free up memory.

    **Example:**
    ```json
    {
        "status_filter": "ingested"
    }
    ```

    **Response:**
    ```json
    {
        "success": true,
        "cleared": 25,
        "message": "Cleared 25 discovered files"
    }
    ```
    """
    try:
        engine = ContentSourcingEngine(db)

        # Convert status string to enum if provided
        status_filter = None
        if request.status_filter:
            try:
                status_filter = ContentStatus(request.status_filter)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {request.status_filter}. "
                           f"Valid statuses: pending, ingesting, ingested, failed, duplicate, skipped"
                )

        count = engine.clear_discovered(status_filter)

        return {
            "success": True,
            "cleared": count,
            "message": f"Cleared {count} discovered files"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing discovered files: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/discovered")
async def list_discovered(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List discovered content files

    Returns list of discovered files with optional filtering by status.

    **Query Parameters:**
    - `status`: Filter by status (pending, ingested, failed, duplicate)
    - `limit`: Maximum files to return (default: 100)
    - `offset`: Pagination offset (default: 0)

    **Response:**
    ```json
    {
        "total": 150,
        "limit": 100,
        "offset": 0,
        "files": [
            {
                "file_path": "/path/to/video.mp4",
                "file_hash": "abc123...",
                "file_size": 15728640,
                "media_type": "video",
                "status": "pending",
                "discovered_at": "2026-01-20T10:00:00Z"
            }
        ]
    }
    ```
    """
    try:
        engine = ContentSourcingEngine(db)

        # Filter by status if specified
        files = list(engine.discovered_files.values())

        if status:
            try:
                status_filter = ContentStatus(status)
                files = [f for f in files if f.status == status_filter]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status: {status}"
                )

        # Apply pagination
        total = len(files)
        files = files[offset:offset+limit]

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "files": [f.to_dict() for f in files]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing discovered files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
