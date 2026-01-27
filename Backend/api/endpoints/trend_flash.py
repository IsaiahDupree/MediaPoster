"""
API Endpoints for Trend Flash Video System
Real-time trend detection → video generation pipeline.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
from loguru import logger

router = APIRouter(prefix="/trend-flash", tags=["Trend Flash"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class GenerateRequest(BaseModel):
    """Request to generate content."""
    variant: str = Field(default="educational", description="Script variant: educational, contrarian, meme")


class DetectRequest(BaseModel):
    """Request to run detection."""
    hours_back: int = Field(default=1, description="Hours of data to analyze")


# =============================================================================
# DETECTION ENDPOINTS
# =============================================================================

@router.post("/detect")
async def detect_trends(request: DetectRequest = None):
    """Run trend detection cycle."""
    try:
        from services.trend_flash import get_trend_radar
        
        radar = get_trend_radar()
        hours = request.hours_back if request else 1
        
        clusters = await radar.detect_trends(hours_back=hours)
        
        return {
            "success": True,
            "clusters_found": len(clusters),
            "top_clusters": [c.to_dict() for c in clusters[:5]]
        }
        
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters")
async def get_clusters(
    status: Optional[str] = None,
    min_score: float = 0,
    limit: int = 20
):
    """Get detected trend clusters."""
    try:
        from services.trend_flash import get_trend_radar
        
        radar = get_trend_radar()
        clusters = radar.get_clusters(status=status, min_score=min_score, limit=limit)
        
        return {
            "clusters": [c.to_dict() for c in clusters],
            "count": len(clusters)
        }
        
    except Exception as e:
        logger.error(f"Failed to get clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/{cluster_id}")
async def get_cluster(cluster_id: str):
    """Get a specific cluster."""
    try:
        from services.trend_flash import get_trend_radar
        
        radar = get_trend_radar()
        clusters = radar.get_clusters(limit=100)
        cluster = next((c for c in clusters if c.id == cluster_id), None)
        
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        return cluster.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cluster: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top")
async def get_top_clusters(limit: int = 3):
    """Get top-scored clusters ready for content generation."""
    try:
        from services.trend_flash import get_trend_radar
        
        radar = get_trend_radar()
        clusters = radar.get_top_clusters(limit=limit)
        
        return {
            "clusters": [c.to_dict() for c in clusters],
            "count": len(clusters)
        }
        
    except Exception as e:
        logger.error(f"Failed to get top clusters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GENERATION ENDPOINTS
# =============================================================================

@router.post("/generate/{cluster_id}")
async def generate_content(cluster_id: str, request: GenerateRequest = None):
    """Generate content for a trend cluster."""
    try:
        from services.trend_flash import get_trend_radar, get_flash_generator
        
        radar = get_trend_radar()
        generator = get_flash_generator()
        
        # Get cluster
        clusters = radar.get_clusters(limit=100)
        cluster = next((c for c in clusters if c.id == cluster_id), None)
        
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        variant = request.variant if request else "educational"
        
        # Generate content
        content = await generator.generate_content(cluster, variant=variant)
        
        # Update cluster status
        radar.update_cluster_status(cluster_id, "generating")
        
        return {
            "success": True,
            "content": content.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content")
async def get_content_list(status: Optional[str] = None, limit: int = 20):
    """Get list of generated content."""
    try:
        from services.trend_flash import get_flash_generator
        
        generator = get_flash_generator()
        content_list = generator.get_content_list(status=status, limit=limit)
        
        return {
            "content": [c.to_dict() for c in content_list],
            "count": len(content_list)
        }
        
    except Exception as e:
        logger.error(f"Failed to get content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/content/{content_id}")
async def get_content(content_id: str):
    """Get specific generated content."""
    try:
        from services.trend_flash import get_flash_generator
        
        generator = get_flash_generator()
        content = generator.get_content(content_id)
        
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        return content.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get content: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# PIPELINE ENDPOINTS
# =============================================================================

@router.post("/run")
async def run_full_pipeline(background_tasks: BackgroundTasks):
    """Run full detect → generate pipeline."""
    try:
        from services.trend_flash import get_trend_radar, get_flash_generator
        
        radar = get_trend_radar()
        generator = get_flash_generator()
        
        # Detect trends
        clusters = await radar.detect_trends(hours_back=1)
        
        if not clusters:
            return {
                "success": True,
                "message": "No trends detected",
                "generated": 0
            }
        
        # Get top 3 and generate content
        top_clusters = clusters[:3]
        generated = []
        
        for cluster in top_clusters:
            content = await generator.generate_content(cluster)
            radar.update_cluster_status(cluster.id, "generated")
            generated.append(content.to_dict())
        
        return {
            "success": True,
            "detected": len(clusters),
            "generated": len(generated),
            "content": generated
        }
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get trend flash statistics."""
    try:
        from services.trend_flash import get_trend_radar, get_flash_generator, get_remotion_shipper
        
        radar = get_trend_radar()
        generator = get_flash_generator()
        shipper = get_remotion_shipper()
        
        clusters = radar.get_clusters(limit=100)
        content = generator.get_content_list(limit=100)
        render_stats = shipper.get_stats()
        
        return {
            "total_clusters": len(clusters),
            "clusters_by_status": {
                "detected": len([c for c in clusters if c.status == "detected"]),
                "generating": len([c for c in clusters if c.status == "generating"]),
                "generated": len([c for c in clusters if c.status == "generated"]),
                "shipped": len([c for c in clusters if c.status == "shipped"])
            },
            "total_content": len(content),
            "content_by_status": {
                "pending": len([c for c in content if c.status == "pending"]),
                "ready": len([c for c in content if c.status == "ready"]),
                "posted": len([c for c in content if c.status == "posted"])
            },
            "render_stats": render_stats,
            "avg_trend_score": sum(c.trend_score for c in clusters) / len(clusters) if clusters else 0
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# RENDER ENDPOINTS
# =============================================================================

@router.post("/content/{content_id}/render")
async def render_video(content_id: str):
    """Render a video from generated content."""
    try:
        from services.trend_flash import get_flash_generator, get_remotion_shipper
        
        generator = get_flash_generator()
        shipper = get_remotion_shipper()
        
        content = generator.get_content(content_id)
        if not content:
            raise HTTPException(status_code=404, detail="Content not found")
        
        job = await shipper.render_video(content)
        
        return {
            "success": job.status == "complete",
            "job": job.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Render failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/render/jobs")
async def get_render_jobs():
    """Get all render jobs."""
    try:
        from services.trend_flash import get_remotion_shipper
        
        shipper = get_remotion_shipper()
        
        return {
            "jobs": [j.to_dict() for j in shipper.jobs.values()],
            "stats": shipper.get_stats()
        }
        
    except Exception as e:
        logger.error(f"Failed to get jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/render/jobs/{job_id}")
async def get_render_job(job_id: str):
    """Get a specific render job."""
    try:
        from services.trend_flash import get_remotion_shipper
        
        shipper = get_remotion_shipper()
        job = shipper.get_job(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ship/{cluster_id}")
async def ship_trend(cluster_id: str, variant: str = "educational"):
    """Full pipeline: generate content + render video for a trend."""
    try:
        from services.trend_flash import (
            get_trend_radar, get_flash_generator, get_remotion_shipper
        )
        
        radar = get_trend_radar()
        generator = get_flash_generator()
        shipper = get_remotion_shipper()
        
        # Get cluster
        clusters = radar.get_clusters(limit=100)
        cluster = next((c for c in clusters if c.id == cluster_id), None)
        
        if not cluster:
            raise HTTPException(status_code=404, detail="Cluster not found")
        
        # Generate content
        content = await generator.generate_content(cluster, variant=variant)
        
        # Render video
        job = await shipper.render_video(content)
        
        # Update cluster status
        if job.status == "complete":
            radar.update_cluster_status(cluster_id, "shipped")
        
        return {
            "success": job.status == "complete",
            "content": content.to_dict(),
            "render_job": job.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ship failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
