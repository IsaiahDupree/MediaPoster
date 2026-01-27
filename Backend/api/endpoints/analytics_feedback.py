"""
API Endpoints for Analytics Feedback Loop
Provides AI-powered performance insights and content optimization recommendations.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from loguru import logger

router = APIRouter(prefix="/analytics-ci", tags=["Analytics Insights"])


@router.get("/weekly-report")
async def get_weekly_report():
    """Get weekly performance report with AI insights."""
    try:
        from services.analytics_feedback import get_feedback_loop
        
        feedback = get_feedback_loop()
        report = await feedback.generate_weekly_report()
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-insights")
async def generate_insights(days: int = 7, platform: Optional[str] = None):
    """Generate AI-powered performance insights."""
    try:
        from services.analytics_feedback import get_feedback_loop
        
        feedback = get_feedback_loop()
        insights = await feedback.analyze_recent_performance(days=days, platform=platform)
        
        return {
            "insights": [
                {
                    "insight_type": i.insight_type,
                    "title": i.title,
                    "description": i.description,
                    "confidence": i.confidence,
                    "applicable_to": i.applicable_to,
                    "action_items": i.action_items
                }
                for i in insights
            ],
            "period_days": days,
            "platform": platform
        }
        
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_performance_summary(days: int = 7, platform: Optional[str] = None):
    """Get performance summary for the specified period."""
    try:
        from services.analytics_feedback import get_feedback_loop
        
        feedback = get_feedback_loop()
        summary = feedback.get_performance_summary(days=days, platform=platform)
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization-hints")
async def get_optimization_hints(platform: Optional[str] = None, content_type: str = "short_video"):
    """Get content optimization hints based on performance data."""
    try:
        from services.analytics_feedback import get_feedback_loop
        
        feedback = get_feedback_loop()
        hints = await feedback.get_content_optimization_hints(platform=platform, content_type=content_type)
        
        return hints
        
    except Exception as e:
        logger.error(f"Failed to get optimization hints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-performers")
async def get_top_performers(days: int = 30, limit: int = 10, platform: Optional[str] = None):
    """Get top performing content."""
    try:
        from services.analytics_feedback import get_feedback_loop
        
        feedback = get_feedback_loop()
        top_content = feedback.get_top_performing_content(days=days, limit=limit, platform=platform)
        
        return {
            "top_performers": [
                {
                    "content_id": p.content_id,
                    "platform": p.platform,
                    "views": p.views,
                    "likes": p.likes,
                    "comments": p.comments,
                    "shares": p.shares,
                    "engagement_rate": p.engagement_rate,
                    "hook": p.hook,
                    "posted_at": p.posted_at.isoformat() if p.posted_at else None
                }
                for p in top_content
            ],
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get top performers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/low-performers")
async def get_low_performers(days: int = 7, limit: int = 10, platform: Optional[str] = None):
    """Get low performing content for analysis."""
    try:
        from services.analytics_feedback import get_feedback_loop
        
        feedback = get_feedback_loop()
        low_content = feedback.get_low_performing_content(days=days, limit=limit, platform=platform)
        
        return {
            "low_performers": [
                {
                    "content_id": p.content_id,
                    "platform": p.platform,
                    "views": p.views,
                    "engagement_rate": p.engagement_rate,
                    "hook": p.hook
                }
                for p in low_content
            ],
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"Failed to get low performers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enhance-prompt")
async def enhance_prompt(base_prompt: str, platform: Optional[str] = None):
    """Enhance a content generation prompt with performance insights."""
    try:
        from services.analytics_feedback import get_feedback_loop
        
        feedback = get_feedback_loop()
        hints = await feedback.get_content_optimization_hints(platform=platform)
        enhanced = feedback.enhance_prompt_with_insights(base_prompt, hints)
        
        return {
            "original_prompt": base_prompt,
            "enhanced_prompt": enhanced,
            "hints_applied": hints
        }
        
    except Exception as e:
        logger.error(f"Failed to enhance prompt: {e}")
        raise HTTPException(status_code=500, detail=str(e))
