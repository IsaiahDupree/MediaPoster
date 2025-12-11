"""
Social Media Accounts Management API
Manages connected social accounts and fetches live analytics via RapidAPI
"""
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy import create_engine, text
import os
import logging

from services.rapidapi_social_fetcher import (
    RapidAPISocialFetcher,
    SocialAccount,
    Platform,
    get_social_fetcher
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Social Accounts"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
engine = create_engine(DATABASE_URL)


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ConnectedAccountResponse(BaseModel):
    id: int
    platform: str
    username: str
    display_name: Optional[str]
    profile_pic_url: Optional[str]
    followers_count: int
    following_count: int
    posts_count: int
    total_views: int
    total_likes: int
    engagement_rate: float
    is_verified: bool
    is_active: bool
    last_fetched_at: Optional[str]


class AddAccountRequest(BaseModel):
    platform: str
    username: str
    account_id: Optional[str] = None
    profile_url: Optional[str] = None


class PlatformSummary(BaseModel):
    platform: str
    account_count: int
    total_followers: int
    total_views: int
    total_likes: int
    avg_engagement_rate: float


class LiveAnalyticsResponse(BaseModel):
    platform: str
    username: str
    followers_count: int
    following_count: int
    posts_count: int
    total_views: int
    total_likes: int
    total_comments: int
    engagement_rate: float
    is_verified: bool
    bio: str
    profile_pic_url: str
    fetched_at: str


# ============================================================================
# HELPER: Initialize accounts from environment variables
# ============================================================================

def get_env_accounts() -> List[dict]:
    """
    Load social media accounts from environment variables.
    Returns list of {platform, username} dicts.
    """
    accounts = []
    
    # Instagram
    instagram_users = os.getenv("INSTAGRAM_USERNAMES", "")
    for username in instagram_users.split(","):
        username = username.strip()
        if username:
            accounts.append({"platform": "instagram", "username": username})
    
    # TikTok
    tiktok_users = os.getenv("TIKTOK_USERNAMES", "")
    for username in tiktok_users.split(","):
        username = username.strip()
        if username:
            accounts.append({"platform": "tiktok", "username": username})
    
    # Twitter/X
    twitter_users = os.getenv("TWITTER_USERNAMES", "")
    for username in twitter_users.split(","):
        username = username.strip()
        if username:
            accounts.append({"platform": "twitter", "username": username})
    
    # YouTube
    youtube_users = os.getenv("YOUTUBE_USERNAMES", "")
    for username in youtube_users.split(","):
        username = username.strip()
        if username:
            accounts.append({"platform": "youtube", "username": username})
    
    # Threads
    threads_users = os.getenv("THREADS_USERNAMES", "")
    for username in threads_users.split(","):
        username = username.strip()
        if username:
            accounts.append({"platform": "threads", "username": username})
    
    # Pinterest
    pinterest_users = os.getenv("PINTEREST_USERNAMES", "")
    for username in pinterest_users.split(","):
        username = username.strip()
        if username:
            accounts.append({"platform": "pinterest", "username": username})
    
    # Facebook
    facebook_pages = os.getenv("FACEBOOK_PAGE_NAMES", "")
    for page in facebook_pages.split(","):
        page = page.strip()
        if page:
            accounts.append({"platform": "facebook", "username": page})
    
    # Bluesky
    bluesky_users = os.getenv("BLUESKY_USERNAMES", "")
    for username in bluesky_users.split(","):
        username = username.strip()
        if username:
            accounts.append({"platform": "bluesky", "username": username})
    
    return accounts


# ============================================================================
# ACCOUNT MANAGEMENT ENDPOINTS
# ============================================================================

@router.post("/accounts/sync-from-env")
async def sync_accounts_from_env():
    """
    Sync accounts from environment variables to the database.
    Creates any accounts that don't already exist.
    """
    conn = engine.connect()
    
    try:
        env_accounts = get_env_accounts()
        added = 0
        existing = 0
        
        for account in env_accounts:
            # Check if exists
            check = conn.execute(text("""
                SELECT id FROM social_media_accounts 
                WHERE platform = :platform AND username = :username
            """), account).fetchone()
            
            if check:
                existing += 1
            else:
                # Insert
                conn.execute(text("""
                    INSERT INTO social_media_accounts (platform, username, is_active)
                    VALUES (:platform, :username, TRUE)
                """), account)
                added += 1
        
        conn.commit()
        
        return {
            "message": "Sync complete",
            "added": added,
            "existing": existing,
            "total_env_accounts": len(env_accounts)
        }
        
    finally:
        conn.close()


@router.get("/accounts", response_model=List[ConnectedAccountResponse])
async def get_connected_accounts(
    platform: Optional[str] = None,
    active_only: bool = True
):
    """
    Get all connected social media accounts
    Supports filtering by platform
    """
    conn = engine.connect()
    
    try:
        query = """
            SELECT 
                id, platform, username, display_name, profile_pic_url,
                COALESCE(followers_count, 0) as followers_count,
                COALESCE(following_count, 0) as following_count,
                COALESCE(posts_count, 0) as posts_count,
                COALESCE(total_views, 0) as total_views,
                COALESCE(total_likes, 0) as total_likes,
                COALESCE(engagement_rate, 0) as engagement_rate,
                COALESCE(is_verified, FALSE) as is_verified,
                is_active,
                last_fetched_at
            FROM social_media_accounts
            WHERE 1=1
        """
        
        params = {}
        if platform:
            query += " AND platform = :platform"
            params["platform"] = platform.lower()
        
        if active_only:
            query += " AND is_active = TRUE"
        
        query += " ORDER BY platform, followers_count DESC"
        
        results = conn.execute(text(query), params).fetchall()
        
        return [
            ConnectedAccountResponse(
                id=row[0],
                platform=row[1],
                username=row[2],
                display_name=row[3],
                profile_pic_url=row[4],
                followers_count=row[5],
                following_count=row[6],
                posts_count=row[7],
                total_views=row[8],
                total_likes=row[9],
                engagement_rate=round(float(row[10]), 2),
                is_verified=row[11],
                is_active=row[12],
                last_fetched_at=str(row[13]) if row[13] else None
            )
            for row in results
        ]
        
    finally:
        conn.close()


@router.post("/accounts", response_model=dict)
async def add_account(request: AddAccountRequest):
    """
    Add a new social media account to track
    """
    conn = engine.connect()
    
    try:
        # Check if account already exists
        check_query = text("""
            SELECT id FROM social_media_accounts
            WHERE platform = :platform AND username = :username
        """)
        
        existing = conn.execute(check_query, {
            "platform": request.platform.lower(),
            "username": request.username
        }).fetchone()
        
        if existing:
            return {"message": "Account already exists", "account_id": existing[0]}
        
        # Insert new account
        insert_query = text("""
            INSERT INTO social_media_accounts (
                platform, username, external_account_id, profile_url, is_active
            ) VALUES (
                :platform, :username, :account_id, :profile_url, TRUE
            )
            RETURNING id
        """)
        
        result = conn.execute(insert_query, {
            "platform": request.platform.lower(),
            "username": request.username,
            "account_id": request.account_id,
            "profile_url": request.profile_url
        }).fetchone()
        
        conn.commit()
        
        return {"message": "Account added successfully", "account_id": result[0]}
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Error adding account: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        conn.close()


@router.post("/accounts/{account_id}/sync")
async def sync_account_endpoint(account_id: int, force_refresh: bool = False):
    """
    Sync/refresh account data from the platform API
    For RapidAPI platforms, this consumes monthly API calls
    """
    from api.endpoints.accounts import sync_account_data
    from loguru import logger
    
    try:
        # Get account platform
        conn = engine.connect()
        result = conn.execute(text("""
            SELECT platform FROM social_media_accounts WHERE id = :account_id
        """), {"account_id": account_id})
        account = result.fetchone()
        conn.close()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        platform = account[0]
        
        # Sync account data
        await sync_account_data(str(account_id), platform, force_refresh)
        
        return {
            "message": "Account synced successfully",
            "account_id": account_id,
            "platform": platform
        }
    except Exception as e:
        logger.error(f"Error syncing account {account_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/accounts/{account_id}")
async def remove_account(account_id: int):
    """
    Remove a social media account from tracking
    """
    conn = engine.connect()
    
    try:
        query = text("""
            UPDATE social_media_accounts
            SET is_active = FALSE, updated_at = NOW()
            WHERE id = :account_id
        """)
        
        conn.execute(query, {"account_id": account_id})
        conn.commit()
        
        return {"message": "Account deactivated successfully"}
        
    finally:
        conn.close()


# ============================================================================
# LIVE ANALYTICS FETCH ENDPOINTS
# ============================================================================

@router.get("/accounts/{account_id}/fetch-live", response_model=LiveAnalyticsResponse)
async def fetch_live_analytics(account_id: int):
    """
    Fetch live analytics for a specific account via RapidAPI
    Updates the database with fresh data
    """
    conn = engine.connect()
    
    try:
        # Get account details
        query = text("""
            SELECT platform, username, external_account_id, profile_url
            FROM social_media_accounts
            WHERE id = :account_id
        """)
        
        account = conn.execute(query, {"account_id": account_id}).fetchone()
        
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
        
        platform_str, username, external_id, profile_url = account
        
        # Map to Platform enum
        try:
            platform = Platform(platform_str)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform_str}")
        
        # Create SocialAccount for fetcher
        social_account = SocialAccount(
            platform=platform,
            username=username,
            account_id=external_id,
            profile_url=profile_url
        )
        
        # Fetch live data
        fetcher = get_social_fetcher()
        results = await fetcher.fetch_all_accounts([social_account])
        
        if not results:
            raise HTTPException(status_code=500, detail="Failed to fetch analytics")
        
        analytics = results[0]
        
        # Update database with fresh data
        update_query = text("""
            UPDATE social_media_accounts
            SET 
                display_name = COALESCE(:display_name, display_name),
                bio = COALESCE(:bio, bio),
                profile_pic_url = COALESCE(:profile_pic_url, profile_pic_url),
                followers_count = :followers_count,
                following_count = :following_count,
                posts_count = :posts_count,
                total_views = :total_views,
                total_likes = :total_likes,
                engagement_rate = :engagement_rate,
                is_verified = :is_verified,
                last_fetched_at = NOW(),
                updated_at = NOW()
            WHERE id = :account_id
        """)
        
        conn.execute(update_query, {
            "account_id": account_id,
            "display_name": analytics.bio[:100] if analytics.bio else None,
            "bio": analytics.bio,
            "profile_pic_url": analytics.profile_pic_url,
            "followers_count": analytics.followers_count,
            "following_count": analytics.following_count,
            "posts_count": analytics.posts_count,
            "total_views": analytics.total_views,
            "total_likes": analytics.total_likes,
            "engagement_rate": analytics.engagement_rate,
            "is_verified": analytics.is_verified
        })
        
        conn.commit()
        
        return LiveAnalyticsResponse(
            platform=analytics.platform.value,
            username=analytics.username,
            followers_count=analytics.followers_count,
            following_count=analytics.following_count,
            posts_count=analytics.posts_count,
            total_views=analytics.total_views,
            total_likes=analytics.total_likes,
            total_comments=analytics.total_comments,
            engagement_rate=analytics.engagement_rate,
            is_verified=analytics.is_verified,
            bio=analytics.bio,
            profile_pic_url=analytics.profile_pic_url,
            fetched_at=datetime.now().isoformat()
        )
        
    finally:
        conn.close()


