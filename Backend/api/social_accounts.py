"""
Social Accounts API Router
Provides endpoints for fetching connected social media accounts.
"""

from fastapi import APIRouter, Query
from typing import Optional, List
import logging

from services.blotato_api import BlotatoAPI

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/social", tags=["Social Accounts"])


@router.get("/accounts")
async def get_social_accounts(platform: Optional[str] = Query(default=None, description="Filter by platform")):
    """
    Get connected social media accounts.
    
    Args:
        platform: Optional platform filter (instagram, tiktok, twitter, etc.)
    
    Returns:
        List of connected accounts with id, platform, username
    """
    try:
        api = BlotatoAPI()
        accounts = await api.get_accounts(platform=platform)
        
        # Transform to consistent format
        result = []
        for acc in accounts:
            result.append({
                "id": acc.get("id"),
                "platform": acc.get("platform"),
                "username": acc.get("username") or acc.get("fullname"),
                "fullname": acc.get("fullname"),
                "profile_url": acc.get("profileUrl"),
                "avatar_url": acc.get("avatarUrl"),
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching social accounts: {e}", exc_info=True)
        # Return empty list instead of raising - frontend can handle empty state
        return []
