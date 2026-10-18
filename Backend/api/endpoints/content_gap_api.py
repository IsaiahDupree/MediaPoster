"""
Content Gap Analysis API Endpoints
Identify content themes competitors cover that the user doesn't.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from services.content_gap_service import get_content_gap_service

router = APIRouter(prefix="/api/gap-analysis", tags=["Content Gap Analysis"])


class RunGapAnalysisRequest(BaseModel):
    """Request to run a content gap analysis"""
    user_themes: Optional[List[str]] = None
    user_captions: Optional[List[str]] = None
    competitor_usernames: Optional[List[str]] = None


@router.get("/health")
async def health_check():
    """Health check for content gap analysis service"""
    return {
        "status": "healthy",
        "service": "content-gap-analysis",
    }


@router.post("/run")
async def run_gap_analysis(request: RunGapAnalysisRequest = RunGapAnalysisRequest()):
    """
    Run a content gap analysis.
    
    Compares user's content themes against competitors to find:
    - **Gap themes**: Topics competitors cover that user doesn't (opportunities!)
    - **Overlap themes**: Topics both cover (benchmark your performance)
    - **Unique themes**: Topics only user covers (potential differentiators)
    
    Optionally pass:
    - user_themes: Explicit list of themes you cover
    - user_captions: Your recent captions (AI will extract themes)
    - competitor_usernames: Specific competitors (default: all tracked)
    """
    service = get_content_gap_service()

    try:
        result = await service.analyze_gaps(
            user_themes=request.user_themes,
            user_captions=request.user_captions,
            competitor_usernames=request.competitor_usernames,
        )

        return {
            "status": "analyzed",
            "result": result.model_dump(),
        }

    except Exception as e:
        logger.error(f"Error running gap analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest")
async def get_latest_gap_analysis():
    """Get the most recent content gap analysis results"""
    service = get_content_gap_service()
    result = service.get_latest_analysis()

    if not result:
        raise HTTPException(
            status_code=404,
            detail="No gap analysis found. POST /api/gap-analysis/run first.",
        )

    return result.model_dump()