@router.post("/accounts/fetch-all")
async def fetch_all_accounts_live(background_tasks: BackgroundTasks):
    """
    Trigger a background fetch of all active accounts
    """
    background_tasks.add_task(background_fetch_all_accounts)
    return {"message": "Background fetch started", "status": "processing"}


async def background_fetch_all_accounts():
    """Background task to fetch all accounts"""
    conn = engine.connect()
    
    try:
        # Get all active accounts
        query = text("""
            SELECT id, platform, username, external_account_id, profile_url
            FROM social_media_accounts
            WHERE is_active = TRUE
        """)
        
        accounts = conn.execute(query).fetchall()
        
        fetcher = get_social_fetcher()
        
        for account in accounts:
            account_id, platform_str, username, external_id, profile_url = account
            
            try:
                platform = Platform(platform_str)
                
                social_account = SocialAccount(
                    platform=platform,
                    username=username,
                    account_id=external_id,
                    profile_url=profile_url
                )
                
                results = await fetcher.fetch_all_accounts([social_account])
                
                if results:
                    analytics = results[0]
                    
                    update_query = text("""
                        UPDATE social_media_accounts
                        SET 
                            followers_count = :followers_count,
                            following_count = :following_count,
                            posts_count = :posts_count,
                            total_views = :total_views,
                            total_likes = :total_likes,
                            engagement_rate = :engagement_rate,
                            is_verified = :is_verified,
                            last_fetched_at = NOW(),
                            updated_at = NOW()
                        WHERE id = :account_id
                    """)
                    
                    conn.execute(update_query, {
                        "account_id": account_id,
                        "followers_count": analytics.followers_count,
                        "following_count": analytics.following_count,
                        "posts_count": analytics.posts_count,
                        "total_views": analytics.total_views,
                        "total_likes": analytics.total_likes,
                        "engagement_rate": analytics.engagement_rate,
                        "is_verified": analytics.is_verified
                    })
                    
                    conn.commit()
                    logger.info(f"Updated {platform_str}/@{username}")
                    
            except Exception as e:
                logger.error(f"Error fetching {platform_str}/@{username}: {e}")
                
    finally:
        conn.close()


