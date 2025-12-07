"""
Social Media Analytics API Endpoints
Provides aggregated and platform-specific analytics data
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy import create_engine, text
from pydantic import BaseModel
import os

router = APIRouter(tags=["Social Analytics"])

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")
engine = create_engine(DATABASE_URL)


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class AccountSummary(BaseModel):
    platform: str
    username: str
    account_status: str
    followers_count: int
    total_views: int
    total_likes: int
    total_comments: int
    engagement_rate: float
    follower_growth: int
    posts_count: int
    last_fetched_at: Optional[str]


class PlatformMetrics(BaseModel):
    platform: str
    total_accounts: int
    total_followers: int
    total_posts: int
    total_views: int
    total_likes: int
    avg_engagement_rate: float


class PostWithContent(BaseModel):
    post_id: int
    platform: str
    account_username: str
    post_url: str
    caption: Optional[str]
    media_type: str
    posted_at: Optional[str]
    current_views: int
    current_likes: int
    current_comments: int
    engagement_rate: float
    video_id: Optional[str]
    clip_id: Optional[str]
    has_video: bool
    has_clip: bool


class ContentMapping(BaseModel):
    video_id: Optional[str]
    clip_id: Optional[str]
    video_title: Optional[str]
    platforms: List[str]
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    best_performing_platform: str


class DashboardOverview(BaseModel):
    total_platforms: int
    total_accounts: int
    total_followers: int
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    avg_engagement_rate: float
    platform_breakdown: List[PlatformMetrics]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/overview", response_model=DashboardOverview)
async def get_dashboard_overview():
    """
    Get top-level overview of all social media analytics
    Aggregates data across all platforms
    """
    conn = engine.connect()
    
    try:
        # Get aggregated metrics
        result = conn.execute(text("""
            SELECT 
                COUNT(DISTINCT platform) as total_platforms,
                COUNT(DISTINCT id) as total_accounts,
                COALESCE(SUM(followers_count), 0) as total_followers,
                COALESCE(SUM(posts_count), 0) as total_posts,
                COALESCE(SUM(total_views), 0) as total_views,
                COALESCE(SUM(total_likes), 0) as total_likes,
                COALESCE(SUM(total_comments), 0) as total_comments,
                COALESCE(AVG(engagement_rate), 0) as avg_engagement_rate
            FROM social_analytics_latest
        """)).fetchone()
        
        # Get platform breakdown
        platform_results = conn.execute(text("""
            SELECT 
                platform,
                COUNT(*) as total_accounts,
                COALESCE(SUM(followers_count), 0) as total_followers,
                COALESCE(SUM(posts_count), 0) as total_posts,
                COALESCE(SUM(total_views), 0) as total_views,
                COALESCE(SUM(total_likes), 0) as total_likes,
                COALESCE(AVG(engagement_rate), 0) as avg_engagement_rate
            FROM social_analytics_latest
            GROUP BY platform
            ORDER BY total_followers DESC
        """)).fetchall()
        
        platform_breakdown = [
            PlatformMetrics(
                platform=row[0],
                total_accounts=row[1],
                total_followers=row[2],
                total_posts=row[3],
                total_views=row[4],
                total_likes=row[5],
                avg_engagement_rate=round(float(row[6]), 2)
            )
            for row in platform_results
        ]
        
        return DashboardOverview(
            total_platforms=result[0],
            total_accounts=result[1],
            total_followers=result[2],
            total_posts=result[3],
            total_views=result[4],
            total_likes=result[5],
            total_comments=result[6],
            avg_engagement_rate=round(float(result[7]), 2),
            platform_breakdown=platform_breakdown
        )
        
    finally:
        conn.close()


@router.get("/accounts", response_model=List[AccountSummary])
async def get_all_accounts(
    platform: Optional[str] = None,
    monitoring_only: bool = True
):
    """
    Get all social media accounts with their latest analytics
    
    - **platform**: Filter by specific platform (optional)
    - **monitoring_only**: Only return accounts with monitoring enabled
    """
    conn = engine.connect()
    
    try:
        query = """
            SELECT 
                platform,
                username,
                account_status,
                COALESCE(followers_count, 0) as followers_count,
                COALESCE(total_views, 0) as total_views,
                COALESCE(total_likes, 0) as total_likes,
                COALESCE(total_comments, 0) as total_comments,
                COALESCE(engagement_rate, 0) as engagement_rate,
                COALESCE(follower_growth, 0) as follower_growth,
                COALESCE(posts_count, 0) as posts_count,
                last_fetched_at
            FROM social_analytics_latest
            WHERE 1=1
        """
        
        params = {}
        if platform:
            query += " AND platform = :platform"
            params["platform"] = platform
        
        if monitoring_only:
            query += " AND monitoring_enabled = TRUE"
        
        query += " ORDER BY followers_count DESC"
        
        results = conn.execute(text(query), params).fetchall()
        
        return [
            AccountSummary(
                platform=row[0],
                username=row[1],
                account_status=row[2],
                followers_count=row[3],
                total_views=row[4],
                total_likes=row[5],
                total_comments=row[6],
                engagement_rate=round(float(row[7]), 2),
                follower_growth=row[8],
                posts_count=row[9],
                last_fetched_at=str(row[10]) if row[10] else None
            )
            for row in results
        ]
        
    finally:
        conn.close()


@router.get("/platform/{platform}", response_model=dict)
async def get_platform_details(
    platform: str,
    days: int = Query(default=30, ge=1, le=365)
):
    """
    Get detailed analytics for a specific platform
    
    - **platform**: Platform name (tiktok, instagram, youtube, etc.)
    - **days**: Number of days to include in trends (default: 30)
    """
    conn = engine.connect()
    
    try:
        # Get accounts for this platform
        accounts = conn.execute(text("""
            SELECT 
                username,
                followers_count,
                total_views,
                total_likes,
                engagement_rate,
                follower_growth
            FROM social_analytics_latest
            WHERE platform = :platform
            ORDER BY followers_count DESC
        """), {"platform": platform}).fetchall()
        
        # Get growth trends
        trends = conn.execute(text("""
            SELECT 
                snapshot_date,
                SUM(followers_count) as total_followers,
                SUM(total_views) as total_views,
                SUM(total_likes) as total_likes,
                AVG(engagement_rate) as avg_engagement
            FROM social_analytics_snapshots sas
            JOIN social_accounts sa ON sas.social_account_id = sa.id
            WHERE sa.platform = :platform
            AND snapshot_date >= CURRENT_DATE - INTERVAL '1 day' * :days
            GROUP BY snapshot_date
            ORDER BY snapshot_date
        """), {"platform": platform, "days": days}).fetchall()
        
        # Get top posts
        top_posts = conn.execute(text("""
            SELECT 
                post_url,
                caption,
                current_views,
                current_likes,
                engagement_rate
            FROM social_post_performance
            WHERE platform = :platform
            ORDER BY current_views DESC
            LIMIT 10
        """), {"platform": platform}).fetchall()
        
        return {
            "platform": platform,
            "accounts": [
                {
                    "username": a[0],
                    "followers": a[1] or 0,
                    "views": a[2] or 0,
                    "likes": a[3] or 0,
                    "engagement_rate": round(float(a[4]), 2) if a[4] is not None else 0.0,
                    "growth": a[5] or 0
                }
                for a in accounts
            ],
            "trends": [
                {
                    "date": str(t[0]),
                    "followers": t[1] or 0,
                    "views": t[2] or 0,
                    "likes": t[3] or 0,
                    "engagement_rate": round(float(t[4]), 2) if t[4] is not None else 0.0
                }
                for t in trends
            ],
            "top_posts": [
                {
                    "url": p[0],
                    "caption": p[1][:100] if p[1] else "",
                    "views": p[2] or 0,
                    "likes": p[3] or 0,
                    "engagement_rate": round(float(p[4]), 2) if p[4] is not None else 0.0
                }
                for p in top_posts
            ]
        }
        
    finally:
        conn.close()


@router.get("/content-mapping", response_model=List[ContentMapping])
async def get_content_mapping(
    has_video: Optional[bool] = None,
    has_clip: Optional[bool] = None
):
    """
    Get content mapping showing which videos/clips are posted to which platforms
    
    - **has_video**: Filter by whether content is mapped to a video
    - **has_clip**: Filter by whether content is mapped to a clip
    """
    conn = engine.connect()
    
    try:
        query = """
            SELECT 
                spa.video_id,
                spa.clip_id,
                v.title as video_title,
                ARRAY_AGG(DISTINCT spa.platform) as platforms,
                COUNT(DISTINCT spa.id) as total_posts,
                SUM(spm.views_count) as total_views,
                SUM(spm.likes_count) as total_likes,
                SUM(spm.comments_count) as total_comments,
                (
                    SELECT spa2.platform 
                    FROM social_posts_analytics spa2
                    LEFT JOIN LATERAL (
                        SELECT views_count 
                        FROM social_post_metrics 
                        WHERE post_id = spa2.id 
                        ORDER BY snapshot_date DESC 
                        LIMIT 1
                    ) spm2 ON TRUE
                    WHERE spa2.video_id = spa.video_id OR spa2.clip_id = spa.clip_id
                    ORDER BY spm2.views_count DESC NULLS LAST
                    LIMIT 1
                ) as best_platform
            FROM social_posts_analytics spa
            LEFT JOIN videos v ON spa.video_id = v.id
            LEFT JOIN LATERAL (
                SELECT * FROM social_post_metrics 
                WHERE post_id = spa.id 
                ORDER BY snapshot_date DESC 
                LIMIT 1
            ) spm ON TRUE
            WHERE (spa.video_id IS NOT NULL OR spa.clip_id IS NOT NULL)
        """
        
        conditions = []
        if has_video is not None:
            conditions.append("spa.video_id IS NOT NULL" if has_video else "spa.video_id IS NULL")
        if has_clip is not None:
            conditions.append("spa.clip_id IS NOT NULL" if has_clip else "spa.clip_id IS NULL")
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += """
            GROUP BY spa.video_id, spa.clip_id, v.title
            ORDER BY total_views DESC NULLS LAST
        """
        
        results = conn.execute(text(query)).fetchall()
        
        return [
            ContentMapping(
                video_id=str(row[0]) if row[0] else None,
                clip_id=str(row[1]) if row[1] else None,
                video_title=row[2],
                platforms=row[3] if row[3] else [],
                total_posts=row[4],
                total_views=row[5] or 0,
                total_likes=row[6] or 0,
                total_comments=row[7] or 0,
                best_performing_platform=row[8] or "Unknown"
            )
            for row in results
        ]
        
    finally:
        conn.close()


@router.get("/posts", response_model=List[PostWithContent])
async def get_posts_with_content(
    platform: Optional[str] = None,
    limit: int = Query(default=50, le=500),
    has_video: Optional[bool] = None,
    has_clip: Optional[bool] = None
):
    """
    Get all social posts with their content mappings
    
    - **platform**: Filter by platform
    - **limit**: Maximum number of posts to return
    - **has_video**: Filter by video mapping
    - **has_clip**: Filter by clip mapping
    """
    conn = engine.connect()
    
    try:
        query = """
            SELECT 
                spa.id,
                spa.platform,
                sa.handle as username,
                spa.post_url,
                spa.caption,
                spa.media_type,
                spa.posted_at,
                spm.views_count,
                spm.likes_count,
                spm.comments_count,
                spm.engagement_rate,
                spa.video_id,
                spa.clip_id
            FROM social_posts_analytics spa
            JOIN social_accounts sa ON spa.social_account_id = sa.id
            LEFT JOIN LATERAL (
                SELECT * FROM social_post_metrics 
                WHERE post_id = spa.id 
                ORDER BY snapshot_date DESC 
                LIMIT 1
            ) spm ON TRUE
            WHERE spa.deleted_at IS NULL
        """
        
        params = {"limit": limit}
        conditions = []
        
        if platform:
            conditions.append("spa.platform = :platform")
            params["platform"] = platform
        
        if has_video is not None:
            conditions.append("spa.video_id IS NOT NULL" if has_video else "spa.video_id IS NULL")
        
        if has_clip is not None:
            conditions.append("spa.clip_id IS NOT NULL" if has_clip else "spa.clip_id IS NULL")
        
        if conditions:
            query += " AND " + " AND ".join(conditions)
        
        query += " ORDER BY spa.posted_at DESC LIMIT :limit"
        
        results = conn.execute(text(query), params).fetchall()
        
        return [
            PostWithContent(
                post_id=row[0],
                platform=row[1],
                account_username=row[2],
                post_url=row[3],
                caption=row[4],
                media_type=row[5],
                posted_at=str(row[6]) if row[6] else None,
                current_views=row[7] or 0,
                current_likes=row[8] or 0,
                current_comments=row[9] or 0,
                engagement_rate=round(float(row[10]), 2) if row[10] else 0.0,
                video_id=str(row[11]) if row[11] else None,
                clip_id=str(row[12]) if row[12] else None,
                has_video=row[11] is not None,
                has_clip=row[12] is not None
            )
            for row in results
        ]
        
    finally:
        conn.close()


@router.get("/trends", response_model=dict)
async def get_analytics_trends(days: int = Query(default=30, ge=7, le=365)):
    """
    Get analytics trends over time (all platforms aggregated)
    
    - **days**: Number of days to include
    """
    conn = engine.connect()
    
    try:
        results = conn.execute(text("""
            SELECT 
                snapshot_date,
                SUM(followers_count) as total_followers,
                SUM(total_views) as total_views,
                SUM(total_likes) as total_likes,
                SUM(total_comments) as total_comments,
                AVG(engagement_rate) as avg_engagement_rate,
                SUM(follower_growth) as total_growth
            FROM social_analytics_snapshots
            WHERE snapshot_date >= CURRENT_DATE - CAST(:days AS INTEGER)
            GROUP BY snapshot_date
            ORDER BY snapshot_date
        """), {"days": days}).fetchall()
        
        return {
            "period_days": days,
            "data_points": len(results),
            "trends": [
                {
                    "date": str(row[0]),
                    "followers": row[1],
                    "views": row[2],
                    "likes": row[3],
                    "comments": row[4],
                    "engagement_rate": round(float(row[5]), 2),
                    "growth": row[6]
                }
                for row in results
            ]
        }
        
    finally:
        conn.close()


@router.get("/hashtags/top", response_model=List[dict])
async def get_top_hashtags(limit: int = Query(default=20, le=100)):
    """Get top performing hashtags across all platforms"""
    conn = engine.connect()
    
    try:
        results = conn.execute(text("""
            SELECT 
                hashtag,
                total_uses,
                total_views,
                avg_engagement_rate
            FROM social_hashtags
            ORDER BY avg_engagement_rate DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        return [
            {
                "hashtag": row[0],
                "uses": row[1],
                "views": row[2],
                "engagement_rate": round(float(row[3]), 2)
            }
            for row in results
        ]
        
    finally:
        conn.close()


