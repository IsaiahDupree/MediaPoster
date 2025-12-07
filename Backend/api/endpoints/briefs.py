"""
Content Briefs API endpoints
Generate and view strategic content briefs for segments
"""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db
from database.models import Segment
from services.content_brief import ContentBriefGenerator

router = APIRouter()


@router.get("/")
async def list_briefs(
    segment_id: Optional[UUID] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List content briefs"""
    try:
        # For now, return empty list as briefs are generated on-demand
        # In the future, this would query a briefs table
        return {
            "briefs": [],
            "total": 0,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GenerateBriefRequest(BaseModel):
    segment_id: UUID
    campaign_goal: str  # educate, nurture, launch, reactivation
    traffic_type: str = 'organic'  # organic or paid
    time_window_days: int = 30
    budget_range: Optional[Dict[str, float]] = None


@router.post("/generate")
async def generate_brief(
    request: GenerateBriefRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a content brief for a segment
    
    Supports both organic and paid briefs
    """
    generator = ContentBriefGenerator(db)
    
    # Verify segment exists
    result = await db.execute(
        select(Segment).where(Segment.id == request.segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    try:
        if request.traffic_type == 'organic':
            brief = await generator.generate_organic_brief(
                segment_id=request.segment_id,
                campaign_goal=request.campaign_goal,
                time_window_days=request.time_window_days
            )
        elif request.traffic_type == 'paid':
            brief = await generator.generate_paid_brief(
                segment_id=request.segment_id,
                campaign_goal=request.campaign_goal,
                budget_range=request.budget_range,
                time_window_days=request.time_window_days
            )
        else:
            raise HTTPException(status_code=400, detail="traffic_type must be 'organic' or 'paid'")
        
        return {
            "status": "success",
            "brief": brief
        }
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating brief: {str(e)}")


@router.get("/goals")
async def list_campaign_goals():
    """List available campaign goals"""
    return {
        "goals": [
            {
                "id": "educate",
                "name": "Educate",
                "description": "Teach audience about topic, build authority"
            },
            {
                "id": "nurture",
                "name": "Nurture",
                "description": "Deepen relationship, build trust"
            },
            {
                "id": "launch",
                "name": "Launch",
                "description": "Introduce new product/service, generate excitement"
            },
            {
                "id": "reactivation",
                "name": "Reactivation",
                "description": "Re-engage dormant audience, win them back"
            }
        ]
    }


@router.post("/test-brief")
async def test_brief_generation(db: AsyncSession = Depends(get_db)):
    """
    Test endpoint to generate a sample brief
    Useful for testing without creating full segment structure
    """
    # This would use mock data or a test segment
    return {
        "status": "success",
        "message": "Test brief generation - implement with real segment data"
    }
