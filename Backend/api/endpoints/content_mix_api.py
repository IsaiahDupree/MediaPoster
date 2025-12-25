"""
Content Mix Planner API Endpoints
Long-term content scheduling with mixed content types
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date
from loguru import logger

from services.content_mix_planner import (
    get_content_mix_planner,
    ScheduleConfig,
    ScheduleDuration,
    ContentMix,
    ContentType
)

router = APIRouter(prefix="/api/content-mix", tags=["Content Mix Planner"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ContentMixRequest(BaseModel):
    """Content mix percentages"""
    ugc_caption_percentage: float = Field(40.0, ge=0, le=100)
    carousel_percentage: float = Field(20.0, ge=0, le=100)
    ai_generated_percentage: float = Field(20.0, ge=0, le=100)
    animated_percentage: float = Field(10.0, ge=0, le=100)
    raw_ugc_percentage: float = Field(10.0, ge=0, le=100)


class GeneratePlanRequest(BaseModel):
    """Request to generate a long-term content plan"""
    name: Optional[str] = None
    duration: str = "2_months"
    custom_days: Optional[int] = None
    posts_per_day: int = Field(2, ge=1, le=10)
    platforms: List[str] = ["tiktok", "instagram"]
    content_mix: ContentMixRequest = Field(default_factory=ContentMixRequest)
    posting_times: List[str] = ["09:00", "18:00"]
    goal_id: Optional[str] = None
    start_date: Optional[str] = None


class UpdateSlotRequest(BaseModel):
    """Request to update a single slot"""
    content_id: Optional[str] = None
    content_title: Optional[str] = None
    content_type: Optional[str] = None
    platform: Optional[str] = None
    pillar: Optional[str] = None
    status: Optional[str] = None


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/durations")
async def get_available_durations():
    """Get available schedule duration options"""
    return {
        "durations": [
            {"value": "1_week", "label": "1 Week", "days": 7},
            {"value": "2_weeks", "label": "2 Weeks", "days": 14},
            {"value": "1_month", "label": "1 Month", "days": 30},
            {"value": "2_months", "label": "2 Months", "days": 60},
            {"value": "3_months", "label": "3 Months", "days": 90},
            {"value": "6_months", "label": "6 Months", "days": 180},
            {"value": "1_year", "label": "1 Year", "days": 365},
            {"value": "custom", "label": "Custom", "days": None}
        ]
    }


@router.get("/content-types")
async def get_content_types():
    """Get available content types"""
    return {
        "content_types": [
            {
                "value": "ugc_caption",
                "label": "UGC with Caption",
                "description": "User-generated content with AI-generated captions",
                "icon": "📝"
            },
            {
                "value": "carousel",
                "label": "Carousel",
                "description": "Multi-image carousel posts",
                "icon": "🎠"
            },
            {
                "value": "ai_generated",
                "label": "AI Generated",
                "description": "Fully AI-generated video content",
                "icon": "🤖"
            },
            {
                "value": "animated",
                "label": "Animated",
                "description": "Animated/motion graphics content",
                "icon": "✨"
            },
            {
                "value": "raw_ugc",
                "label": "Raw UGC",
                "description": "Raw user-generated content as-is",
                "icon": "📱"
            }
        ]
    }


@router.post("/plans/generate")
async def generate_plan(request: GeneratePlanRequest):
    """
    Generate a long-term content plan with mixed content types.
    
    This creates a schedule spanning weeks or months with different
    content types distributed according to the specified mix.
    """
    try:
        planner = get_content_mix_planner()
        
        # Parse duration
        try:
            duration = ScheduleDuration(request.duration)
        except ValueError:
            duration = ScheduleDuration.TWO_MONTHS
        
        # Create content mix
        content_mix = ContentMix(
            ugc_caption_percentage=request.content_mix.ugc_caption_percentage,
            carousel_percentage=request.content_mix.carousel_percentage,
            ai_generated_percentage=request.content_mix.ai_generated_percentage,
            animated_percentage=request.content_mix.animated_percentage,
            raw_ugc_percentage=request.content_mix.raw_ugc_percentage
        )
        
        if not content_mix.validate():
            raise HTTPException(
                status_code=400,
                detail="Content mix percentages must sum to 100%"
            )
        
        # Create config
        config = ScheduleConfig(
            duration=duration,
            custom_days=request.custom_days,
            posts_per_day=request.posts_per_day,
            platforms=request.platforms,
            content_mix=content_mix,
            posting_times=request.posting_times,
            goal_id=request.goal_id
        )
        
        # Parse start date
        start_date = None
        if request.start_date:
            start_date = date.fromisoformat(request.start_date)
        
        # Generate plan
        plan = await planner.generate_plan(
            config=config,
            start_date=start_date,
            name=request.name
        )
        
        return plan.to_dict()
        
    except Exception as e:
        logger.error(f"Error generating content mix plan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans")
async def list_plans(limit: int = Query(20, ge=1, le=100)):
    """List all content mix plans"""
    try:
        planner = get_content_mix_planner()
        plans = await planner.list_plans(limit)
        return {"plans": plans, "count": len(plans)}
    except Exception as e:
        logger.error(f"Error listing plans: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: str):
    """Get a specific content mix plan with all slots"""
    try:
        planner = get_content_mix_planner()
        plan = await planner.get_plan(plan_id)
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        return plan.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/slots/{slot_id}")
async def update_slot(slot_id: str, request: UpdateSlotRequest):
    """Update a single slot in a plan"""
    try:
        planner = get_content_mix_planner()
        
        updates = {}
        if request.content_id is not None:
            updates["content_id"] = request.content_id
        if request.content_title is not None:
            updates["content_title"] = request.content_title
        if request.content_type is not None:
            updates["content_type"] = request.content_type
        if request.platform is not None:
            updates["platform"] = request.platform
        if request.pillar is not None:
            updates["pillar"] = request.pillar
        if request.status is not None:
            updates["status"] = request.status
        
        success = await planner.update_slot(slot_id, updates)
        
        if not success:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        return {"updated": True, "slot_id": slot_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating slot {slot_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/plans/{plan_id}/approve")
async def approve_plan(plan_id: str):
    """Approve a plan and create scheduled posts"""
    try:
        planner = get_content_mix_planner()
        result = await planner.approve_plan(plan_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error approving plan {plan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/plans/{plan_id}/summary")
async def get_plan_summary(plan_id: str):
    """Get summary statistics for a plan"""
    try:
        planner = get_content_mix_planner()
        plan = await planner.get_plan(plan_id)
        
        if not plan:
            raise HTTPException(status_code=404, detail="Plan not found")
        
        # Calculate weekly breakdown
        weeks = {}
        for slot in plan.slots:
            week_num = (slot.date - plan.start_date).days // 7 + 1
            if week_num not in weeks:
                weeks[week_num] = {"posts": 0, "content_types": {}}
            weeks[week_num]["posts"] += 1
            ct = slot.content_type.value if hasattr(slot.content_type, 'value') else slot.content_type
            weeks[week_num]["content_types"][ct] = weeks[week_num]["content_types"].get(ct, 0) + 1
        
        # Platform breakdown
        platforms = {}
        for slot in plan.slots:
            platforms[slot.platform] = platforms.get(slot.platform, 0) + 1
        
        return {
            "plan_id": plan_id,
            "name": plan.name,
            "total_days": (plan.end_date - plan.start_date).days + 1,
            "total_posts": plan.total_posts,
            "content_distribution": plan.content_type_distribution,
            "platform_distribution": platforms,
            "weekly_breakdown": weeks,
            "start_date": plan.start_date.isoformat(),
            "end_date": plan.end_date.isoformat(),
            "status": plan.status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting plan summary {plan_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