# ============================================================================
# CONTENT TRACKING ENDPOINTS
# ============================================================================

@router.get("/content", response_model=List[dict])
async def get_content_items(
    platform: Optional[str] = None,
    min_platforms: int = Query(default=1, ge=1),
    sort_by: str = Query(default="total_likes", regex="^(total_likes|total_comments|total_shares|platform_count)$"),
    limit: int = Query(default=50, le=200)
):
    """
    Get content items with cross-platform metrics
    """
    conn = engine.connect()
    
    try:
        # Build query
        platform_filter = ""
        if platform:
            platform_filter = f"AND '{platform}' = ANY(platforms)"
        
        query = f"""
            SELECT 
                ccs.content_id,
                ccs.title,
                ccs.slug,
                ccs.platform_count,
                ccs.platforms,
                ccs.total_views,
                ccs.total_likes,
                ccs.total_comments,
                ccs.total_shares,
                ccs.total_saves,
                ccs.best_platform,
                ccs.created_at,
                ci.thumbnail_url
            FROM content_cross_platform_summary ccs
            LEFT JOIN content_items ci ON ccs.content_id = ci.id
            WHERE ccs.platform_count >= :min_platforms
            {platform_filter}
            ORDER BY ccs.{sort_by} DESC
            LIMIT :limit
        """
        
        results = conn.execute(text(query), {
            "min_platforms": min_platforms,
            "limit": limit
        }).fetchall()
        
        return [
            {
                "content_id": str(row[0]),
                "title": row[1],
                "slug": row[2],
                "platform_count": row[3],
                "platforms": row[4],
                "total_views": row[5] or 0,
                "total_likes": row[6] or 0,
                "total_comments": row[7] or 0,
                "total_shares": row[8] or 0,
                "total_saves": row[9] or 0,
                "best_platform": row[10],
                "created_at": str(row[11]),
                "thumbnail_url": row[12]
            }
            for row in results
        ]
        
    finally:
        conn.close()


