"""
Data Orchestrator API Endpoints
Exposes the unified platform data fetching system via REST API
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional
from pydantic import BaseModel
import logging

from services.platform_data_orchestrator import (
    get_orchestrator,
    Platform,
    DataType
)
from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)
router = APIRouter()


class PopulateRequest(BaseModel):
    platform: str
    username: str


class RefreshAllResponse(BaseModel):
    success: int
    failed: int
    errors: list


@router.get("/status")
async def get_orchestrator_status():
    """Get status of all API providers across platforms."""
    orchestrator = get_orchestrator()
    return {
        "providers": orchestrator.get_provider_status(),
        "cache_size": len(orchestrator._cache),
    }


@router.post("/refresh-all")
async def refresh_all_accounts(background_tasks: BackgroundTasks):
    """
    Refresh data for all connected social accounts.
    Uses failover and efficient batching.
    """
    orchestrator = get_orchestrator()
    results = await orchestrator.refresh_all_accounts()
    return results


@router.post("/populate-engagement")
async def populate_engagement_data(request: PopulateRequest):
    """
    Fetch comprehensive engagement data for a specific account.
    Populates: profile, posts, comments, engaged followers.
    """
    try:
        platform = Platform(request.platform.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {request.platform}")
    
    orchestrator = get_orchestrator()
    results = await orchestrator.populate_engagement_data(platform, request.username)
    return results


@router.get("/fetch/profile/{platform}/{username}")
async def fetch_profile(platform: str, username: str):
    """Fetch profile data with failover."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
    
    orchestrator = get_orchestrator()
    result = await orchestrator.fetch_profile(plat, username)
    
    if result.success:
        return {
            "data": result.data,
            "provider": result.provider_used,
            "cached": result.cached,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/fetch/posts/{platform}/{username}")
async def fetch_posts(platform: str, username: str, count: int = 20):
    """Fetch user posts with failover."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
    
    orchestrator = get_orchestrator()
    result = await orchestrator.fetch_posts(plat, username, count)
    
    if result.success:
        return {
            "data": result.data,
            "provider": result.provider_used,
            "cached": result.cached,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)


@router.get("/fetch/comments/{platform}/{post_id}")
async def fetch_comments(platform: str, post_id: str, count: int = 50):
    """Fetch post comments with failover."""
    try:
        plat = Platform(platform.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid platform: {platform}")
    
    orchestrator = get_orchestrator()
    result = await orchestrator.fetch_comments(plat, post_id, count)
    
    if result.success:
        return {
            "data": result.data,
            "provider": result.provider_used,
            "cached": result.cached,
        }
    else:
        raise HTTPException(status_code=500, detail=result.error)