# ============================================================================
# PLATFORM SUMMARY ENDPOINTS
# ============================================================================

@router.get("/platforms/summary", response_model=List[PlatformSummary])
async def get_platform_summary():
    """
    Get summary metrics grouped by platform
    """
    conn = engine.connect()
    
    try:
        query = text("""
            SELECT 
                platform,
                COUNT(*) as account_count,
                COALESCE(SUM(followers_count), 0) as total_followers,
                COALESCE(SUM(total_views), 0) as total_views,
                COALESCE(SUM(total_likes), 0) as total_likes,
                COALESCE(AVG(engagement_rate), 0) as avg_engagement_rate
            FROM social_media_accounts
            WHERE is_active = TRUE
            GROUP BY platform
            ORDER BY total_followers DESC
        """)
        
        results = conn.execute(query).fetchall()
        
        return [
            PlatformSummary(
                platform=row[0],
                account_count=row[1],
                total_followers=row[2],
                total_views=row[3],
                total_likes=row[4],
                avg_engagement_rate=round(float(row[5]), 2)
            )
            for row in results
        ]
        
    finally:
        conn.close()


@router.get("/platforms/{platform}/accounts", response_model=List[ConnectedAccountResponse])
async def get_platform_accounts(platform: str):
    """
    Get all accounts for a specific platform
    """
    return await get_connected_accounts(platform=platform, active_only=True)
