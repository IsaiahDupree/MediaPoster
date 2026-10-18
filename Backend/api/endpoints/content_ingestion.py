"""
Content Ingestion API
=====================
API endpoints for directory ingestion, AI analysis integration, and safe export.

Features:
- BM-001: Directory Ingestion Pipeline
- BM-002: Media Deduplication (via ContentSourcingEngine)
- BM-003: AI Analysis Integration
- BM-004: Safe Export System
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from services.content_sourcing_engine import ContentSourcingEngine
from services.ingestion_analysis_integrator import get_ingestion_analysis_integrator
from services.safe_export_system import get_safe_export_system


router = APIRouter(prefix="/api/content-ingestion", tags=["Content Ingestion"])


class ScanDirectoryRequest(BaseModel):
    """Request to scan a directory for content"""
    directory: str = Field(..., description="Directory path to scan")
    recursive: bool = Field(default=True, description="Scan subdirectories")
    skip_existing: bool = Field(default=True, description="Skip already discovered files")


class IngestRequest(BaseModel):
    """Request to ingest discovered content"""
    auto_analyze: bool = Field(default=True, description="Automatically trigger AI analysis")


class ExportRequest(BaseModel):
    """Request to export analysis data"""
    video_ids: List[str] = Field(..., description="List of video UUIDs to export")
    export_dir: str = Field(..., description="Export directory path")
    include_thumbnails: bool = Field(default=True, description="Include thumbnails")
    include_frames: bool = Field(default=True, description="Include extracted frames")
    use_symlinks: bool = Field(default=True, description="Use symlinks instead of copying")


class VerifyExportRequest(BaseModel):
    """Request to verify an export"""
    manifest_path: str = Field(..., description="Path to export manifest JSON")


@router.post("/scan")
async def scan_directory(
    request: ScanDirectoryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scan directory for media files (BM-001)

    Discovers video and image files, generates file hashes for deduplication,
    and prepares content for ingestion.

    Returns:
        - Discovered files count
        - Duplicates detected
        - Files ready for ingestion
    """
    try:
        logger.info(f"📂 Scanning directory: {request.directory}")

        # Initialize Content Sourcing Engine
        engine = ContentSourcingEngine(db)

        # Scan directory
        result = await engine.scan_directory(
            directory=request.directory,
            recursive=request.recursive,
            skip_existing=request.skip_existing
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error scanning directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest")
async def ingest_pending(
    request: IngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest discovered content (BM-001, BM-002)

    Ingests pending content files into the database with hash-based
    deduplication. Optionally triggers AI analysis integration.

    Returns:
        - Ingested files count
        - Duplicates skipped
        - Analysis triggered (if enabled)
    """
    try:
        logger.info("📥 Starting content ingestion")

        # Initialize Content Sourcing Engine
        engine = ContentSourcingEngine(db)

        # Ingest pending files
        result = await engine.ingest_pending()

        # Start AI analysis integration if requested
        if request.auto_analyze:
            integrator = get_ingestion_analysis_integrator(db)
            if not integrator._is_running:
                await integrator.start()
                logger.info("✓ AI Analysis Integrator started")

        return {
            "success": True,
            "data": result,
            "ai_analysis_enabled": request.auto_analyze
        }

    except Exception as e:
        logger.error(f"Error ingesting content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_ingestion_status(db: AsyncSession = Depends(get_db)):
    """
    Get content ingestion status

    Returns:
        - Pending files count
        - Ingested files count
        - Failed files count
        - AI analysis queue status
    """
    try:
        engine = ContentSourcingEngine(db)

        # Count discovered files by status
        status_counts = {}
        for file in engine.discovered_files.values():
            status = file.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        # Get AI analysis integrator status
        integrator = get_ingestion_analysis_integrator(db)
        ai_status = {
            "running": integrator._is_running,
            "queue_size": integrator._processing_queue.qsize() if integrator._processing_queue else 0
        }

        return {
            "success": True,
            "data": {
                "discovered_files": len(engine.discovered_files),
                "status_counts": status_counts,
                "ai_analysis": ai_status
            }
        }

    except Exception as e:
        logger.error(f"Error getting ingestion status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analysis/start")
async def start_analysis_integration(db: AsyncSession = Depends(get_db)):
    """
    Start AI analysis integration (BM-003)

    Starts the background service that automatically triggers AI analysis
    for newly ingested content.

    Returns:
        - Service status
        - Queue status
    """
    try:
        integrator = get_ingestion_analysis_integrator(db)

        if integrator._is_running:
            return {
                "success": True,
                "message": "AI Analysis Integrator already running",
                "queue_size": integrator._processing_queue.qsize()
            }

        await integrator.start()

        return {
            "success": True,
            "message": "AI Analysis Integrator started",
            "queue_size": 0
        }

    except Exception as e:
        logger.error(f"Error starting analysis integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analysis/stop")
async def stop_analysis_integration(db: AsyncSession = Depends(get_db)):
    """
    Stop AI analysis integration

    Stops the background AI analysis service. Ingestion will continue
    but automatic analysis will pause.

    Returns:
        - Service status
    """
    try:
        integrator = get_ingestion_analysis_integrator(db)

        if not integrator._is_running:
            return {
                "success": True,
                "message": "AI Analysis Integrator not running"
            }

        await integrator.stop()

        return {
            "success": True,
            "message": "AI Analysis Integrator stopped"
        }

    except Exception as e:
        logger.error(f"Error stopping analysis integration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export")
async def export_analysis(
    request: ExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Export analysis data (BM-004)

    Exports analysis data, thumbnails, and file references (not copies)
    for the specified videos. Creates export manifest.

    IMPORTANT: Original media files are NOT copied - only referenced.

    Returns:
        - Export manifest path
        - Files exported counts
        - Export directory path
    """
    try:
        logger.info(f"📦 Exporting analysis for {len(request.video_ids)} videos")

        exporter = get_safe_export_system(db)

        # Export batch
        result = await exporter.export_batch(
            video_ids=request.video_ids,
            export_dir=request.export_dir,
            include_thumbnails=request.include_thumbnails,
            include_frames=request.include_frames,
            use_symlinks=request.use_symlinks
        )

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        logger.error(f"Error exporting analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/export/verify")
async def verify_export(
    request: VerifyExportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify an export (BM-004)

    Verifies that all files referenced in an export manifest exist
    and are accessible.

    Returns:
        - Verification status
        - Missing files (if any)
        - Files verified count
    """
    try:
        logger.info(f"✓ Verifying export: {request.manifest_path}")

        exporter = get_safe_export_system(db)

        # Verify export
        result = await exporter.verify_export(request.manifest_path)

        return {
            "success": result.get("success", False),
            "data": result
        }

    except Exception as e:
        logger.error(f"Error verifying export: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check for content ingestion services

    Returns:
        - Content Sourcing Engine status
        - AI Analysis Integrator status
        - Safe Export System status
    """
    try:
        # Check Content Sourcing Engine
        engine = ContentSourcingEngine(db)
        engine_status = {
            "initialized": True,
            "monitoring": engine._is_monitoring,
            "discovered_files": len(engine.discovered_files)
        }

        # Check AI Analysis Integrator
        integrator = get_ingestion_analysis_integrator(db)
        integrator_status = {
            "initialized": True,
            "running": integrator._is_running,
            "openai_configured": bool(integrator.openai_api_key),
            "queue_size": integrator._processing_queue.qsize() if integrator._processing_queue else 0
        }

        # Check Safe Export System
        exporter = get_safe_export_system(db)
        exporter_status = {
            "initialized": True
        }

        return {
            "success": True,
            "services": {
                "content_sourcing": engine_status,
                "ai_analysis": integrator_status,
                "safe_export": exporter_status
            }
        }

    except Exception as e:
        logger.error(f"Error checking health: {e}")
        raise HTTPException(status_code=500, detail=str(e))