@router.get("/content/leaderboard", response_model=List[dict])
async def get_content_leaderboard(
    metric: str = Query(default="total_likes", regex="^(total_likes|total_comments|total_shares)$"),
    limit: int = Query(default=20, le=100)
):
    """
    Get top performing content ranked by metric
    """
    conn = engine.connect()
    
    try:
        sort_column = {
            "total_likes": "total_likes",
            "total_comments": "total_comments",
            "total_shares": "total_shares"
        }.get(metric, "total_likes")
        
        results = conn.execute(text(f"""
            SELECT 
                content_id,
                title,
                platform_count,
                platforms,
                total_likes,
                total_comments,
                total_shares,
                total_saves,
                best_platform
            FROM content_cross_platform_summary
            WHERE platform_count > 0
            ORDER BY {sort_column} DESC
            LIMIT :limit
        """), {"limit": limit}).fetchall()
        
        return [
            {
                "rank": idx + 1,
                "content_id": str(row[0]),
                "title": row[1],
                "platform_count": row[2],
                "platforms": row[3],
                "total_likes": row[4] or 0,
                "total_comments": row[5] or 0,
                "total_shares": row[6] or 0,
                "total_saves": row[7] or 0,
                "best_platform": row[8]
            }
            for idx, row in enumerate(results)
        ]
        
    finally:
        conn.close()


