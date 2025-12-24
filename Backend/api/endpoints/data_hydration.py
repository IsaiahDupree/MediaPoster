"""
Data Hydration API Endpoints
Centralized data fetching and page data providers
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Optional, List
from pydantic import BaseModel

from services.data_hydration_service import (
    get_hydration_service,
    DataDomain
)
from services.event_bus import EventBus, Topics

router = APIRouter()


class RefreshRequest(BaseModel):
    domains: Optional[List[str]] = None  # None = all


@router.get("/status")
async def get_hydration_status():
    """Get current hydration status - last refresh times, record counts."""
    service = get_hydration_service()
    return await service.get_status()


@router.post("/refresh")
async def master_refresh(request: RefreshRequest = None, background_tasks: BackgroundTasks = None):
    """
    Master refresh - fetches all data from APIs and populates database.
    
    Domains: accounts, posts, comments, followers, metrics, all
    
    This is the main "re-fetch" button that hydrates all pages.
    """
    service = get_hydration_service()
    
    domains = None
    if request and request.domains:
        try:
            domains = [DataDomain(d.lower()) for d in request.domains]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid domain: {e}")
    
    results = await service.master_refresh(domains)
    
    # Convert results to serializable format
    return {
        domain: {
            "success": result.success,
            "records_updated": result.records_updated,
            "duration_seconds": round(result.duration_seconds, 2),
            "error": result.error,
        }
        for domain, result in results.items()
        if hasattr(result, 'success')
    }


@router.post("/refresh-background")
async def master_refresh_background(background_tasks: BackgroundTasks, request: RefreshRequest = None):
    """
    Start master refresh in background - returns immediately.
    Use /status to check progress.
    """
    service = get_hydration_service()
    
    if service.status.refresh_in_progress:
        return {"status": "already_running", "current_domain": service.status.current_domain}
    
    domains = None
    if request and request.domains:
        try:
            domains = [DataDomain(d.lower()) for d in request.domains]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid domain: {e}")
    
    background_tasks.add_task(service.master_refresh, domains)
    
    return {"status": "started", "domains": request.domains if request else ["all"]}


# =========================================================================
# PAGE DATA ENDPOINTS - Pull from centralized data
# =========================================================================

@router.get("/page/analytics")
async def get_analytics_page_data():
    """Get hydrated data for Analytics/Dashboard page."""
    service = get_hydration_service()
    return await service.get_analytics_overview()


@router.get("/page/content-performance")
async def get_content_performance_page_data(limit: int = 100):
    """Get hydrated data for Content Performance page."""
    service = get_hydration_service()
    return await service.get_content_performance(limit)


@router.get("/page/followers")
async def get_followers_page_data(
    platform: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 50
):
    """Get hydrated data for Followers/Top Fans page."""
    service = get_hydration_service()
    return await service.get_top_fans(platform, tier, limit)


@router.get("/page/people")
async def get_people_page_data(limit: int = 50):
    """Get hydrated data for People page."""
    service = get_hydration_service()
    return await service.get_people(limit)


@router.get("/page/schedule")
async def get_schedule_page_data(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """
    Get hydrated data for Schedule/Calendar page.
    
    Returns:
    - scheduled_posts: All scheduled posts with content metadata
    - accounts: Connected social media accounts for selector
    - media_library: Analyzed content for media selector
    - platform_stats: Posts per platform
    - stats: Overall schedule statistics
    """
    service = get_hydration_service()
    return await service.get_schedule_data(start_date, end_date)


@router.get("/page/narrative-builder")
async def get_narrative_builder_page_data():
    """
    Get hydrated data for Narrative Builder page.
    
    Returns:
    - candidates: Content candidates for scheduling
    - accounts: Connected accounts for platform selection
    - upcoming_posts: Recently scheduled posts
    - recommendations: AI-generated scheduling recommendations
    """
    service = get_hydration_service()
    return await service.get_narrative_builder_data()
