from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid

from database.connection import get_db
from services.ai_recommendation_service import AIRecommendationService
from pydantic import BaseModel

router = APIRouter()

class RecommendationResponse(BaseModel):
    id: uuid.UUID
    insight_type: str
    title: str
    description: str
    metric_impact: str | None
    confidence_score: float | None
    status: str
    created_at: Any

class GenerateRequest(BaseModel):
    user_id: uuid.UUID

@router.post("/generate", response_model=List[Dict[str, Any]])
async def generate_recommendations(
    request: GenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger generation of new AI recommendations for a user.
    """
    service = AIRecommendationService(db)
    try:
        recommendations = await service.generate_daily_recommendations(request.user_id)
        return recommendations
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate recommendations: {str(e)}"
        )

@router.get("/", response_model=List[RecommendationResponse])
def get_active_recommendations(
    user_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """
    Get active recommendations for a user.
    """
    service = AIRecommendationService(db)
    return service.get_active_recommendations(user_id)

@router.post("/{id}/action")
def action_recommendation(
    id: uuid.UUID,
    action: str, # accept, reject, dismiss
    db: Session = Depends(get_db)
):
    """
    Take an action on a recommendation.
    """
    service = AIRecommendationService(db)
    success = service.action_recommendation(id, action)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found"
        )
    return {"success": True}