@router.get("/content/{content_id}", response_model=dict)
async def get_content_detail(content_id: str):
    """
    Get detailed view of content with per-platform breakdown
    """
    conn = engine.connect()
    
    try:
        # Get content summary
        summary = conn.execute(text("""
            SELECT 
                content_id,
                title,
                description,
                slug,
                thumbnail_url,
                platform_count,
                platforms,
                total_likes,
                total_comments,
                total_shares,
                total_saves,
                best_platform,
                created_at
            FROM content_cross_platform_summary
            WHERE content_id = :content_id
        """), {"content_id": content_id}).fetchone()
        
        if not summary:
            raise HTTPException(status_code=404, detail="Content not found")
        
        # Get per-platform breakdown
        platforms = conn.execute(text("""
            SELECT 
                platform,
                post_count,
                first_posted_at,
                last_posted_at,
                like_count,
                comment_count,
                share_count,
                save_count,
                post_urls
            FROM content_platform_rollup
            WHERE content_id = :content_id
            ORDER BY like_count DESC
        """), {"content_id": content_id}).fetchall()
        
        return {
            "content_id": str(summary[0]),
            "title": summary[1],
            "description": summary[2],
            "slug": summary[3],
            "thumbnail_url": summary[4],
            "platform_count": summary[5],
            "platforms": summary[6],
            "totals": {
                "likes": summary[7] or 0,
                "comments": summary[8] or 0,
                "shares": summary[9] or 0,
                "saves": summary[10] or 0
            },
            "best_platform": summary[11],
            "created_at": str(summary[12]),
            "platform_breakdown": [
                {
                    "platform": p[0],
                    "post_count": p[1],
                    "first_posted_at": str(p[2]) if p[2] else None,
                    "last_posted_at": str(p[3]) if p[3] else None,
                    "likes": p[4] or 0,
                    "comments": p[5] or 0,
                    "shares": p[6] or 0,
                    "saves": p[7] or 0,
                    "post_urls": p[8] or []
                }
                for p in platforms
            ]
        }
        
    finally:
        conn.close()


