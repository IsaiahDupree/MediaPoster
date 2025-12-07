"""
Connected Accounts API Endpoints
Manages social media account connections and syncing
Phase 1: Multi-Platform Analytics Ingest
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import text, select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timedelta
import uuid

from database.connection import get_db, async_session_maker
from database.models import ConnectorConfig

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


# ==================== Request/Response Models ====================

class ConnectedAccount(BaseModel):
    """Connected account response model"""
    id: str
    platform: str
    handle: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    status: str  # 'connected', 'error', 'disconnected', 'needs_reauth'
    connection_method: str  # 'bloatato', 'rapidapi', 'scraper', 'oauth', 'manual'
    last_synced_at: Optional[str] = None
    follower_count: Optional[int] = None
    posts_count: Optional[int] = None
    error_message: Optional[str] = None


class ConnectAccountRequest(BaseModel):
    """Request to connect a new account"""
    platform: str
    connection_method: str  # 'bloatato', 'rapidapi', 'oauth', 'manual'
    credentials: Dict[str, Any]  # Platform-specific credentials
    username: Optional[str] = None
    account_id: Optional[str] = None


class SyncAccountRequest(BaseModel):
    """Request to sync account data"""
    account_id: str
    force_refresh: bool = False


# ==================== Endpoints ====================

@router.get("/", response_model=List[ConnectedAccount])
async def get_connected_accounts(
    platform: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all connected social media accounts
    
    Returns list of accounts with their connection status and last sync time
    """
    try:
        # Use async_session_maker if available, otherwise use db from dependency injection
        if async_session_maker:
            async with async_session_maker() as session:
                # Try to get from social_media_accounts first
                try:
                    result = await session.execute(text("""
                        SELECT 
                            id::text,
                            platform,
                            username as handle,
                            display_name,
                            profile_pic_url as avatar_url,
                            CASE 
                                WHEN is_active THEN 'connected'
                                WHEN connection_status = 'error' THEN 'error'
                                ELSE 'disconnected'
                            END as status,
                            connected_via as connection_method,
                            last_synced_at::text,
                            NULL as follower_count,
                            NULL as posts_count,
                            NULL as error_message
                        FROM social_media_accounts
                        WHERE 1=1
                    """ + (f" AND platform = '{platform}'" if platform else "")))
                    
                    accounts = result.fetchall()
                    
                    if accounts:
                        return [
                            ConnectedAccount(
                                id=str(row[0]),
                                platform=row[1],
                                handle=row[2] or '',
                                display_name=row[3],
                                avatar_url=row[4],
                                status=row[5] or 'disconnected',
                                connection_method=row[6] or 'manual',
                                last_synced_at=row[7],
                                follower_count=row[8],
                                posts_count=row[9],
                                error_message=row[10]
                            )
                            for row in accounts
                        ]
                except Exception:
                    # Table might not exist, fall through to connector_configs
                    pass
                
                # Fallback: Get from connector_configs
                result = await session.execute(
                    select(ConnectorConfig).where(
                        ConnectorConfig.is_enabled == True
                    )
                )
                configs = result.scalars().all()
                
                accounts_list = []
                for config in configs:
                    # Extract account info from config JSONB
                    config_data = config.config if isinstance(config.config, dict) else {}
                    
                    accounts_list.append(ConnectedAccount(
                        id=str(config.id),
                        platform=config.connector_type,
                        handle=config_data.get('username', config_data.get('handle', '')),
                        display_name=config_data.get('display_name'),
                        avatar_url=config_data.get('avatar_url'),
                        status='connected' if config.is_enabled else 'disconnected',
                        connection_method=config.connector_type,
                        last_synced_at=None,  # Would need to track this separately
                        follower_count=config_data.get('follower_count'),
                        posts_count=config_data.get('posts_count')
                    ))
                
                return accounts_list
        else:
            # Fallback: Use db from dependency injection if async_session_maker not available
            result = await db.execute(
                select(ConnectorConfig).where(
                    ConnectorConfig.is_enabled == True
                )
            )
            configs = result.scalars().all()
            
            accounts_list = []
            for config in configs:
                config_data = config.config if isinstance(config.config, dict) else {}
                accounts_list.append(ConnectedAccount(
                    id=str(config.id),
                    platform=config.connector_type,
                    handle=config_data.get('username', config_data.get('handle', '')),
                    display_name=config_data.get('display_name'),
                    avatar_url=config_data.get('avatar_url'),
                    status='connected' if config.is_enabled else 'disconnected',
                    connection_method=config.connector_type,
                    last_synced_at=None,
                    follower_count=config_data.get('follower_count'),
                    posts_count=config_data.get('posts_count')
                ))
            return accounts_list
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching accounts: {str(e)}")


