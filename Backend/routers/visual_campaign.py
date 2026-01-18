"""
Visual Campaign API Endpoints
Instagram Carousels & TikTok Picture Videos
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from services.visual_campaign_service import get_visual_campaign_service, ContentFormat
from services.visual_remotion_renderer import get_visual_renderer
from services.visual_poster_service import get_visual_poster_service

router = APIRouter(prefix="/api/visual-campaign", tags=["Visual Campaign"])


# =============================================================================
# MODELS
# =============================================================================

class GenerateContentRequest(BaseModel):
    product_slug: Optional[str] = None
    format: str = "instagram_carousel"  # instagram_carousel, tiktok_picture_video
    count: int = 5


class ScheduleContentRequest(BaseModel):
    content_items: List[dict]
    platform: str  # instagram, tiktok
    start_time: Optional[str] = None
    interval_minutes: int = 90


# =============================================================================
# CAMPAIGN ENDPOINTS
# =============================================================================

@router.post("/generate")
async def generate_content(request: GenerateContentRequest):
    """Generate visual content for one or all products."""
    service = get_visual_campaign_service()
    
    content_format = ContentFormat.INSTAGRAM_CAROUSEL if request.format == 'instagram_carousel' else ContentFormat.TIKTOK_PICTURE_VIDEO
    
    if request.product_slug:
        products = [p for p in service.get_products() if p.slug == request.product_slug]
        if not products:
            raise HTTPException(status_code=404, detail=f"Product not found: {request.product_slug}")
    else:
        products = service.get_products()
    
    all_content = []
    for product in products:
        if content_format == ContentFormat.INSTAGRAM_CAROUSEL:
            content = service.generate_batch_carousels(product, count=request.count // len(products))
        else:
            content = service.generate_batch_picture_videos(product, count=request.count // len(products))
        all_content.extend(content)
    
    return {
        "generated": len(all_content),
        "format": request.format,
        "content": all_content
    }


@router.post("/schedule")
async def schedule_content(request: ScheduleContentRequest):
    """Schedule visual content for posting."""
    service = get_visual_campaign_service()
    
    start_time = None
    if request.start_time:
        start_time = datetime.fromisoformat(request.start_time)
    
    scheduled_ids = service.schedule_content(
        content_items=request.content_items,
        platform=request.platform,
        start_time=start_time,
        interval_minutes=request.interval_minutes
    )
    
    return {
        "scheduled": len(scheduled_ids),
        "platform": request.platform,
        "ids": scheduled_ids
    }


@router.post("/run-daily")
async def run_daily_campaign():
    """Run daily visual content generation and scheduling."""
    service = get_visual_campaign_service()
    result = await service.run_daily_visual_campaign()
    return {"status": "completed", "result": result}


@router.post("/render-pending")
async def render_pending_content():
    """Render all pending visual content."""
    renderer = get_visual_renderer()
    result = await renderer.render_pending_content()
    return result


@router.post("/post-due")
async def post_due_content():
    """Post all content that's due for posting."""
    poster = get_visual_poster_service()
    result = await poster.process_due_content()
    return result


@router.post("/post/{content_id}")
async def post_content(content_id: str):
    """Post a specific scheduled content item."""
    poster = get_visual_poster_service()
    result = await poster.post_scheduled_content(content_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.get("/stats")
async def get_posting_stats(days: int = 7):
    """Get posting statistics."""
    poster = get_visual_poster_service()
    return poster.get_posting_stats(days=days)


# =============================================================================
# TEMPLATE ENDPOINTS
# =============================================================================

@router.get("/templates")
async def get_templates(format: Optional[str] = None):
    """Get visual content templates."""
    service = get_visual_campaign_service()
    
    templates = []
    formats = [ContentFormat.INSTAGRAM_CAROUSEL, ContentFormat.TIKTOK_PICTURE_VIDEO]
    
    if format:
        formats = [ContentFormat(format)]
    
    for fmt in formats:
        fmt_templates = service.get_templates(fmt)
        for t in fmt_templates:
            templates.append({
                "id": t.id,
                "name": t.name,
                "format": t.format.value,
                "template_type": t.template_type,
                "slide_count": t.slide_count,
                "animation_preset": t.animation_preset,
                "music_mood": t.music_mood
            })
    
    return {"templates": templates}


# =============================================================================
# ANALYTICS ENDPOINTS
# =============================================================================

@router.get("/analytics/scheduled")
async def get_scheduled_content(platform: Optional[str] = None, limit: int = 50):
    """Get scheduled visual content."""
    from sqlalchemy import create_engine, text
    import os
    
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"))
    
    query = """
        SELECT svc.id, svc.title, svc.format, svc.awareness_stage, svc.content_type,
               svc.scheduled_time, svc.platform, svc.status, svc.render_status,
               cp.name as product_name
        FROM scheduled_visual_content svc
        JOIN campaign_products cp ON svc.product_id = cp.id
        WHERE svc.status IN ('pending', 'scheduled', 'rendering')
    """
    
    params = {"limit": limit}
    if platform:
        query += " AND svc.platform = :platform"
        params["platform"] = platform
    
    query += " ORDER BY svc.scheduled_time ASC LIMIT :limit"
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        
        items = []
        for row in result.fetchall():
            items.append({
                "id": str(row[0]),
                "title": row[1],
                "format": row[2],
                "awareness_stage": row[3],
                "content_type": row[4],
                "scheduled_time": str(row[5]) if row[5] else None,
                "platform": row[6],
                "status": row[7],
                "render_status": row[8],
                "product_name": row[9]
            })
    
    return {"scheduled_content": items, "count": len(items)}


@router.get("/analytics/posted")
async def get_posted_content(platform: Optional[str] = None, days: int = 7, limit: int = 50):
    """Get posted visual content with analytics."""
    from sqlalchemy import create_engine, text
    import os
    
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres"))
    
    query = """
        SELECT pvc.id, pvc.title, pvc.format, pvc.awareness_stage, pvc.content_type,
               pvc.platform, pvc.platform_url, pvc.posted_at,
               pvc.impressions, pvc.likes, pvc.comments, pvc.shares, pvc.saves,
               pvc.engagement_rate, cp.name as product_name
        FROM posted_visual_content pvc
        JOIN campaign_products cp ON pvc.product_id = cp.id
        WHERE pvc.posted_at > NOW() - INTERVAL ':days days'
    """
    
    params = {"days": days, "limit": limit}
    if platform:
        query += " AND pvc.platform = :platform"
        params["platform"] = platform
    
    query += " ORDER BY pvc.posted_at DESC LIMIT :limit"
    
    with engine.connect() as conn:
        result = conn.execute(text(query), params)
        
        items = []
        for row in result.fetchall():
            items.append({
                "id": str(row[0]),
                "title": row[1],
                "format": row[2],
                "awareness_stage": row[3],
                "content_type": row[4],
                "platform": row[5],
                "platform_url": row[6],
                "posted_at": str(row[7]) if row[7] else None,
                "impressions": row[8] or 0,
                "likes": row[9] or 0,
                "comments": row[10] or 0,
                "shares": row[11] or 0,
                "saves": row[12] or 0,
                "engagement_rate": row[13] or 0,
                "product_name": row[14]
            })
    
    return {"posted_content": items, "count": len(items)}
