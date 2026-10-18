"""
UGC Content Generation API
============================
Generate, manage, and queue offer-aware UGC video scripts.
All endpoints callable from external servers (Safari Automation, dashboard, mobile app).

Prefix: /api/ugc-content
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from services.ugc_content_generator import get_ugc_generator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ugc-content", tags=["UGC Content Generation"])


# =============================================================================
# Request Models
# =============================================================================

class GenerateForOfferRequest(BaseModel):
    """Generate UGC scripts for a specific offer."""
    offer_id: str = Field(..., description="Offer UUID from /api/offers")
    count: int = Field(default=5, ge=1, le=20)
    formats: Optional[List[str]] = Field(None, description="talking_head, sora_ai, broll_overlay")
    trend_descriptions: Optional[List[str]] = Field(None, description="Manual trends to use instead of live fetch")
    platforms: Optional[List[str]] = Field(None, description="Target platforms")
    duration: int = Field(default=30, description="Target duration in seconds (30 or 60)")


class GenerateForAllOffersRequest(BaseModel):
    """Generate UGC scripts for all active offers."""
    count_per_offer: int = Field(default=3, ge=1, le=10)
    formats: Optional[List[str]] = None


class UpdateScriptRequest(BaseModel):
    """Update script fields."""
    title: Optional[str] = None
    hook: Optional[str] = None
    body: Optional[str] = None
    cta: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    sora_prompt: Optional[str] = None
    visual_notes: Optional[str] = None
    status: Optional[str] = None
    target_audience: Optional[str] = None
    awareness_level: Optional[str] = None


class QueueScriptRequest(BaseModel):
    """Queue a script for publishing."""
    platform: str = Field(..., description="Target platform (tiktok, instagram, etc.)")
    account_id: str = Field(..., description="Blotato account ID")
    account_username: str = Field(default="", description="Account username for display")
    video_url: str = Field(..., description="URL/path to the recorded video file")
    scheduled_for: Optional[datetime] = Field(None, description="When to publish (null=next slot)")


class BulkQueueRequest(BaseModel):
    """Queue multiple scripts at once."""
    items: List[Dict[str, Any]]
    # Each item: {script_id, platform, account_id, video_url, scheduled_for?}


# =============================================================================
# Generation Endpoints
# =============================================================================

@router.post("/generate")
async def generate_for_offer(request: GenerateForOfferRequest):
    """
    Generate UGC video scripts for a specific offer.

    Combines:
    - Offer details (title, description, CTA, landing page)
    - Live social media trends
    - @isaiahdupree character definition

    Returns talking-head scripts, Sora AI prompts, and platform-optimized captions.
    """
    gen = get_ugc_generator()
    scripts = await gen.generate_for_offer(
        offer_id=request.offer_id,
        count=request.count,
        formats=request.formats,
        trend_descriptions=request.trend_descriptions,
        platforms=request.platforms,
        duration=request.duration,
    )
    if not scripts:
        raise HTTPException(
            status_code=404,
            detail=f"No scripts generated. Check that offer '{request.offer_id}' exists and is active.",
        )
    return {
        "generated": len(scripts),
        "offer_id": request.offer_id,
        "scripts": [s.to_dict() for s in scripts],
    }


@router.post("/generate/all-offers")
async def generate_for_all_offers(request: GenerateForAllOffersRequest):
    """
    Generate UGC scripts for ALL active offers.

    Iterates through every active offer and generates scripts for each.
    """
    gen = get_ugc_generator()
    results = await gen.generate_for_all_offers(
        count_per_offer=request.count_per_offer,
        formats=request.formats,
    )
    summary = {
        offer_id: len(scripts)
        for offer_id, scripts in results.items()
    }
    total = sum(summary.values())
    return {
        "total_generated": total,
        "offers_processed": len(summary),
        "per_offer": summary,
    }


# =============================================================================
# Script CRUD
# =============================================================================

@router.get("/scripts")
async def list_scripts(
    offer_id: Optional[str] = None,
    status: Optional[str] = None,
    format_type: Optional[str] = None,
    limit: int = 50,
):
    """
    List generated UGC scripts with optional filters.

    Filters:
    - **offer_id**: Filter by offer
    - **status**: generated, approved, queued, published, archived
    - **format_type**: talking_head, sora_ai, broll_overlay
    """
    gen = get_ugc_generator()
    scripts = gen.get_scripts(
        offer_id=offer_id, status=status, format_type=format_type, limit=limit
    )
    return {"scripts": [s.to_dict() for s in scripts], "count": len(scripts)}


@router.get("/scripts/{script_id}")
async def get_script(script_id: str):
    """Get a single UGC script by ID."""
    gen = get_ugc_generator()
    script = gen.get_script_by_id(script_id)
    if not script:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")
    return script.to_dict()


@router.patch("/scripts/{script_id}")
async def update_script(script_id: str, request: UpdateScriptRequest):
    """Update a UGC script's fields (caption, hook, body, status, etc.)."""
    gen = get_ugc_generator()
    kwargs = {k: v for k, v in request.model_dump().items() if v is not None}
    if not kwargs:
        raise HTTPException(status_code=400, detail="No fields to update")
    ok = gen.update_script(script_id, **kwargs)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")
    updated = gen.get_script_by_id(script_id)
    return {"updated": True, "script": updated.to_dict() if updated else None}


