"""
Template Leaderboard API Endpoints (OPS-007)
=============================================
API for template performance ranking and bandit allocation.

Endpoints:
- GET /api/templates/leaderboard - Get ranked templates
- POST /api/templates/leaderboard/recompute - Trigger ranking recomputation
- GET /api/templates/top - Get top performing templates
- POST /api/templates/sample - Sample template using bandit strategy
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from loguru import logger

from services.template_leaderboard import get_template_leaderboard


router = APIRouter(prefix="/api/templates", tags=["Template Leaderboard"])


class SampleTemplateRequest(BaseModel):
    """Request to sample a template using bandit allocation"""
    channel: str = Field(..., description="Channel to sample for (twitter, instagram, etc.)")
    awareness_level: str = Field(..., description="Awareness level (unaware, problem_aware, etc.)")
    brand_id: Optional[UUID] = Field(default=None, description="Optional brand filter")
    exclude_template_ids: Optional[List[UUID]] = Field(default=None, description="Templates to exclude")


@router.get("/leaderboard")
async def get_leaderboard(
    channel: Optional[str] = Query(default=None, description="Filter by channel"),
    awareness_level: Optional[str] = Query(default=None, description="Filter by awareness level"),
    brand_id: Optional[UUID] = Query(default=None, description="Filter by brand"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of templates")
):
    """
    Get template leaderboard ranked by performance

    Returns templates ordered by reward score and usage count.
    Optionally filter by channel, awareness level, or brand.

    Args:
        channel: Filter by channel (optional)
        awareness_level: Filter by awareness level (optional)
        brand_id: Filter by brand (optional)
        limit: Maximum number of templates to return (1-100)

    Returns:
        List of ranked templates with performance metrics
    """
    try:
        leaderboard = get_template_leaderboard()
        templates = await leaderboard.get_top_templates(
            channel=channel,
            awareness_level=awareness_level,
            brand_id=brand_id,
            limit=limit
        )

        return {
            "success": True,
            "data": {
                "templates": templates,
                "count": len(templates),
                "filters": {
                    "channel": channel,
                    "awareness_level": awareness_level,
                    "brand_id": str(brand_id) if brand_id else None
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting template leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/leaderboard/recompute")
async def recompute_leaderboard():
    """
    Manually trigger template ranking recomputation

    Recalculates performance labels and reward scores for all templates.
    This is normally done automatically every 6 hours, but can be
    triggered manually after significant touchpoint updates.

    Returns:
        Summary of updated templates
    """
    try:
        leaderboard = get_template_leaderboard()
        result = await leaderboard.recompute_rankings()

        return {
            "success": True,
            "message": f"Recomputed rankings for {result['updated']} templates",
            "data": result
        }

    except Exception as e:
        logger.error(f"Error recomputing template leaderboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top")
async def get_top_templates(
    channel: Optional[str] = Query(default=None, description="Filter by channel"),
    awareness_level: Optional[str] = Query(default=None, description="Filter by awareness level"),
    brand_id: Optional[UUID] = Query(default=None, description="Filter by brand"),
    limit: int = Query(default=10, ge=1, le=50, description="Number of top templates")
):
    """
    Get top performing templates

    Quick endpoint to get just the top N templates without full leaderboard.

    Args:
        channel: Filter by channel (optional)
        awareness_level: Filter by awareness level (optional)
        brand_id: Filter by brand (optional)
        limit: Number of top templates to return (1-50)

    Returns:
        Top performing templates
    """
    try:
        leaderboard = get_template_leaderboard()
        templates = await leaderboard.get_top_templates(
            channel=channel,
            awareness_level=awareness_level,
            brand_id=brand_id,
            limit=limit
        )

        return {
            "success": True,
            "data": templates
        }

    except Exception as e:
        logger.error(f"Error getting top templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sample")
async def sample_template(request: SampleTemplateRequest):
    """
    Sample a template using bandit allocation strategy

    Uses multi-armed bandit approach:
    - 70% → Top performers (exploit)
    - 20% → Promising templates (explore)
    - 10% → Untested templates (experiment)

    This ensures we mostly use proven winners while still exploring
    new templates and giving promising ones more data.

    Args:
        channel: Channel to sample for
        awareness_level: Awareness level to match
        brand_id: Optional brand filter
        exclude_template_ids: Templates to exclude from sampling

    Returns:
        Selected template ID and metadata
    """
    try:
        leaderboard = get_template_leaderboard()
        template_id = await leaderboard.sample_template(
            channel=request.channel,
            awareness_level=request.awareness_level,
            brand_id=request.brand_id,
            exclude_template_ids=request.exclude_template_ids
        )

        if not template_id:
            raise HTTPException(
                status_code=404,
                detail=f"No templates found for channel={request.channel}, "
                       f"awareness_level={request.awareness_level}"
            )

        return {
            "success": True,
            "data": {
                "template_id": str(template_id),
                "channel": request.channel,
                "awareness_level": request.awareness_level
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sampling template: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_leaderboard_stats():
    """
    Get template leaderboard statistics

    Returns aggregate stats about template performance distribution.

    Returns:
        - Total templates
        - Templates by performance label
        - Average reward scores
        - Usage statistics
    """
    try:
        leaderboard = get_template_leaderboard()

        # Get all templates to compute stats
        all_templates = await leaderboard.get_top_templates(limit=1000)

        # Group by performance label
        label_counts = {}
        total_usage = 0
        total_reward = 0.0
        scored_count = 0

        for template in all_templates:
            label = template.get("performance_label", "unknown")
            label_counts[label] = label_counts.get(label, 0) + 1

            total_usage += template.get("usage_count", 0)
            reward = template.get("avg_reward_score", 0.0)
            if reward > 0:
                total_reward += reward
                scored_count += 1

        avg_reward = total_reward / scored_count if scored_count > 0 else 0.0

        return {
            "success": True,
            "data": {
                "total_templates": len(all_templates),
                "label_distribution": label_counts,
                "total_usage": total_usage,
                "average_reward_score": round(avg_reward, 3),
                "templates_with_data": scored_count,
                "bandit_allocation": {
                    "exploit": f"{leaderboard.exploit_weight * 100}%",
                    "explore": f"{leaderboard.explore_weight * 100}%",
                    "experiment": f"{leaderboard.experiment_weight * 100}%"
                }
            }
        }

    except Exception as e:
        logger.error(f"Error getting leaderboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
