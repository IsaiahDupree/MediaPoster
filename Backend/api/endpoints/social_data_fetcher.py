"""
Social Data Fetcher API
Triggers RapidAPISocialFetcher to populate frontend pages with real data
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import List, Optional
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import os
import asyncio
from loguru import logger

from services.rapidapi_social_fetcher import RapidAPISocialFetcher, Platform, SocialAccount
from services.social_analytics_service import SocialAnalyticsService

router = APIRouter(prefix="/api/social-data", tags=["Social Data Fetcher"])

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:54322/postgres")
engine = create_engine(DATABASE_URL)


class FetchRequest(BaseModel):
    platforms: Optional[List[str]] = None  # If None, fetch all
    force_refresh: bool = False


class FetchStatus(BaseModel):
    status: str
    message: str
    accounts_queued: int
    estimated_time_seconds: int


@router.post("/fetch-all", response_model=FetchStatus)
async def trigger_social_data_fetch(
    request: FetchRequest,
    background_tasks: BackgroundTasks
):
    """
    Trigger RapidAPISocialFetcher to fetch data for all accounts
    This populates:
    - /accounts page (account metrics)
    - /social-metrics page (engagement data)
    - /analytics/content page (post performance)
    - /trends page (trending topics)
    """
    try:
        # Get accounts from config (not database)
        from config.blotato_accounts import BLOTATO_ACCOUNTS
        
        accounts_to_fetch = []
        for account in BLOTATO_ACCOUNTS:
            # Filter by platform if specified
            if request.platforms and account.platform not in request.platforms:
                continue
            
            if account.is_active:
                accounts_to_fetch.append({
                    'platform': account.platform,
                    'username': account.username,
                    'blotato_id': account.blotato_id,
                    'fullname': account.display_name or account.username
                })
        
        if not accounts_to_fetch:
            return FetchStatus(
                status="no_accounts",
                message="No accounts found to fetch",
                accounts_queued=0,
                estimated_time_seconds=0
            )
        
        # Queue background task
        background_tasks.add_task(
            fetch_social_data_background,
            accounts_to_fetch,
            request.force_refresh
        )
        
        # Estimate time (3 seconds per account for API calls)
        estimated_time = len(accounts_to_fetch) * 3
        
        return FetchStatus(
            status="queued",
            message=f"Fetching data for {len(accounts_to_fetch)} accounts",
            accounts_queued=len(accounts_to_fetch),
            estimated_time_seconds=estimated_time
        )
        
    except Exception as e:
        logger.error(f"Error triggering social data fetch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def fetch_social_data_background(accounts: List[dict], force_refresh: bool):
    """
    Background task to fetch social data from RapidAPI
    Wrapped in global try-except to prevent crashes
    """
    fetcher = RapidAPISocialFetcher()
    analytics_service = SocialAnalyticsService()
    
    logger.info(f"Starting social data fetch for {len(accounts)} accounts")
    
    for account_data in accounts:
        try:
            platform_str = account_data['platform']
            username = account_data['username']
            
            # Skip if recently fetched (unless force_refresh)
            if not force_refresh:
                conn = engine.connect()
                check_query = text("""
                    SELECT last_fetched_at
                    FROM social_media_accounts
                    WHERE platform = :platform AND username = :username
                """)
                result = conn.execute(check_query, {
                    'platform': platform_str,
                    'username': username
                }).fetchone()
                conn.close()
                
                if result and result[0]:
                    last_fetched = result[0]
                    if isinstance(last_fetched, str):
                        last_fetched = datetime.fromisoformat(last_fetched.replace('Z', '+00:00'))
                    
                    # Skip if fetched within last hour
                    if datetime.now() - last_fetched < timedelta(hours=1):
                        logger.info(f"Skipping {platform_str}/@{username} - recently fetched")
                        continue
            
            # Map platform string to enum
            try:
                platform = Platform(platform_str.lower())
            except ValueError:
                logger.warning(f"Unknown platform: {platform_str}")
                continue
            
            # Create SocialAccount object
            social_account = SocialAccount(
                platform=platform,
                username=username,
                display_name=account_data.get('fullname')
            )
            
            # Fetch analytics from RapidAPI using platform-specific methods
            logger.info(f"Fetching {platform_str}/@{username} from RapidAPI...")
            
            # Call the appropriate fetch method based on platform
            if platform == Platform.TIKTOK:
                analytics = await fetcher.fetch_tiktok_analytics(username)
            elif platform == Platform.INSTAGRAM:
                analytics = await fetcher.fetch_instagram_analytics(username)
            elif platform == Platform.YOUTUBE:
                analytics = await fetcher.fetch_youtube_analytics(username)
            elif platform == Platform.TWITTER:
                analytics = await fetcher.fetch_twitter_analytics(username)
            elif platform == Platform.THREADS:
                analytics = await fetcher.fetch_threads_analytics(username)
            elif platform == Platform.LINKEDIN:
                analytics = await fetcher.fetch_linkedin_analytics(username)
            elif platform == Platform.PINTEREST:
                analytics = await fetcher.fetch_pinterest_analytics(username)
            elif platform == Platform.FACEBOOK:
                analytics = await fetcher.fetch_facebook_analytics(username)
            elif platform == Platform.BLUESKY:
                analytics = await fetcher.fetch_bluesky_analytics(username)
            else:
                logger.warning(f"No fetch method for platform: {platform_str}")
                continue
            
            if analytics:
                # Save to database - update account with metrics
                account_id = await analytics_service.get_or_create_account(
                    platform=platform_str,
                    username=username,
                    profile_data={
                        'full_name': analytics.bio or account_data.get('fullname'),
                        'bio': analytics.bio,
                        'profile_pic_url': analytics.profile_pic_url,
                        'is_verified': analytics.is_verified,
                        'is_business': False
                    }
                )
                
                # Update account metrics directly in social_media_accounts table
                conn = engine.connect()
                try:
                    conn.execute(text("""
                        UPDATE social_media_accounts SET
                            followers_count = :followers,
                            posts_count = :posts,
                            total_views = :views,
                            updated_at = NOW(),
                            last_fetched_at = NOW()
                        WHERE id = :account_id
                    """), {
                        'followers': analytics.followers_count or 0,
                        'posts': analytics.posts_count or 0,
                        'views': analytics.total_views or 0,
                        'account_id': account_id
                    })
                    conn.commit()
                finally:
                    conn.close()
                
                # Save analytics snapshot for historical tracking
                await analytics_service.save_analytics_snapshot(
                    account_id=account_id,
                    analytics_data={
                        'followers_count': analytics.followers_count,
                        'following_count': analytics.following_count,
                        'posts_count': analytics.posts_count,
                        'total_views': analytics.total_views,
                        'total_likes': analytics.total_likes,
                        'total_comments': analytics.total_comments,
                        'total_shares': analytics.total_shares,
                        'engagement_rate': analytics.engagement_rate
                    }
                )
                
                logger.success(f"✅ Fetched {platform_str}/@{username}: {analytics.followers_count} followers, {analytics.posts_count} posts")
            else:
                logger.warning(f"No analytics returned for {platform_str}/@{username}")
            
            # Rate limiting - wait 1 second between requests
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.error(f"Error fetching {account_data['platform']}/@{account_data['username']}: {e}")
            continue
    
    logger.info(f"Social data fetch complete for {len(accounts)} accounts")


@router.get("/fetch-status")
async def get_fetch_status():
    """
    Get status of social data fetching
    Returns last fetch times and account counts
    """
    conn = engine.connect()
    
    try:
        # Get overall stats
        stats_query = text("""
            SELECT 
                COUNT(*) as total_accounts,
                COUNT(*) FILTER (WHERE last_fetched_at > NOW() - INTERVAL '1 hour') as recently_fetched,
                COUNT(*) FILTER (WHERE last_fetched_at > NOW() - INTERVAL '24 hours') as fetched_today,
                MAX(last_fetched_at) as last_fetch_time
            FROM social_media_accounts
            WHERE is_active = TRUE
        """)
        
        stats = conn.execute(stats_query).fetchone()
        
        # Get platform breakdown
        platform_query = text("""
            SELECT 
                platform,
                COUNT(*) as account_count,
                MAX(last_fetched_at) as last_fetch
            FROM social_media_accounts
            WHERE is_active = TRUE
            GROUP BY platform
            ORDER BY account_count DESC
        """)
        
        platforms = conn.execute(platform_query).fetchall()
        
        return {
            'total_accounts': stats[0] if stats else 0,
            'recently_fetched': stats[1] if stats else 0,
            'fetched_today': stats[2] if stats else 0,
            'last_fetch_time': str(stats[3]) if stats and stats[3] else None,
            'platforms': [
                {
                    'platform': row[0],
                    'account_count': row[1],
                    'last_fetch': str(row[2]) if row[2] else None
                }
                for row in platforms
            ]
        }
        
    finally:
        conn.close()


@router.post("/fetch-platform/{platform}")
async def fetch_platform_data(
    platform: str,
    background_tasks: BackgroundTasks,
    force_refresh: bool = False
):
    """
    Fetch data for a specific platform only
    """
    return await trigger_social_data_fetch(
        FetchRequest(platforms=[platform], force_refresh=force_refresh),
        background_tasks
    )
