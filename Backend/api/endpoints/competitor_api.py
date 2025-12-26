"""
Competitor Research API Endpoints
Manage tracked competitor accounts and fetch their content.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
from loguru import logger

from services.competitor_service import get_competitor_service

router = APIRouter(prefix="/api/competitors", tags=["Competitor Research"])


class AddAccountRequest(BaseModel):
    """Request to add a competitor account"""
    username: str
    priority: int = 1  # 1=high, 2=medium, 3=low


class SyncResponse(BaseModel):
    """Response from sync operation"""
    username: str
    reels_fetched: int
    posts_fetched: int
    videos_downloaded: int
    errors: List[str]


@router.get("/health")
async def health_check():
    """Health check for competitor service"""
    service = get_competitor_service()
    accounts = service.get_stored_accounts()
    return {
        "status": "healthy",
        "service": "competitor-research",
        "tracked_accounts": len(accounts),
        "storage_dir": str(service.storage_dir)
    }


@router.get("/accounts")
async def list_accounts():
    """List all tracked competitor accounts"""
    service = get_competitor_service()
    accounts = service.get_stored_accounts()
    return {
        "count": len(accounts),
        "accounts": accounts
    }


@router.post("/accounts")
async def add_account(request: AddAccountRequest):
    """
    Add a new competitor account to track.
    Fetches initial profile info.
    """
    service = get_competitor_service()
    
    try:
        profile = await service.fetch_account_info(request.username)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"Could not find Instagram account: @{request.username}"
            )
        
        return {
            "status": "added",
            "account": profile.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/accounts/{username}/sync")
async def sync_account(username: str, background_tasks: BackgroundTasks):
    """
    Sync all content from a competitor account.
    Runs in background for large accounts.
    """
    service = get_competitor_service()
    
    try:
        # Run sync
        results = await service.sync_account(username)
        
        return {
            "status": "synced",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error syncing account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/profile")
async def get_account_profile(username: str):
    """Get profile info for a competitor account"""
    service = get_competitor_service()
    
    try:
        profile = await service.fetch_account_info(username)
        
        if not profile:
            raise HTTPException(status_code=404, detail="Account not found")
        
        return profile.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/reels")
async def get_account_reels(username: str, count: int = 50):
    """Get reels from a competitor account"""
    service = get_competitor_service()
    
    try:
        reels = await service.fetch_user_reels(username, count)
        
        return {
            "count": len(reels),
            "reels": [r.model_dump() for r in reels]
        }
        
    except Exception as e:
        logger.error(f"Error fetching reels: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accounts/{username}/posts")
async def get_account_posts(username: str, count: int = 50):
    """Get posts from a competitor account"""
    service = get_competitor_service()
    
    try:
        posts = await service.fetch_user_posts(username, count)
        
        return {
            "count": len(posts),
            "posts": [p.model_dump() for p in posts]
        }
        
    except Exception as e:
        logger.error(f"Error fetching posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))
