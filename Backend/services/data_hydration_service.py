"""
Data Hydration Service
Centralized system for fetching, storing, and serving social media data across all pages.

Architecture:
- Single source of truth for all social data
- Master refresh populates all tables in optimal order
- Pages read from unified tables, not directly from APIs
- Efficient caching + incremental updates
"""
import os
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy import create_engine, text

from services.platform_data_orchestrator import get_orchestrator, Platform

logger = logging.getLogger(__name__)


class DataDomain(str, Enum):
    """Data domains that can be refreshed"""
    ACCOUNTS = "accounts"           # social_media_accounts
    POSTS = "posts"                 # posted_content
    FOLLOWERS = "followers"         # top_engaged_followers
    COMMENTS = "comments"           # post_comments
    METRICS = "metrics"             # aggregated metrics
    ALL = "all"


@dataclass
class RefreshResult:
    domain: DataDomain
    success: bool
    records_updated: int = 0
    duration_seconds: float = 0
    error: Optional[str] = None


@dataclass
class HydrationStatus:
    last_full_refresh: Optional[datetime] = None
    last_incremental: Optional[datetime] = None
    accounts_count: int = 0
    posts_count: int = 0
    followers_count: int = 0
    comments_count: int = 0
    refresh_in_progress: bool = False
    current_domain: Optional[str] = None