@router.patch("/scripts/{script_id}/status")
async def update_script_status(script_id: str, status: str):
    """
    Update script status.

    Valid transitions: generated → approved → queued → published | archived
    """
    valid = {"generated", "approved", "queued", "published", "archived"}
    if status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid}")
    gen = get_ugc_generator()
    ok = gen.update_script_status(script_id, status)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")
    return {"script_id": script_id, "status": status}


@router.delete("/scripts/{script_id}")
async def delete_script(script_id: str):
    """Delete a UGC script."""
    gen = get_ugc_generator()
    ok = gen.delete_script(script_id)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Script '{script_id}' not found")
    return {"deleted": True, "script_id": script_id}


# =============================================================================
# Queue Integration
# =============================================================================

@router.post("/scripts/{script_id}/queue")
async def queue_script(script_id: str, request: QueueScriptRequest):
    """
    Push an approved UGC script into the video publishing queue.

    The script's caption, hashtags, and tracked URL are automatically used.
    You must provide the video_url (the recorded/rendered video file).
    """
    gen = get_ugc_generator()
    result = gen.queue_script_for_publishing(
        script_id=script_id,
        platform=request.platform,
        account_id=request.account_id,
        account_username=request.account_username,
        video_url=request.video_url,
        scheduled_for=request.scheduled_for,
    )
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Script '{script_id}' not found or could not be queued",
        )
    return {"queued": True, "queue_item": result}


@router.post("/scripts/bulk-queue")
async def bulk_queue_scripts(request: BulkQueueRequest):
    """
    Queue multiple scripts for publishing at once.

    Each item needs: script_id, platform, account_id, video_url
    """
    gen = get_ugc_generator()
    results = []
    errors = []
    for item in request.items:
        script_id = item.get("script_id")
        if not script_id:
            errors.append({"error": "Missing script_id", "item": item})
            continue
        result = gen.queue_script_for_publishing(
            script_id=script_id,
            platform=item.get("platform", "tiktok"),
            account_id=item.get("account_id", ""),
            account_username=item.get("account_username", ""),
            video_url=item.get("video_url", ""),
            scheduled_for=item.get("scheduled_for"),
        )
        if result:
            results.append(result)
        else:
            errors.append({"script_id": script_id, "error": "Not found or failed"})

    return {
        "queued": len(results),
        "failed": len(errors),
        "items": results,
        "errors": errors,
    }


# =============================================================================
# Stats + Dashboard
# =============================================================================

@router.get("/stats")
async def get_ugc_stats():
    """
    UGC generation statistics.

    Returns: total scripts, counts by status, offers covered, format types.
    """
    gen = get_ugc_generator()
    return gen.get_stats()


@router.get("/offers")
async def get_offers_for_ugc():
    """
    List all active offers available for UGC generation.

    Convenience endpoint so external servers can discover which offers exist.
    """
    gen = get_ugc_generator()
    offers = gen._load_active_offers()
    return {"offers": offers, "count": len(offers)}