@router.post("/connect")
async def connect_account(
    request: ConnectAccountRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Connect a new social media account
    
    Supports multiple connection methods:
    - bloatato: Use Blotato API
    - rapidapi: Use RapidAPI endpoints
    - oauth: Platform OAuth flow
    - manual: Manual entry
    """
    try:
        # Validate platform
        valid_platforms = [
            'instagram', 'tiktok', 'youtube', 'facebook', 'twitter',
            'threads', 'linkedin', 'pinterest', 'bluesky'
        ]
        if request.platform not in valid_platforms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid platform. Must be one of: {', '.join(valid_platforms)}"
            )
        
        # Create connector config
        config_data = {
            'username': request.username or request.credentials.get('username'),
            'account_id': request.account_id or request.credentials.get('account_id'),
            **request.credentials
        }
        
        # Use async_session_maker if available, otherwise use db from dependency injection
        if async_session_maker:
            async with async_session_maker() as session:
                # Check if account already exists
                existing = await session.execute(
                    select(ConnectorConfig).where(
                        ConnectorConfig.connector_type == request.platform,
                        ConnectorConfig.config['username'].astext == config_data.get('username', '')
                    )
                )
                
                if existing.scalar_one_or_none():
                    raise HTTPException(
                        status_code=400,
                        detail=f"Account already connected for {request.platform}"
                    )
                
                # Create new connector config
                test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")  # Placeholder until auth
                test_workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000000")  # Use test workspace
                connector = ConnectorConfig(
                    id=uuid.uuid4(),
                    user_id=test_user_id,
                    workspace_id=test_workspace_id,
                    connector_type=request.platform,
                    config=config_data,
                    is_enabled=True
                )
                
                session.add(connector)
                await session.commit()
                await session.refresh(connector)
                
                # Trigger initial sync in background
                background_tasks.add_task(sync_account_data, str(connector.id), request.platform)
                
                return {
                    "success": True,
                    "message": f"Account connected successfully",
                    "account_id": str(connector.id),
                    "platform": request.platform
                }
        else:
            # Fallback: Use db from dependency injection if async_session_maker not available
            # Check if account already exists
            existing = await db.execute(
                select(ConnectorConfig).where(
                    ConnectorConfig.connector_type == request.platform,
                    ConnectorConfig.config['username'].astext == config_data.get('username', '')
                )
            )
            
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=400,
                    detail=f"Account already connected for {request.platform}"
                )
            
            # Create new connector config
            test_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
            test_workspace_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
            connector = ConnectorConfig(
                id=uuid.uuid4(),
                user_id=test_user_id,
                workspace_id=test_workspace_id,
                connector_type=request.platform,
                config=config_data,
                is_enabled=True
            )
            
            db.add(connector)
            await db.commit()
            await db.refresh(connector)
            
            # Trigger initial sync in background
            background_tasks.add_task(sync_account_data, str(connector.id), request.platform)
            
            return {
                "success": True,
                "message": f"Account connected successfully",
                "account_id": str(connector.id),
                "platform": request.platform
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error connecting account: {str(e)}")


@router.post("/sync")
async def sync_account(
    request: SyncAccountRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync data for a connected account
    
    Triggers background sync of:
    - Follower count
    - Post metrics
    - Recent posts
    - Analytics data
    """
    try:
        # Use async_session_maker if available, otherwise use db from dependency injection
        if async_session_maker:
            async with async_session_maker() as session:
                # Get account
                result = await session.execute(
                    select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(request.account_id))
                )
                account = result.scalar_one_or_none()
                
                if not account:
                    raise HTTPException(status_code=404, detail="Account not found")
                
                # Trigger sync in background
                background_tasks.add_task(
                    sync_account_data,
                    request.account_id,
                    account.connector_type,
                    request.force_refresh
                )
                
                return {
                    "success": True,
                    "message": "Sync started",
                    "account_id": request.account_id
                }
        else:
            # Fallback: Use db from dependency injection
            result = await db.execute(
                select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(request.account_id))
            )
            account = result.scalar_one_or_none()
            
            if not account:
                raise HTTPException(status_code=404, detail="Account not found")
            
            # Trigger sync in background
            background_tasks.add_task(
                sync_account_data,
                request.account_id,
                account.connector_type,
                request.force_refresh
            )
            
            return {
                "success": True,
                "message": "Sync started",
                "account_id": request.account_id
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error syncing account: {str(e)}")


@router.get("/status")
async def get_accounts_status(db: AsyncSession = Depends(get_db)):
    """
    Get overall accounts status
    
    Returns:
    - Total connected accounts
    - Accounts per platform
    - Last sync times
    - Data health indicator
    """
    try:
        # Use async_session_maker if available, otherwise use db from dependency injection
        if async_session_maker:
            async with async_session_maker() as session:
                # Get all accounts
                result = await session.execute(
                    select(ConnectorConfig).where(ConnectorConfig.is_enabled == True)
                )
                accounts = result.scalars().all()
        else:
            # Fallback: Use db from dependency injection
            result = await db.execute(
                select(ConnectorConfig).where(ConnectorConfig.is_enabled == True)
            )
            accounts = result.scalars().all()
        
        # Count by platform
        platform_counts = {}
        for account in accounts:
            platform = account.connector_type
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
        
        # Get last sync times (would need to track this)
        last_syncs = {}
        
        return {
            "total_accounts": len(accounts),
            "platforms_connected": len(platform_counts),
            "platform_breakdown": platform_counts,
            "last_syncs": last_syncs,
            "data_health": {
                "connected_platforms": len(platform_counts),
                "total_platforms_available": 9,
                "status": "good" if len(platform_counts) >= 6 else "needs_attention"
            }
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


# ==================== Background Tasks ====================

async def sync_account_data(account_id: str, platform: str, force_refresh: bool = False):
    """
    Background task to sync account data
    
    This will:
    1. Fetch latest metrics from platform API
    2. Update account record
    3. Store metrics in analytics tables
    """
    from loguru import logger
    from sqlalchemy import select
    from database.models import ConnectorConfig
    
    logger.info(f"Syncing account {account_id} for platform {platform}")
    
    try:
        async with async_session_maker() as session:
            # Get account config
            result = await session.execute(
                select(ConnectorConfig).where(ConnectorConfig.id == uuid.UUID(account_id))
            )
            account = result.scalar_one_or_none()
            
            if not account:
                logger.error(f"Account {account_id} not found")
                return
            
            config = account.config if isinstance(account.config, dict) else {}
            username = config.get('username') or config.get('handle')
            account_id_external = config.get('account_id')
            
            # Platform-specific sync
            if platform == 'youtube':
                await _sync_youtube_account(session, account, username, account_id_external)
            elif platform in ['instagram', 'facebook', 'threads']:
                await _sync_meta_account(session, account, platform, username, account_id_external)
            elif platform == 'tiktok':
                await _sync_tiktok_account(session, account, username, account_id_external)
            elif platform in ['twitter', 'linkedin', 'pinterest', 'bluesky']:
                await _sync_rapidapi_account(session, account, platform, username)
            else:
                logger.warning(f"Unsupported platform for sync: {platform}")
            
            # Update last_synced_at
            await session.execute(
                text("""
                    UPDATE connector_configs
                    SET updated_at = NOW(),
                        config = jsonb_set(config, '{last_synced_at}', to_jsonb(NOW()::text))
                    WHERE id = :account_id
                """),
                {"account_id": account_id}
            )
            await session.commit()
        
        logger.success(f"Account {account_id} synced successfully")
        
    except Exception as e:
        logger.error(f"Error syncing account {account_id}: {e}")
        # Update error status
        async with async_session_maker() as session:
            await session.execute(
                text("""
                    UPDATE connector_configs
                    SET config = jsonb_set(config, '{last_error}', :error::jsonb)
                    WHERE id = :account_id
                """),
                {"account_id": account_id, "error": f'"{str(e)}"'}
            )
            await session.commit()


async def _sync_youtube_account(session, account, username: str, channel_id: str):
    """Sync YouTube account data"""
    from services.youtube_analytics import YouTubeAnalytics
    from loguru import logger
    
    try:
        analytics = YouTubeAnalytics()
        
        # Get channel ID from username or use provided
        if not channel_id and username:
            # Try to resolve channel ID from username
            # For now, assume username is channel ID or custom URL
            channel_id = username.replace('@', '').replace('youtube.com/c/', '').replace('youtube.com/channel/', '')
        
        if not channel_id:
            logger.warning(f"No channel ID for YouTube account {username}")
            return
        
        # Get channel info
        channel_info = await analytics.get_channel_info(channel_id)
        if not channel_info:
            logger.warning(f"Could not fetch YouTube channel info for {channel_id}")
            return
        
        # Upsert into social_media_accounts
        await session.execute(
            text("""
                INSERT INTO social_media_accounts (
                    platform, username, display_name, profile_pic_url,
                    followers_count, posts_count, total_views,
                    last_fetched_at, is_active
                )
                VALUES (
                    'youtube', :username, :display_name, :thumbnail_url,
                    :subscriber_count, :video_count, :view_count,
                    NOW(), TRUE
                )
                ON CONFLICT (platform, username)
                DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    profile_pic_url = EXCLUDED.profile_pic_url,
                    followers_count = EXCLUDED.followers_count,
                    posts_count = EXCLUDED.posts_count,
                    total_views = EXCLUDED.total_views,
                    last_fetched_at = NOW()
            """),
            {
                'username': username or channel_info.get('custom_url', ''),
                'display_name': channel_info.get('title'),
                'thumbnail_url': channel_info.get('thumbnail_url'),
                'subscriber_count': channel_info.get('subscriber_count', 0),
                'video_count': channel_info.get('video_count', 0),
                'view_count': channel_info.get('view_count', 0)
            }
        )
        
        # Create analytics snapshot
        await session.execute(
            text("""
                INSERT INTO social_media_analytics_snapshots (
                    social_account_id, snapshot_date,
                    followers_count, posts_count, total_views
                )
                SELECT 
                    id, CURRENT_DATE,
                    :subscriber_count, :video_count, :view_count
                FROM social_media_accounts
                WHERE platform = 'youtube' AND username = :username
                ON CONFLICT (social_account_id, snapshot_date)
                DO UPDATE SET
                    followers_count = EXCLUDED.followers_count,
                    posts_count = EXCLUDED.posts_count,
                    total_views = EXCLUDED.total_views
            """),
            {
                'username': username or channel_info.get('custom_url', ''),
                'subscriber_count': channel_info.get('subscriber_count', 0),
                'video_count': channel_info.get('video_count', 0),
                'view_count': channel_info.get('view_count', 0)
            }
        )
        
        logger.info(f"YouTube account {username} synced: {channel_info.get('subscriber_count', 0)} subscribers")
        
    except Exception as e:
        logger.error(f"Error syncing YouTube account: {e}")
        raise


async def _sync_meta_account(session, account, platform: str, username: str, account_id: str):
    """Sync Meta platform account (Instagram, Facebook, Threads)"""
    from loguru import logger
    import os
    
    # Check for Blotato integration first
    blotato_key = os.getenv('BLOTATO_API_KEY')
    if blotato_key:
        # Use Blotato API
        logger.info(f"Syncing {platform} via Blotato")
        # TODO: Implement Blotato sync
        pass
    else:
        # Fallback to RapidAPI
        await _sync_rapidapi_account(session, account, platform, username)


async def _sync_tiktok_account(session, account, username: str, account_id: str):
    """Sync TikTok account"""
    from loguru import logger
    import os
    
    # Check for Blotato integration first
    blotato_key = os.getenv('BLOTATO_API_KEY')
    if blotato_key:
        logger.info(f"Syncing TikTok via Blotato")
        # TODO: Implement Blotato sync
        pass
    else:
        # Fallback to RapidAPI
        await _sync_rapidapi_account(session, account, 'tiktok', username)


async def _sync_rapidapi_account(session, account, platform: str, username: str):
    """Sync account using RapidAPI scraper"""
    from services.rapidapi_scraper import RapidAPIScraper
    from loguru import logger
    
    try:
        if not username:
            logger.warning(f"No username provided for {platform} account")
            return
        
        scraper = RapidAPIScraper()
        
        # Scrape profile data
        profile_data = await scraper.scrape_platform_profile(platform, username)
        
        if not profile_data:
            logger.warning(f"Could not scrape {platform} profile for {username}")
            return
        
        # Upsert into social_media_accounts
        await session.execute(
            text("""
                INSERT INTO social_media_accounts (
                    platform, username, display_name, bio, profile_pic_url,
                    followers_count, posts_count, is_verified,
                    last_fetched_at, is_active
                )
                VALUES (
                    :platform, :username, :display_name, :bio, :profile_pic_url,
                    :follower_count, :posts_count, :is_verified,
                    NOW(), TRUE
                )
                ON CONFLICT (platform, username)
                DO UPDATE SET
                    display_name = EXCLUDED.display_name,
                    bio = EXCLUDED.bio,
                    profile_pic_url = EXCLUDED.profile_pic_url,
                    followers_count = EXCLUDED.followers_count,
                    posts_count = EXCLUDED.posts_count,
                    is_verified = EXCLUDED.is_verified,
                    last_fetched_at = NOW()
            """),
            {
                'platform': platform,
                'username': username,
                'display_name': profile_data.get('display_name'),
                'bio': profile_data.get('bio'),
                'profile_pic_url': profile_data.get('profile_pic_url'),
                'follower_count': profile_data.get('follower_count', 0),
                'posts_count': profile_data.get('posts_count', 0),
                'is_verified': profile_data.get('is_verified', False)
            }
        )
        
        # Create analytics snapshot
        await session.execute(
            text("""
                INSERT INTO social_media_analytics_snapshots (
                    social_account_id, snapshot_date,
                    followers_count, posts_count
                )
                SELECT 
                    id, CURRENT_DATE,
                    :follower_count, :posts_count
                FROM social_media_accounts
                WHERE platform = :platform AND username = :username
                ON CONFLICT (social_account_id, snapshot_date)
                DO UPDATE SET
                    followers_count = EXCLUDED.followers_count,
                    posts_count = EXCLUDED.posts_count
            """),
            {
                'platform': platform,
                'username': username,
                'follower_count': profile_data.get('follower_count', 0),
                'posts_count': profile_data.get('posts_count', 0)
            }
        )
        
        logger.info(f"{platform} account {username} synced: {profile_data.get('follower_count', 0)} followers")
        
    except Exception as e:
        logger.error(f"Error syncing {platform} account via RapidAPI: {e}")
        raise