class DataHydrationService:
    """
    Centralized service for hydrating all social media data.
    
    Data Flow:
    1. Master Refresh triggers orchestrator
    2. Data flows: APIs → Orchestrator → Database Tables
    3. Pages read from database tables (not APIs)
    4. Incremental updates for efficiency
    
    Tables Populated:
    - social_media_accounts: Profile data for all connected accounts
    - posted_content: All posts with metrics
    - top_engaged_followers: Engaged users from comments
    - hydration_cache: Aggregated metrics for quick page loads
    """
    
    def __init__(self):
        self.db_url = os.getenv("DATABASE_URL", "")
        self.orchestrator = get_orchestrator()
        self.status = HydrationStatus()
        self._refresh_lock = asyncio.Lock()
    
    def _get_engine(self):
        return create_engine(self.db_url)
    
    async def get_status(self) -> Dict:
        """Get current hydration status for monitoring."""
        engine = self._get_engine()
        
        with engine.connect() as conn:
            # Count records in each table
            try:
                accounts = conn.execute(text("SELECT COUNT(*) FROM social_media_accounts")).scalar() or 0
            except Exception:
                accounts = 0
            
            try:
                posts = conn.execute(text("SELECT COUNT(*) FROM posted_content")).scalar() or 0
            except Exception:
                posts = 0
            
            try:
                followers = conn.execute(text("SELECT COUNT(*) FROM top_engaged_followers")).scalar() or 0
            except Exception:
                followers = 0
            
            try:
                last_refresh = conn.execute(text(
                    "SELECT MAX(last_fetched_at) FROM social_media_accounts"
                )).scalar()
            except Exception:
                last_refresh = None
        
        return {
            "last_full_refresh": str(self.status.last_full_refresh) if self.status.last_full_refresh else None,
            "last_incremental": str(self.status.last_incremental) if self.status.last_incremental else None,
            "accounts_count": accounts,
            "posts_count": posts,
            "followers_count": followers,
            "refresh_in_progress": self.status.refresh_in_progress,
            "current_domain": self.status.current_domain,
            "last_account_fetch": str(last_refresh) if last_refresh else None,
        }
    
    async def master_refresh(self, domains: List[DataDomain] = None) -> Dict[str, RefreshResult]:
        """
        Master refresh - fetches all data in optimal order.
        
        Order matters:
        1. Accounts first (need profile data)
        2. Posts (need account context)
        3. Comments (need post IDs)
        4. Followers (extracted from comments)
        5. Metrics (aggregated from above)
        """
        if self.status.refresh_in_progress:
            return {"error": "Refresh already in progress"}
        
        async with self._refresh_lock:
            self.status.refresh_in_progress = True
            results = {}
            
            try:
                domains = domains or [DataDomain.ALL]
                
                if DataDomain.ALL in domains or DataDomain.ACCOUNTS in domains:
                    self.status.current_domain = "accounts"
                    results["accounts"] = await self._refresh_accounts()
                
                if DataDomain.ALL in domains or DataDomain.POSTS in domains:
                    self.status.current_domain = "posts"
                    results["posts"] = await self._refresh_posts()
                
                if DataDomain.ALL in domains or DataDomain.COMMENTS in domains:
                    self.status.current_domain = "comments"
                    results["comments"] = await self._refresh_comments()
                
                if DataDomain.ALL in domains or DataDomain.FOLLOWERS in domains:
                    self.status.current_domain = "followers"
                    results["followers"] = await self._refresh_followers()
                
                if DataDomain.ALL in domains or DataDomain.METRICS in domains:
                    self.status.current_domain = "metrics"
                    results["metrics"] = await self._refresh_metrics()
                
                self.status.last_full_refresh = datetime.now()
                
            finally:
                self.status.refresh_in_progress = False
                self.status.current_domain = None
            
            return results
    
    async def _refresh_accounts(self) -> RefreshResult:
        """Refresh all social media accounts with profile data."""
        start = datetime.now()
        engine = self._get_engine()
        updated = 0
        
        try:
            with engine.connect() as conn:
                # Get all active accounts
                accounts = conn.execute(text("""
                    SELECT id, platform, username, external_account_id
                    FROM social_media_accounts WHERE is_active = TRUE
                """)).fetchall()
                
                for account in accounts:
                    account_id, platform_str, username, external_id = account
                    
                    try:
                        platform = Platform(platform_str)
                    except ValueError:
                        continue
                    
                    # Use external_id for YouTube, username for others
                    identifier = external_id or username
                    result = await self.orchestrator.fetch_profile(platform, identifier)
                    
                    if result.success:
                        parsed = self.orchestrator._parse_profile_data(platform, result.data)
                        if parsed:
                            conn.execute(text("""
                                UPDATE social_media_accounts SET
                                    followers_count = :followers,
                                    following_count = :following,
                                    posts_count = :posts,
                                    total_views = :views,
                                    total_likes = :likes,
                                    bio = :bio,
                                    profile_pic_url = :avatar,
                                    last_fetched_at = NOW(),
                                    updated_at = NOW()
                                WHERE id = :id
                            """), {
                                "id": account_id,
                                "followers": parsed.get("followers", 0),
                                "following": parsed.get("following", 0),
                                "posts": parsed.get("posts", 0),
                                "views": parsed.get("views", 0),
                                "likes": parsed.get("likes", 0),
                                "bio": (parsed.get("bio", "") or "")[:500],
                                "avatar": parsed.get("avatar", ""),
                            })
                            conn.commit()
                            updated += 1
                    
                    await asyncio.sleep(0.3)  # Rate limit protection
            
            duration = (datetime.now() - start).total_seconds()
            return RefreshResult(DataDomain.ACCOUNTS, True, updated, duration)
            
        except Exception as e:
            logger.error(f"Error refreshing accounts: {e}")
            return RefreshResult(DataDomain.ACCOUNTS, False, error=str(e))
    
    async def _refresh_posts(self) -> RefreshResult:
        """Refresh post metrics from APIs."""
        start = datetime.now()
        engine = self._get_engine()
        updated = 0
        
        try:
            with engine.connect() as conn:
                # Get accounts to fetch posts for
                accounts = conn.execute(text("""
                    SELECT id, platform, username, external_account_id
                    FROM social_media_accounts WHERE is_active = TRUE
                """)).fetchall()
                
                for account in accounts:
                    account_id, platform_str, username, external_id = account
                    
                    try:
                        platform = Platform(platform_str)
                    except ValueError:
                        continue
                    
                    identifier = external_id or username
                    
                    # Fetch recent posts
                    result = await self.orchestrator.fetch_posts(platform, identifier, count=30)
                    
                    if result.success:
                        posts = self.orchestrator._extract_posts(platform, result.data)
                        
                        for post in posts:
                            post_id = self._extract_post_id(platform, post)
                            if post_id:
                                # Update or insert post
                                metrics = self._extract_post_metrics(platform, post)
                                
                                conn.execute(text("""
                                    INSERT INTO posted_content 
                                    (platform_post_id, platform, account_username, 
                                     views, likes, comments, shares, analytics_updated_at)
                                    VALUES (:post_id, :platform, :username,
                                            :views, :likes, :comments, :shares, NOW())
                                    ON CONFLICT (platform_post_id) DO UPDATE SET
                                        views = :views,
                                        likes = :likes,
                                        comments = :comments,
                                        shares = :shares,
                                        analytics_updated_at = NOW()
                                """), {
                                    "post_id": post_id,
                                    "platform": platform_str,
                                    "username": username,
                                    "views": metrics.get("views", 0),
                                    "likes": metrics.get("likes", 0),
                                    "comments": metrics.get("comments", 0),
                                    "shares": metrics.get("shares", 0),
                                })
                                updated += 1
                        
                        conn.commit()
                    
                    await asyncio.sleep(0.5)
            
            duration = (datetime.now() - start).total_seconds()
            return RefreshResult(DataDomain.POSTS, True, updated, duration)
            
        except Exception as e:
            logger.error(f"Error refreshing posts: {e}")
            return RefreshResult(DataDomain.POSTS, False, error=str(e))
    
    async def _refresh_comments(self) -> RefreshResult:
        """Refresh comments from recent posts."""
        start = datetime.now()
        engine = self._get_engine()
        updated = 0
        
        try:
            with engine.connect() as conn:
                # Get recent posts that need comment refresh
                posts = conn.execute(text("""
                    SELECT platform_post_id, platform, account_username
                    FROM posted_content 
                    WHERE posted_at > NOW() - INTERVAL '30 days'
                    ORDER BY posted_at DESC
                    LIMIT 50
                """)).fetchall()
                
                for post in posts:
                    post_id, platform_str, username = post
                    
                    try:
                        platform = Platform(platform_str)
                    except ValueError:
                        continue
                    
                    result = await self.orchestrator.fetch_comments(platform, post_id, count=50)
                    
                    if result.success:
                        commenters = self.orchestrator._extract_commenters(platform, result.data)
                        updated += len(commenters)
                        
                        # Save commenters to engaged followers
                        for c in commenters:
                            user_id = c.get("user_id")
                            if user_id:
                                score = c.get("comment_count", 1) * 10 + c.get("like_count", 0) * 2
                                tier = "super_fan" if score >= 30 else "active" if score >= 15 else "lurker"
                                
                                conn.execute(text("""
                                    INSERT INTO top_engaged_followers 
                                    (follower_id, platform, username, display_name, avatar_url,
                                     engagement_score, engagement_tier, comment_count, like_count,
                                     total_interactions, last_interaction, rank, platform_rank)
                                    VALUES (:fid, :platform, :username, :display_name, :avatar,
                                            :score, :tier, :comments, :likes, :interactions, NOW(), 0, 0)
                                    ON CONFLICT (platform, follower_id) DO UPDATE SET
                                        comment_count = top_engaged_followers.comment_count + EXCLUDED.comment_count,
                                        like_count = top_engaged_followers.like_count + EXCLUDED.like_count,
                                        engagement_score = top_engaged_followers.engagement_score + :score,
                                        total_interactions = top_engaged_followers.total_interactions + :interactions,
                                        last_interaction = NOW()
                                """), {
                                    "fid": user_id,
                                    "platform": platform_str,
                                    "username": c.get("username", ""),
                                    "display_name": c.get("display_name", c.get("username", "")),
                                    "avatar": c.get("avatar", ""),
                                    "score": score,
                                    "tier": tier,
                                    "comments": c.get("comment_count", 1),
                                    "likes": c.get("like_count", 0),
                                    "interactions": c.get("comment_count", 1) + c.get("like_count", 0),
                                })
                        
                        conn.commit()
                    
                    await asyncio.sleep(0.3)
            
            duration = (datetime.now() - start).total_seconds()
            return RefreshResult(DataDomain.COMMENTS, True, updated, duration)
            
        except Exception as e:
            logger.error(f"Error refreshing comments: {e}")
            return RefreshResult(DataDomain.COMMENTS, False, error=str(e))
    
    async def _refresh_followers(self) -> RefreshResult:
        """Update follower rankings and tiers."""
        start = datetime.now()
        engine = self._get_engine()
        updated = 0
        
        try:
            with engine.connect() as conn:
                # Recalculate tiers based on current scores
                conn.execute(text("""
                    UPDATE top_engaged_followers SET
                        engagement_tier = CASE
                            WHEN engagement_score >= 30 THEN 'super_fan'
                            WHEN engagement_score >= 15 THEN 'active'
                            WHEN engagement_score >= 5 THEN 'lurker'
                            ELSE 'inactive'
                        END
                """))
                
                # Update global rankings
                conn.execute(text("""
                    WITH ranked AS (
                        SELECT id, ROW_NUMBER() OVER (ORDER BY engagement_score DESC) as new_rank
                        FROM top_engaged_followers
                    )
                    UPDATE top_engaged_followers SET rank = ranked.new_rank
                    FROM ranked WHERE top_engaged_followers.id = ranked.id
                """))
                
                # Update platform-specific rankings
                conn.execute(text("""
                    WITH ranked AS (
                        SELECT id, ROW_NUMBER() OVER (
                            PARTITION BY platform ORDER BY engagement_score DESC
                        ) as new_rank
                        FROM top_engaged_followers
                    )
                    UPDATE top_engaged_followers SET platform_rank = ranked.new_rank
                    FROM ranked WHERE top_engaged_followers.id = ranked.id
                """))
                
                conn.commit()
                
                updated = conn.execute(text("SELECT COUNT(*) FROM top_engaged_followers")).scalar() or 0
            
            duration = (datetime.now() - start).total_seconds()
            return RefreshResult(DataDomain.FOLLOWERS, True, updated, duration)
            
        except Exception as e:
            logger.error(f"Error refreshing followers: {e}")
            return RefreshResult(DataDomain.FOLLOWERS, False, error=str(e))
    
    async def _refresh_metrics(self) -> RefreshResult:
        """Compute aggregated metrics for quick page loads."""
        start = datetime.now()
        engine = self._get_engine()
        
        try:
            with engine.connect() as conn:
                # Ensure hydration_cache table exists
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS hydration_cache (
                        key TEXT PRIMARY KEY,
                        value JSONB NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """))
                conn.commit()
                
                # Aggregate account metrics
                account_totals = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_accounts,
                        COUNT(DISTINCT platform) as total_platforms,
                        COALESCE(SUM(followers_count), 0)::bigint as total_followers,
                        COALESCE(SUM(posts_count), 0)::bigint as total_posts,
                        COALESCE(SUM(total_views), 0)::bigint as total_views,
                        COALESCE(SUM(total_likes), 0)::bigint as total_likes
                    FROM social_media_accounts WHERE is_active = TRUE
                """)).fetchone()
                
                import json
                totals_json = json.dumps({
                    "total_accounts": int(account_totals[0]),
                    "total_platforms": int(account_totals[1]),
                    "total_followers": int(account_totals[2]),
                    "total_posts": int(account_totals[3]),
                    "total_views": int(account_totals[4]),
                    "total_likes": int(account_totals[5]),
                })
                
                conn.execute(text("""
                    INSERT INTO hydration_cache (key, value, updated_at)
                    VALUES ('account_totals', CAST(:value AS jsonb), NOW())
                    ON CONFLICT (key) DO UPDATE SET value = CAST(EXCLUDED.value AS jsonb), updated_at = NOW()
                """), {"value": totals_json})
                
                # Platform breakdown
                platform_breakdown = conn.execute(text("""
                    SELECT 
                        platform,
                        COUNT(*)::int as accounts,
                        COALESCE(SUM(followers_count), 0)::bigint as followers,
                        COALESCE(SUM(total_views), 0)::bigint as views
                    FROM social_media_accounts WHERE is_active = TRUE
                    GROUP BY platform
                """)).fetchall()
                
                breakdown = {row[0]: {"accounts": int(row[1]), "followers": int(row[2]), "views": int(row[3])} 
                            for row in platform_breakdown}
                breakdown_json = json.dumps(breakdown)
                
                conn.execute(text("""
                    INSERT INTO hydration_cache (key, value, updated_at)
                    VALUES ('platform_breakdown', CAST(:value AS jsonb), NOW())
                    ON CONFLICT (key) DO UPDATE SET value = CAST(EXCLUDED.value AS jsonb), updated_at = NOW()
                """), {"value": breakdown_json})
                
                # Engagement stats
                engagement_stats = conn.execute(text("""
                    SELECT 
                        COUNT(*)::int as total_followers,
                        COUNT(*) FILTER (WHERE engagement_tier = 'super_fan')::int as super_fans,
                        COUNT(*) FILTER (WHERE engagement_tier = 'active')::int as active,
                        COUNT(*) FILTER (WHERE engagement_tier = 'lurker')::int as lurkers
                    FROM top_engaged_followers
                """)).fetchone()
                
                engagement_json = json.dumps({
                    "total_engaged": int(engagement_stats[0]),
                    "super_fans": int(engagement_stats[1]),
                    "active": int(engagement_stats[2]),
                    "lurkers": int(engagement_stats[3]),
                })
                
                conn.execute(text("""
                    INSERT INTO hydration_cache (key, value, updated_at)
                    VALUES ('engagement_stats', CAST(:value AS jsonb), NOW())
                    ON CONFLICT (key) DO UPDATE SET value = CAST(EXCLUDED.value AS jsonb), updated_at = NOW()
                """), {"value": engagement_json})
                
                conn.commit()
            
            duration = (datetime.now() - start).total_seconds()
            return RefreshResult(DataDomain.METRICS, True, 3, duration)
            
        except Exception as e:
            logger.error(f"Error refreshing metrics: {e}")
            return RefreshResult(DataDomain.METRICS, False, error=str(e))
    
    def _extract_post_id(self, platform: Platform, post: Dict) -> Optional[str]:
        """Extract post ID from different platform formats."""
        if platform == Platform.TIKTOK:
            return post.get("video_id") or post.get("aweme_id")
        elif platform == Platform.INSTAGRAM:
            return post.get("shortcode") or post.get("id")
        elif platform == Platform.YOUTUBE:
            return post.get("id")
        elif platform == Platform.BLUESKY:
            uri = post.get("id") or ""
            return uri.split("/")[-1] if "/" in uri else uri
        return post.get("id")
    
    def _extract_post_metrics(self, platform: Platform, post: Dict) -> Dict:
        """Extract metrics from different platform formats."""
        if platform == Platform.TIKTOK:
            stats = post.get("statistics", {})
            return {
                "views": stats.get("play_count", 0) or post.get("play_count", 0),
                "likes": stats.get("digg_count", 0) or post.get("digg_count", 0),
                "comments": stats.get("comment_count", 0) or post.get("comment_count", 0),
                "shares": stats.get("share_count", 0) or post.get("share_count", 0),
            }
        elif platform == Platform.INSTAGRAM:
            return {
                "views": post.get("video_view_count", 0),
                "likes": post.get("edge_liked_by", {}).get("count", 0) or post.get("like_count", 0),
                "comments": post.get("edge_media_to_comment", {}).get("count", 0) or post.get("comment_count", 0),
                "shares": 0,
            }
        elif platform == Platform.YOUTUBE:
            stats = post.get("statistics", {})
            return {
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "comments": int(stats.get("commentCount", 0)),
                "shares": 0,
            }
        return {"views": 0, "likes": 0, "comments": 0, "shares": 0}
    
    # =========================================================================
    # PAGE DATA PROVIDERS
    # =========================================================================
    
    async def get_analytics_overview(self) -> Dict:
        """Get data for Analytics/Dashboard page."""
        engine = self._get_engine()
        
        with engine.connect() as conn:
            # Get cached totals
            try:
                totals_row = conn.execute(text(
                    "SELECT value FROM hydration_cache WHERE key = 'account_totals'"
                )).fetchone()
                totals = eval(totals_row[0]) if totals_row else {}
            except Exception:
                totals = {}
            
            # Get platform breakdown
            try:
                breakdown_row = conn.execute(text(
                    "SELECT value FROM hydration_cache WHERE key = 'platform_breakdown'"
                )).fetchone()
                breakdown = eval(breakdown_row[0]) if breakdown_row else {}
            except Exception:
                breakdown = {}
            
            # Get accounts list
            accounts = conn.execute(text("""
                SELECT id, platform, username, display_name, profile_pic_url,
                       followers_count, posts_count, total_views, engagement_rate, last_fetched_at
                FROM social_media_accounts WHERE is_active = TRUE
                ORDER BY followers_count DESC
            """)).fetchall()
            
            return {
                "totals": totals,
                "platform_breakdown": breakdown,
                "accounts": [
                    {
                        "id": row[0],
                        "platform": row[1],
                        "username": row[2],
                        "display_name": row[3],
                        "profile_pic_url": row[4],
                        "followers_count": row[5],
                        "posts_count": row[6],
                        "total_views": row[7],
                        "engagement_rate": float(row[8]) if row[8] else 0,
                        "last_fetched_at": str(row[9]) if row[9] else None,
                    }
                    for row in accounts
                ],
            }
    
    async def get_content_performance(self, limit: int = 100) -> Dict:
        """Get data for Content Performance page."""
        engine = self._get_engine()
        
        with engine.connect() as conn:
            posts = conn.execute(text("""
                SELECT 
                    id, platform, platform_post_id, account_username,
                    caption, views, likes, comments, shares, saves,
                    engagement_rate, posted_at, analytics_updated_at
                FROM posted_content
                ORDER BY posted_at DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            return {
                "posts": [
                    {
                        "id": str(row[0]),
                        "platform": row[1],
                        "platform_post_id": row[2],
                        "account_username": row[3],
                        "caption": row[4],
                        "views": row[5] or 0,
                        "likes": row[6] or 0,
                        "comments": row[7] or 0,
                        "shares": row[8] or 0,
                        "saves": row[9] or 0,
                        "engagement_rate": float(row[10]) if row[10] else 0,
                        "posted_at": str(row[11]) if row[11] else None,
                        "analytics_updated_at": str(row[12]) if row[12] else None,
                    }
                    for row in posts
                ],
                "total": len(posts),
            }
    
    async def get_top_fans(self, platform: str = None, tier: str = None, limit: int = 50) -> Dict:
        """Get data for Followers/Top Fans page."""
        engine = self._get_engine()
        
        with engine.connect() as conn:
            # Build query
            where_clauses = ["1=1"]
            params = {"limit": limit}
            
            if platform:
                where_clauses.append("platform = :platform")
                params["platform"] = platform
            
            if tier:
                where_clauses.append("engagement_tier = :tier")
                params["tier"] = tier
            
            query = f"""
                SELECT 
                    follower_id, platform, username, display_name, avatar_url,
                    follower_count, verified, engagement_score, engagement_tier,
                    total_interactions, comment_count, like_count, share_count,
                    last_interaction, rank, platform_rank
                FROM top_engaged_followers
                WHERE {' AND '.join(where_clauses)}
                ORDER BY engagement_score DESC
                LIMIT :limit
            """
            
            followers = conn.execute(text(query), params).fetchall()
            
            # Get stats
            try:
                stats_row = conn.execute(text(
                    "SELECT value FROM hydration_cache WHERE key = 'engagement_stats'"
                )).fetchone()
                stats = eval(stats_row[0]) if stats_row else {}
            except Exception:
                stats = {}
            
            return {
                "followers": [
                    {
                        "follower_id": row[0],
                        "platform": row[1],
                        "username": row[2],
                        "display_name": row[3],
                        "avatar_url": row[4],
                        "follower_count": row[5] or 0,
                        "verified": row[6] or False,
                        "engagement_score": float(row[7]) if row[7] else 0,
                        "engagement_tier": row[8],
                        "total_interactions": row[9] or 0,
                        "comment_count": row[10] or 0,
                        "like_count": row[11] or 0,
                        "share_count": row[12] or 0,
                        "last_interaction": str(row[13]) if row[13] else None,
                        "rank": row[14],
                        "platform_rank": row[15],
                    }
                    for row in followers
                ],
                "stats": stats,
                "total": len(followers),
            }
    
    async def get_people(self, limit: int = 50) -> Dict:
        """Get data for People page."""
        engine = self._get_engine()
        
        with engine.connect() as conn:
            # Combine accounts + engaged followers
            people = conn.execute(text("""
                SELECT 
                    id::text,
                    COALESCE(display_name, username) as name,
                    username as handle,
                    platform,
                    profile_pic_url as avatar_url,
                    followers_count,
                    engagement_rate as engagement_score,
                    'account' as relationship,
                    last_fetched_at as last_interaction
                FROM social_media_accounts
                WHERE is_active = TRUE
                ORDER BY followers_count DESC
                LIMIT :limit
            """), {"limit": limit}).fetchall()
            
            return {
                "people": [
                    {
                        "id": row[0],
                        "name": row[1] or row[2],
                        "handle": f"@{row[2]}",
                        "platform": row[3],
                        "avatar_url": row[4],
                        "followers_count": row[5] or 0,
                        "engagement_score": float(row[6]) if row[6] else 0,
                        "relationship": row[7],
                        "last_interaction": str(row[8]) if row[8] else None,
                    }
                    for row in people
                ],
                "total": len(people),
            }
    
    async def get_schedule_data(self, start_date: str = None, end_date: str = None) -> Dict:
        """Get hydrated data for Schedule/Calendar page."""
        engine = self._get_engine()
        
        # Build where clauses
        where_clauses = ["1=1"]
        params = {}
        
        if start_date:
            where_clauses.append("scheduled_at >= :start_date")
            params["start_date"] = start_date
        if end_date:
            where_clauses.append("scheduled_at <= :end_date")
            params["end_date"] = end_date
        
        # Get scheduled posts (simple query, no join to avoid missing table issues)
        try:
            with engine.connect() as conn:
                scheduled_posts = conn.execute(text(f"""
                    SELECT 
                        id, content_id, title, caption, platform,
                        account_username, scheduled_at, status
                    FROM scheduled_posts
                    WHERE {' AND '.join(where_clauses)}
                    ORDER BY scheduled_at ASC
                """), params).fetchall()
        except Exception as e:
            logger.error(f"Error fetching scheduled posts: {e}")
            scheduled_posts = []
        
        # Get connected accounts for account selector
        try:
            with engine.connect() as conn:
                accounts = conn.execute(text("""
                    SELECT id, platform, username, display_name, profile_pic_url
                    FROM social_media_accounts WHERE is_active = TRUE
                    ORDER BY platform, username
                """)).fetchall()
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            accounts = []
        
        # Get analyzed content for media selector (may not exist)
        try:
            with engine.connect() as conn:
                content = conn.execute(text("""
                    SELECT id, file_name, file_path, thumbnail_path, duration_sec,
                           overall_score, status, title, created_at
                    FROM analyzed_content
                    WHERE status IN ('approved', 'pending', 'fresh')
                    ORDER BY created_at DESC
                    LIMIT 100
                """)).fetchall()
        except Exception as e:
            logger.debug(f"analyzed_content table may not exist: {e}")
            content = []
        
        # Get platform stats
        try:
            with engine.connect() as conn:
                platform_stats = conn.execute(text("""
                    SELECT platform, COUNT(*) as count
                    FROM scheduled_posts
                    WHERE status IN ('scheduled', 'pending')
                    GROUP BY platform
                """)).fetchall()
        except Exception:
            platform_stats = []
        
        # Get schedule stats
        try:
            with engine.connect() as conn:
                stats = conn.execute(text("""
                    SELECT 
                        COUNT(*) FILTER (WHERE status = 'scheduled') as scheduled,
                        COUNT(*) FILTER (WHERE status = 'pending') as pending,
                        COUNT(*) FILTER (WHERE status = 'posted') as posted,
                        COUNT(*) as total
                    FROM scheduled_posts
                """)).fetchone()
        except Exception:
            stats = (0, 0, 0, 0)
        
        return {
            "scheduled_posts": [
                {
                    "id": str(row[0]),
                    "contentId": str(row[1]) if row[1] else None,
                    "title": row[2],
                    "caption": row[3],
                    "platform": row[4],
                    "accountUsername": row[5],
                    "scheduledAt": str(row[6]) if row[6] else None,
                    "status": row[7],
                }
                for row in scheduled_posts
            ],
            "accounts": [
                {
                    "id": str(row[0]),
                    "platform": row[1],
                    "username": row[2],
                    "displayName": row[3],
                    "avatarUrl": row[4],
                }
                for row in accounts
            ],
            "media_library": [
                {
                    "id": str(row[0]),
                    "fileName": row[1],
                    "filePath": row[2],
                    "thumbnailPath": row[3],
                    "duration": row[4],
                    "score": row[5],
                    "status": row[6],
                    "title": row[7],
                    "createdAt": str(row[8]) if row[8] else None,
                }
                for row in content
            ],
            "platform_stats": {row[0]: row[1] for row in platform_stats},
            "stats": {
                "scheduled": stats[0] or 0,
                "pending": stats[1] or 0,
                "posted": stats[2] or 0,
                "total": stats[3] or 0,
            },
        }
    
    async def get_narrative_builder_data(self) -> Dict:
        """Get hydrated data for Narrative Builder page."""
        engine = self._get_engine()
        
        # Get content candidates (may not exist)
        try:
            with engine.connect() as conn:
                candidates = conn.execute(text("""
                    SELECT id, file_name, thumbnail_path, duration_sec,
                           overall_score, status, title, hooks, topics
                    FROM analyzed_content
                    WHERE status IN ('approved', 'pending', 'fresh')
                    ORDER BY overall_score DESC NULLS LAST
                    LIMIT 50
                """)).fetchall()
        except Exception:
            candidates = []
        
        # Get accounts for platform selection
        try:
            with engine.connect() as conn:
                accounts = conn.execute(text("""
                    SELECT id, platform, username, display_name
                    FROM social_media_accounts WHERE is_active = TRUE
                """)).fetchall()
        except Exception:
            accounts = []
        
        # Get recent scheduled posts
        try:
            with engine.connect() as conn:
                recent_scheduled = conn.execute(text("""
                    SELECT id, title, platform, scheduled_at, status
                    FROM scheduled_posts
                    WHERE scheduled_at > NOW()
                    ORDER BY scheduled_at ASC
                    LIMIT 20
                """)).fetchall()
        except Exception:
            recent_scheduled = []
        
        # Get saved recommendations
        try:
            with engine.connect() as conn:
                recommendations = conn.execute(text("""
                    SELECT id, media_id, narrative_score, predicted_performance,
                           suggested_caption, suggested_time, platforms, created_at
                    FROM narrative_recommendations
                    WHERE created_at > NOW() - INTERVAL '7 days'
                    ORDER BY narrative_score DESC
                    LIMIT 10
                """)).fetchall()
        except Exception:
            recommendations = []
        
        return {
            "candidates": [
                {
                    "id": str(row[0]),
                    "fileName": row[1],
                    "thumbnailPath": row[2],
                    "duration": row[3],
                    "score": row[4],
                    "status": row[5],
                    "title": row[6],
                    "hooks": row[7] if row[7] else [],
                    "topics": row[8] if row[8] else [],
                }
                for row in candidates
            ],
            "accounts": [
                {
                    "id": str(row[0]),
                    "platform": row[1],
                    "username": row[2],
                    "displayName": row[3],
                }
                for row in accounts
            ],
            "upcoming_posts": [
                {
                    "id": str(row[0]),
                    "title": row[1],
                    "platform": row[2],
                    "scheduledAt": str(row[3]) if row[3] else None,
                    "status": row[4],
                }
                for row in recent_scheduled
            ],
            "recommendations": [
                {
                    "id": str(row[0]),
                    "mediaId": str(row[1]),
                    "narrativeScore": row[2],
                    "predictedPerformance": row[3],
                    "suggestedCaption": row[4],
                    "suggestedTime": row[5],
                    "platforms": row[6] if row[6] else [],
                    "createdAt": str(row[7]) if row[7] else None,
                }
                for row in recommendations
            ],
        }


# Singleton
_hydration_service: Optional[DataHydrationService] = None


def get_hydration_service() -> DataHydrationService:
    global _hydration_service
    if _hydration_service is None:
        _hydration_service = DataHydrationService()
    return _hydration_service
