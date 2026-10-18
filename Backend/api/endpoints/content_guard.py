"""
Content Guard API Endpoints
===========================
Quality gates and duplicate detection before posting.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from loguru import logger

from services.content_guard.duplicate_detector import DuplicateDetector

router = APIRouter(prefix="/api/v1/content-guard", tags=["Content Guard"])


# =========================================================================
# Request/Response Models
# =========================================================================

class DuplicateCheckRequest(BaseModel):
    account_id: str = Field(..., description="Account ID to check against")
    transcript: str = Field(..., description="Content transcript or script")
    platform: str = Field("instagram", description="Target platform")
    title: Optional[str] = Field(None, description="Content title")
    strict: bool = Field(False, description="Use stricter similarity threshold")


class DuplicateCheckResponse(BaseModel):
    is_duplicate: bool
    similarity_score: float
    similar_post_id: Optional[str]
    similar_post_platform: Optional[str]
    similar_post_date: Optional[str]
    reason: str
    can_post: bool
    warnings: List[str]


class RegisterContentRequest(BaseModel):
    content_id: str = Field(..., description="Unique content ID")
    account_id: str = Field(..., description="Account that posted")
    platform: str = Field(..., description="Platform posted to")
    transcript: str = Field(..., description="Content transcript")


class BatchCheckRequest(BaseModel):
    account_id: str = Field(..., description="Account ID")
    items: List[dict] = Field(..., description="List of {transcript, platform} items to check")


# =========================================================================
# Endpoints
# =========================================================================

@router.post("/check-duplicate", response_model=DuplicateCheckResponse)
async def check_duplicate(request: DuplicateCheckRequest):
    """
    Check if content is a duplicate before posting.
    
    This endpoint compares the provided transcript against all previously
    posted content for the given account. Uses TF-IDF + cosine similarity
    for accurate duplicate detection.
    
    Returns:
        - is_duplicate: True if content should NOT be posted
        - similarity_score: 0-1 score (1 = exact match)
        - can_post: Quick boolean for posting decision
        - warnings: Any near-duplicate warnings
    """
    detector = DuplicateDetector()
    
    try:
        result = await detector.check_content(
            account_id=request.account_id,
            transcript=request.transcript,
            platform=request.platform,
            title=request.title,
            strict=request.strict
        )
        
        return DuplicateCheckResponse(
            is_duplicate=result.is_duplicate,
            similarity_score=result.similarity_score,
            similar_post_id=result.similar_post_id,
            similar_post_platform=result.similar_post_platform,
            similar_post_date=result.similar_post_date,
            reason=result.reason,
            can_post=result.can_post,
            warnings=result.warnings
        )
        
    except Exception as e:
        logger.error(f"Duplicate check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register-content")
async def register_content(request: RegisterContentRequest):
    """
    Register content after posting for future duplicate checks.
    
    Call this AFTER successfully posting content to track it
    for duplicate detection on future posts.
    """
    detector = DuplicateDetector()
    
    try:
        success = await detector.register_posted_content(
            content_id=request.content_id,
            account_id=request.account_id,
            platform=request.platform,
            transcript=request.transcript
        )
        
        if success:
            return {
                "status": "registered",
                "content_id": request.content_id,
                "account_id": request.account_id,
                "platform": request.platform
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to register content")
            
    except Exception as e:
        logger.error(f"Content registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch-check")
async def batch_check_duplicates(request: BatchCheckRequest):
    """
    Check multiple pieces of content for duplicates in one call.
    
    Useful for checking a batch of scheduled content.
    """
    detector = DuplicateDetector()
    results = []
    
    for i, item in enumerate(request.items):
        try:
            result = await detector.check_content(
                account_id=request.account_id,
                transcript=item.get("transcript", ""),
                platform=item.get("platform", "instagram")
            )
            results.append({
                "index": i,
                "is_duplicate": result.is_duplicate,
                "can_post": result.can_post,
                "similarity_score": result.similarity_score,
                "reason": result.reason
            })
        except Exception as e:
            results.append({
                "index": i,
                "error": str(e)
            })
    
    duplicates_found = sum(1 for r in results if r.get("is_duplicate", False))
    
    return {
        "account_id": request.account_id,
        "total_checked": len(request.items),
        "duplicates_found": duplicates_found,
        "can_post_all": duplicates_found == 0,
        "results": results
    }


@router.get("/account-history/{account_id}")
async def get_account_history(
    account_id: str,
    limit: int = Query(50, ge=1, le=200)
):
    """
    Get posting history for an account.
    
    Returns recently posted content fingerprints for review.
    """
    detector = DuplicateDetector()
    
    try:
        history = await detector.get_account_history(account_id, limit)
        return {
            "account_id": account_id,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/info")
async def content_guard_info():
    """Get Content Guard feature information"""
    return {
        "name": "Content Guard",
        "description": "Quality gates and duplicate detection for content posting",
        "version": "1.0.0",
        "features": [
            {
                "name": "Duplicate Detection",
                "endpoint": "/check-duplicate",
                "description": "Check if content is similar to previously posted content"
            },
            {
                "name": "Content Registration",
                "endpoint": "/register-content",
                "description": "Register posted content for future duplicate checks"
            },
            {
                "name": "Batch Check",
                "endpoint": "/batch-check",
                "description": "Check multiple pieces of content at once"
            },
            {
                "name": "Account History",
                "endpoint": "/account-history/{account_id}",
                "description": "View posting history for an account"
            }
        ],
        "thresholds": {
            "default": 0.85,
            "strict": 0.70,
            "loose": 0.92
        }
    }
