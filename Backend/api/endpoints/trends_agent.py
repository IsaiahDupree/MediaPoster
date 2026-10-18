"""
Trends Agent API Endpoints
===========================
Endpoints for the Trends Agent service.

API surface:
- GET /trends - List detected trends
- GET /trends/{trend_id} - Get single trend detail
- POST /trends/detect - Trigger trend detection
- POST /trends/brief - Generate content brief from trend
- GET /trends/daily-digest - Get daily trend digest
- POST /trends/webhooks - Register for trend alerts
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import json

from services.trends_agent import (
    get_trends_agent,
    TrendV1,
    TrendStage,
    ClusterType,
)

router = APIRouter(prefix="/api/trends-agent", tags=["Trends Agent"])


# =============================================================================
# MODELS
# =============================================================================

class TrendQuery(BaseModel):
    """Query parameters for trend search"""
    platform: str = "all"
    niche: str = "general"
    window_hours: int = 24
    min_velocity: float = 5
    stage: Optional[str] = None  # emerging, rising, peak, declining
    cluster_type: Optional[str] = None  # phrase, format, sound, topic


class BriefRequest(BaseModel):
    """Request for generating a content brief from a trend"""
    trend_id: Optional[str] = None
    trend_name: Optional[str] = None
    niche: str = "general"
    brand_voice: str = "engaging"  # engaging, professional, casual, funny
    platform: str = "tiktok"
    platform_constraints: Dict[str, Any] = Field(default_factory=dict)


class WebhookConfig(BaseModel):
    """Webhook configuration for trend alerts"""
    url: str
    event_types: List[str] = ["emerging", "rising"]
    min_score: float = 50
    niches: List[str] = ["general"]
    platforms: List[str] = ["tiktok", "instagram"]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/trends")
async def list_trends(
    platform: str = Query("all", description="Platform filter"),
    niche: str = Query("general", description="Niche/category filter"),
    window: str = Query("24h", description="Time window (1h, 6h, 24h, 7d)"),
    stage: Optional[str] = Query(None, description="Trend stage filter"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get detected trends with optional filtering.
    
    Returns trends sorted by velocity/relevance.
    """
    logger.info(f"📥 [API] GET /trends-agent/trends - platform={platform}, niche={niche}")
    
    # Parse window
    window_hours = {
        "1h": 1,
        "6h": 6,
        "24h": 24,
        "7d": 168,
    }.get(window, 24)
    
    agent = get_trends_agent()
    
    try:
        trends = await agent.detect_trends(
            platform=platform,
            niche=niche,
            window_hours=window_hours,
            min_velocity=5,
            limit=limit
        )
        
        # Filter by stage if specified
        if stage:
            trends = [t for t in trends if t.stage.value == stage]
        
        return {
            "trends": [t.to_dict() for t in trends],
            "count": len(trends),
            "query": {
                "platform": platform,
                "niche": niche,
                "window": window,
                "stage": stage,
            },
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Trend detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trends/{trend_id}")
async def get_trend(trend_id: str):
    """
    Get detailed information about a specific trend.
    """
    logger.info(f"📥 [API] GET /trends-agent/trends/{trend_id}")
    
    # For now, return mock data - in production, fetch from database
    # TODO: Implement database lookup
    
    return {
        "trend_id": trend_id,
        "message": "Trend lookup not yet implemented - use /trends endpoint to detect fresh trends",
    }


@router.post("/detect")
async def trigger_detection(
    query: TrendQuery,
    background_tasks: BackgroundTasks,
    save_results: bool = Query(True, description="Save detected trends to database"),
):
    """
    Trigger trend detection with custom parameters.
    
    This runs the full detection pipeline:
    1. Fetch recent posts
    2. Extract phrases
    3. Compute velocity
    4. Summarize context (AI)
    5. Generate outputs (AI)
    """
    logger.info(f"📥 [API] POST /trends-agent/detect")
    
    agent = get_trends_agent()
    
    try:
        trends = await agent.detect_trends(
            platform=query.platform,
            niche=query.niche,
            window_hours=query.window_hours,
            min_velocity=query.min_velocity,
            limit=20
        )
        
        # Save trends to database if requested
        saved_ids = []
        if save_results:
            for trend in trends:
                trend_id = await agent.save_trend(trend)
                if trend_id:
                    saved_ids.append(trend_id)
        
        return {
            "success": True,
            "trends_detected": len(trends),
            "trends_saved": len(saved_ids),
            "trends": [t.to_dict() for t in trends],
            "query": query.dict(),
            "detected_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/brief")
async def generate_brief(request: BriefRequest):
    """
    Generate a content brief from a trend.
    
    Takes a trend_id or trend_name and returns:
    - Hooks (3 variations)
    - Caption templates
    - Content angles
    - CTA options
    - Script outline
    
    This is what people integrate into their content engine.
    """
    logger.info(f"📥 [API] POST /trends-agent/brief - trend={request.trend_name or request.trend_id}")
    
    if not request.trend_name and not request.trend_id:
        raise HTTPException(status_code=400, detail="Either trend_id or trend_name required")
    
    agent = get_trends_agent()
    
    try:
        # If we have a trend name, generate fresh content
        trend_name = request.trend_name or request.trend_id
        
        # Summarize context
        lingo, context = await agent.summarize_context(
            phrase=trend_name,
            examples=[],
            niche=request.niche
        )
        
        # Generate outputs
        content_ready = await agent.generate_outputs(
            trend_name=trend_name,
            lingo=lingo,
            context=context,
            niche=request.niche,
            brand_voice=request.brand_voice,
            platform=request.platform
        )
        
        # Build comprehensive brief
        brief = {
            "trend_name": trend_name,
            "niche": request.niche,
            "platform": request.platform,
            "brand_voice": request.brand_voice,
            
            "lingo": lingo.to_dict(),
            "context": context.to_dict(),
            "content_ready": content_ready.to_dict(),
            
            # Script outline based on context
            "script_outline": {
                "hook": content_ready.hooks[0] if content_ready.hooks else "Attention-grabbing opener",
                "problem": f"The struggle everyone relates to about {trend_name}",
                "solution": f"Your unique take on {trend_name}",
                "proof": "Quick result or demonstration",
                "cta": content_ready.cta_options[0] if content_ready.cta_options else "Follow for more",
            },
            
            "recommended_format": "short_video",
            "optimal_length_sec": {"min": 15, "max": 45},
            
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        return brief
        
    except Exception as e:
        logger.error(f"Brief generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-digest")
async def get_daily_digest(
    niche: str = Query("general", description="Niche filter"),
    platforms: str = Query("tiktok,instagram", description="Comma-separated platforms"),
    limit: int = Query(10, ge=1, le=20),
):
    """
    Get the daily trend digest.
    
    This is the most sellable format:
    - 10 trends max
    - All actionable
    - No fluff
    - Ready for email/Slack/Discord
    """
    logger.info(f"📥 [API] GET /trends-agent/daily-digest - niche={niche}")
    
    agent = get_trends_agent()
    platform_list = [p.strip() for p in platforms.split(",")]
    
    try:
        # Collect trends from each platform
        all_trends = []
        for platform in platform_list:
            trends = await agent.detect_trends(
                platform=platform,
                niche=niche,
                window_hours=24,
                min_velocity=5,
                limit=limit
            )
            all_trends.extend(trends)
        
        # Deduplicate and sort
        seen_names = set()
        unique_trends = []
        for trend in sorted(all_trends, key=lambda t: t.signals.velocity_24h, reverse=True):
            if trend.trend_name.lower() not in seen_names:
                seen_names.add(trend.trend_name.lower())
                unique_trends.append(trend)
        
        # Build digest
        digest_items = []
        for i, trend in enumerate(unique_trends[:limit], 1):
            digest_items.append({
                "rank": i,
                "trend_name": trend.trend_name,
                "stage": trend.stage.value,
                "platforms": trend.platforms,
                "velocity": trend.signals.velocity_24h,
                "meaning": trend.context.meaning,
                "quick_hook": trend.content_ready.hooks[0] if trend.content_ready.hooks else None,
                "best_angle": trend.content_ready.angles[0] if trend.content_ready.angles else None,
                "brand_safe": trend.brand_safe,
            })
        
        return {
            "digest_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "niche": niche,
            "platforms": platform_list,
            "trend_count": len(digest_items),
            "trends": digest_items,
            "summary": f"Found {len(digest_items)} actionable trends for {niche} on {', '.join(platform_list)}",
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Daily digest failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emerging")
async def get_emerging_trends(
    niche: str = Query("general"),
    platform: str = Query("all"),
    limit: int = Query(5, ge=1, le=20),
):
    """
    Get only EMERGING trends (high velocity, just detected).
    
    These are the "act now" opportunities.
    """
    logger.info(f"📥 [API] GET /trends-agent/emerging")
    
    agent = get_trends_agent()
    
    try:
        trends = await agent.detect_trends(
            platform=platform,
            niche=niche,
            window_hours=6,  # Shorter window for emerging
            min_velocity=20,  # Higher velocity threshold
            limit=limit * 2
        )
        
        # Filter to emerging only
        emerging = [t for t in trends if t.stage == TrendStage.EMERGING][:limit]
        
        return {
            "emerging_trends": [t.to_dict() for t in emerging],
            "count": len(emerging),
            "alert": f"{len(emerging)} emerging trends detected" if emerging else "No emerging trends right now",
            "checked_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Emerging trends check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhooks")
async def register_webhook(config: WebhookConfig):
    """
    Register a webhook for trend alerts.
    
    Alerts will be sent when:
    - New emerging trend detected
    - Trend score exceeds threshold
    - Trend matches specified niches/platforms
    """
    logger.info(f"📥 [API] POST /trends-agent/webhooks - url={config.url}")
    
    # TODO: Implement webhook storage and delivery
    # For now, just acknowledge the registration
    
    return {
        "status": "registered",
        "webhook_id": f"wh_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        "config": config.dict(),
        "message": "Webhook registered. Alerts will be sent when matching trends are detected.",
    }


@router.get("/stats")
async def get_trend_stats():
    """
    Get statistics about trend detection.
    """
    return {
        "service": "trends_agent",
        "version": "1.0.0",
        "capabilities": [
            "phrase_detection",
            "velocity_scoring",
            "ai_context_extraction",
            "content_generation",
            "brand_safety_check",
        ],
        "supported_platforms": ["tiktok", "instagram", "youtube", "threads"],
        "supported_niches": [
            "general", "fitness", "finance", "tech", "lifestyle",
            "beauty", "food", "travel", "gaming", "education"
        ],
        "output_formats": ["trend_v1", "brief", "daily_digest"],
        "status": "operational",
    }


# =============================================================================
# INTEGRATION: Format Generator Bridge
# =============================================================================

@router.post("/to-format-brief")
async def trend_to_format_brief(
    trend_id: Optional[str] = None,
    trend_name: Optional[str] = None,
    format_id: str = Query("broll_text_v1", description="Target format ID"),
    niche: str = Query("general"),
):
    """
    Convert a trend into a format-ready brief for Remotion/Motion Canvas.
    
    This bridges the Trends Agent to the Format Generator,
    so a trend can become a renderable video in one call.
    """
    logger.info(f"📥 [API] POST /trends-agent/to-format-brief - format={format_id}")
    
    if not trend_name and not trend_id:
        raise HTTPException(status_code=400, detail="Either trend_id or trend_name required")
    
    agent = get_trends_agent()
    name = trend_name or trend_id
    
    try:
        # Get trend context
        lingo, context = await agent.summarize_context(
            phrase=name,
            examples=[],
            niche=niche
        )
        
        # Generate content
        content = await agent.generate_outputs(
            trend_name=name,
            lingo=lingo,
            context=context,
            niche=niche,
        )
        
        # Build format-specific brief
        format_brief = {
            "format_id": format_id,
            "trend_source": {
                "trend_name": name,
                "meaning": context.meaning,
                "tone": context.tone,
            },
            
            # For broll_text_v1 format
            "text_overlays": [
                {"text": hook, "position": "center", "beat": "hook"}
                for hook in content.hooks[:3]
            ],
            
            # Suggested B-roll search queries
            "broll_queries": context.best_for[:3] if context.best_for else ["engaging content"],
            
            # Caption for post
            "caption": content.caption_templates[0] if content.caption_templates else name,
            
            # Render parameters
            "render_params": {
                "duration_sec": 15,
                "text_style": "bold",
                "text_position": "center",
                "music_mood": "upbeat" if context.tone == "casual" else "professional",
            },
            
            "ready_for_render": True,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        return format_brief
        
    except Exception as e:
        logger.error(f"Format brief generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