# ============================================================================
# FOLLOWER ENGAGEMENT ENDPOINTS
# ============================================================================

# IMPORTANT: Put /followers/leaderboard BEFORE /followers/{follower_id}
# to avoid route matching issues

@router.get("/followers/leaderboard", response_model=List[dict])
async def get_followers_leaderboard(
    platform: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = Query(default=20, le=100)
):
    """
    Get top engaged followers leaderboard
    """
    conn = engine.connect()
    
    try:
        filters = []
        params = {"limit": limit}
        
        if platform:
            filters.append("platform = :platform")
            params["platform"] = platform
        
        if tier:
            filters.append("engagement_tier = :tier")
            params["tier"] = tier
        
        where_clause = " AND ".join(filters) if filters else "1=1"
        
        results = conn.execute(text(f"""
            SELECT 
                follower_id,
                platform,
                username,
                display_name,
                avatar_url,
                engagement_score,
                engagement_tier,
                total_interactions,
                comment_count,
                last_interaction,
                rank
            FROM top_engaged_followers
            WHERE {where_clause}
            ORDER BY engagement_score DESC
            LIMIT :limit
        """), params).fetchall()
        
        return [
            {
                "rank": row[10],
                "follower_id": str(row[0]),
                "platform": row[1],
                "username": row[2],
                "display_name": row[3],
                "avatar_url": row[4],
                "engagement_score": round(float(row[5]), 2) if row[5] else 0.0,
                "engagement_tier": row[6],
                "total_interactions": row[7],
                "comment_count": row[8],
                "last_interaction": str(row[9]) if row[9] else None
            }
            for row in results
        ]
        
    finally:
        conn.close()


@router.get("/followers", response_model=List[dict])
async def get_followers(
    platform: Optional[str] = None,
    tier: Optional[str] = Query(default=None, regex="^(super_fan|active|lurker|inactive)$"),
    min_score: float = Query(default=0, ge=0),
    sort_by: str = Query(default="engagement_score", regex="^(engagement_score|total_interactions|last_interaction)$"),
    limit: int = Query(default=50, le=200)
):
    """
    Get followers with engagement scores and activity
    """
    conn = engine.connect()
    
    try:
        # Build filters
        filters = ["1=1"]
        params = {"min_score": min_score, "limit": limit}
        
        if platform:
            filters.append("platform = :platform")
            params["platform"] = platform
        
        if tier:
            filters.append("engagement_tier = :tier")
            params["tier"] = tier
        
        filters.append("engagement_score >= :min_score")
        
        where_clause = " AND ".join(filters)
        
        query = f"""
            SELECT 
                follower_id,
                platform,
                username,
                display_name,
                profile_url,
                avatar_url,
                follower_count,
                verified,
                engagement_score,
                engagement_tier,
                total_interactions,
                comment_count,
                like_count,
                share_count,
                avg_sentiment,
                first_interaction,
                last_interaction,
                rank,
                platform_rank
            FROM top_engaged_followers
            WHERE {where_clause}
            ORDER BY {sort_by} DESC
            LIMIT :limit
        """
        
        results = conn.execute(text(query), params).fetchall()
        
        return [
            {
                "follower_id": str(row[0]),
                "platform": row[1],
                "username": row[2],
                "display_name": row[3],
                "profile_url": row[4],
                "avatar_url": row[5],
                "follower_count": row[6],
                "verified": row[7],
                "engagement_score": round(float(row[8]), 2) if row[8] else 0.0,
                "engagement_tier": row[9],
                "total_interactions": row[10],
                "comment_count": row[11],
                "like_count": row[12],
                "share_count": row[13],
                "avg_sentiment": round(float(row[14]), 2) if row[14] else None,
                "first_interaction": str(row[15]) if row[15] else None,
                "last_interaction": str(row[16]) if row[16] else None,
                "rank": row[17],
                "platform_rank": row[18]
            }
            for row in results
        ]
        
    finally:
        conn.close()


@router.get("/followers/{follower_id}", response_model=dict)
async def get_follower_detail(
    follower_id: str,
    timeline_limit: int = Query(default=50, le=200)
):
    """
    Get detailed follower profile with activity timeline
    """
    conn = engine.connect()
    
    try:
        # Get follower profile
        follower = conn.execute(text("""
            SELECT 
                f.id,
                f.platform,
                f.username,
                f.display_name,
                f.profile_url,
                f.avatar_url,
                f.follower_count,
                f.verified,
                f.bio,
                f.first_seen_at,
                f.last_seen_at,
                fes.engagement_score,
                fes.engagement_tier,
                fes.total_interactions,
                fes.comment_count,
                fes.like_count,
                fes.share_count,
                fes.save_count,
                fes.avg_sentiment,
                fes.first_interaction,
                fes.last_interaction
            FROM followers f
            LEFT JOIN follower_engagement_scores fes ON fes.follower_id = f.id
            WHERE f.id = :follower_id
        """), {"follower_id": follower_id}).fetchone()
        
        if not follower:
            raise HTTPException(status_code=404, detail="Follower not found")
        
        # Get activity timeline
        timeline = conn.execute(text("""
            SELECT 
                interaction_id,
                interaction_type,
                occurred_at,
                interaction_value,
                sentiment_score,
                sentiment_label,
                content_title,
                content_id
            FROM follower_activity_timeline
            WHERE follower_id = :follower_id
            ORDER BY occurred_at DESC
            LIMIT :limit
        """), {"follower_id": follower_id, "limit": timeline_limit}).fetchall()
        
        return {
            "follower_id": str(follower[0]),
            "platform": follower[1],
            "username": follower[2],
            "display_name": follower[3],
            "profile_url": follower[4],
            "avatar_url": follower[5],
            "follower_count": follower[6],
            "verified": follower[7],
            "bio": follower[8],
            "first_seen_at": str(follower[9]) if follower[9] else None,
            "last_seen_at": str(follower[10]) if follower[10] else None,
            "engagement": {
                "score": round(float(follower[11]), 2) if follower[11] else 0.0,
                "tier": follower[12],
                "total_interactions": follower[13] or 0,
                "comment_count": follower[14] or 0,
                "like_count": follower[15] or 0,
                "share_count": follower[16] or 0,
                "save_count": follower[17] or 0,
                "avg_sentiment": round(float(follower[18]), 2) if follower[18] else None,
                "first_interaction": str(follower[19]) if follower[19] else None,
                "last_interaction": str(follower[20]) if follower[20] else None
            },
            "timeline": [
                {
                    "interaction_id": t[0],
                    "type": t[1],
                    "occurred_at": str(t[2]),
                    "value": t[3],
                    "sentiment_score": round(float(t[4]), 2) if t[4] else None,
                    "sentiment_label": t[5],
                    "content_title": t[6],
                    "content_id": str(t[7]) if t[7] else None
                }
                for t in timeline
            ]
        }
        
    finally:
        conn.close()


