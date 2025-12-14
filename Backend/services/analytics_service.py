"""
Analytics Service - Phase 5: Analytics & Insights
Calculates North Star Metrics, generates insights, and provides recommendations
Includes external API integration for fetching live metrics from platforms
"""
import logging
import os
import re
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import (
    PlatformPost, PlatformCheckback, PostComment,
    WeeklyMetric, ContentInsight,
    VideoSegment, AnalyzedVideo
)
import uuid

logger = logging.getLogger(__name__)


# =============================================================================
# EXTERNAL ANALYTICS FETCHER - Third-party API integration
# =============================================================================

class ExternalAnalyticsFetcher:
    """Fetches analytics from external APIs (RapidAPI, etc.) with usage tracking"""
    
    def __init__(self):
        self.rapidapi_key = os.getenv("RAPIDAPI_KEY")
        self.rapidapi_tiktok_host = "tiktok-api6.p.rapidapi.com"
        
        # Import usage tracker
        from services.api_usage_tracker import get_api_usage_tracker, APIProvider
        self.usage_tracker = get_api_usage_tracker()
        self.APIProvider = APIProvider
    
    def _get_rapidapi_headers(self, host: str) -> dict:
        """Get headers for RapidAPI requests"""
        return {
            "X-RapidAPI-Key": self.rapidapi_key or "",
            "X-RapidAPI-Host": host
        }
    
    @staticmethod
    def extract_tiktok_video_id(url: str) -> Optional[str]:
        """Extract video ID from TikTok URL"""
        # Patterns for TikTok URLs:
        # https://www.tiktok.com/@username/video/1234567890123456789
        # https://vm.tiktok.com/ABC123/
        patterns = [
            r'tiktok\.com/@[\w.-]+/video/(\d+)',
            r'tiktok\.com/v/(\d+)',
            r'/video/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def extract_tiktok_username(url: str) -> Optional[str]:
        """Extract username from TikTok URL"""
        match = re.search(r'tiktok\.com/@([\w.-]+)', url)
        return match.group(1) if match else None
    
    @staticmethod
    def extract_instagram_media_id(url: str) -> Optional[str]:
        """Extract media shortcode from Instagram URL"""
        # https://www.instagram.com/p/ABC123/
        # https://www.instagram.com/reel/ABC123/
        patterns = [
            r'instagram\.com/p/([\w-]+)',
            r'instagram\.com/reel/([\w-]+)',
            r'instagram\.com/reels/([\w-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def extract_youtube_video_id(url: str) -> Optional[str]:
        """Extract video ID from YouTube URL"""
        # https://www.youtube.com/watch?v=ABC123
        # https://youtu.be/ABC123
        # https://www.youtube.com/shorts/ABC123
        patterns = [
            r'youtube\.com/watch\?v=([\w-]+)',
            r'youtu\.be/([\w-]+)',
            r'youtube\.com/shorts/([\w-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    @staticmethod
    def detect_platform(url: str) -> Optional[str]:
        """Detect platform from URL"""
        url_lower = url.lower()
        if 'tiktok.com' in url_lower:
            return 'tiktok'
        elif 'instagram.com' in url_lower:
            return 'instagram'
        elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
            return 'youtube'
        elif 'twitter.com' in url_lower or 'x.com' in url_lower:
            return 'twitter'
        elif 'facebook.com' in url_lower or 'fb.com' in url_lower:
            return 'facebook'
        elif 'linkedin.com' in url_lower:
            return 'linkedin'
        elif 'threads.net' in url_lower:
            return 'threads'
        elif 'bsky.app' in url_lower:
            return 'bluesky'
        return None
    
    async def fetch_tiktok_analytics(self, video_url: str, use_cache: bool = True, cache_max_age_hours: int = 6) -> Dict[str, Any]:
        """
        Fetch TikTok video analytics via RapidAPI with usage tracking.
        
        Args:
            video_url: TikTok video URL
            use_cache: Whether to check cache first (default True)
            cache_max_age_hours: Max age of cached data in hours (default 6)
            
        Returns:
            Dict with video metrics and usage info
        """
        if not self.rapidapi_key:
            return {"error": "RAPIDAPI_KEY not configured"}
        
        video_id = self.extract_tiktok_video_id(video_url)
        if not video_id:
            return {"error": f"Could not extract video ID from URL: {video_url}"}
        
        # Check cache first
        cache_key = f"tiktok:video:{video_id}"
        if use_cache:
            cached = self.usage_tracker.get_cached_response(cache_key, cache_max_age_hours)
            if cached:
                logger.debug(f"Using cached TikTok analytics for video {video_id}")
                self.usage_tracker.record_call(
                    provider=self.APIProvider.RAPIDAPI_TIKTOK,
                    endpoint="/video/details",
                    success=True,
                    video_id=video_id,
                    cached=True
                )
                cached["from_cache"] = True
                return cached
        
        # Check if we can make the API call (budget check)
        budget_check = self.usage_tracker.can_make_call(self.APIProvider.RAPIDAPI_TIKTOK)
        if not budget_check["allowed"]:
            return {
                "error": f"API budget exceeded: {budget_check['reason']}",
                "budget_info": budget_check
            }
        
        # Log warning if approaching limit
        if budget_check.get("warning"):
            logger.warning(f"TikTok API budget warning: {budget_check.get('warning_message')}")
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(
                    f"https://{self.rapidapi_tiktok_host}/video/details",
                    headers=self._get_rapidapi_headers(self.rapidapi_tiktok_host),
                    params={"video_id": video_id}
                )
                
                if response.status_code != 200:
                    # Record failed call
                    self.usage_tracker.record_call(
                        provider=self.APIProvider.RAPIDAPI_TIKTOK,
                        endpoint="/video/details",
                        success=False,
                        video_id=video_id,
                        metadata={"status_code": response.status_code}
                    )
                    return {"error": f"RapidAPI error: {response.status_code} - {response.text}"}
                
                data = response.json()
                
                # Record successful call
                self.usage_tracker.record_call(
                    provider=self.APIProvider.RAPIDAPI_TIKTOK,
                    endpoint="/video/details",
                    success=True,
                    video_id=video_id,
                    response_size=len(response.content)
                )
                
                # Extract metrics from response
                # RapidAPI TikTok API response structure varies by provider
                video_data = data.get('video', data.get('itemInfo', {}).get('itemStruct', data))
                stats = video_data.get('stats', video_data.get('statistics', {}))
                
                result = {
                    "success": True,
                    "platform": "tiktok",
                    "video_id": video_id,
                    "video_url": video_url,
                    "metrics": {
                        "views": stats.get('playCount', stats.get('play_count', stats.get('views', 0))),
                        "likes": stats.get('diggCount', stats.get('like_count', stats.get('likes', 0))),
                        "comments": stats.get('commentCount', stats.get('comment_count', stats.get('comments', 0))),
                        "shares": stats.get('shareCount', stats.get('share_count', stats.get('shares', 0))),
                        "saves": stats.get('collectCount', stats.get('save_count', stats.get('saves', 0))),
                    },
                    "video_info": {
                        "description": video_data.get('desc', video_data.get('description', '')),
                        "duration": video_data.get('duration', 0),
                        "create_time": video_data.get('createTime', video_data.get('create_time')),
                    },
                    "fetched_at": datetime.now().isoformat(),
                    "from_cache": False,
                    "budget_info": {
                        "usage_pct": budget_check["usage_pct"],
                        "remaining_calls": budget_check["remaining_calls"]
                    }
                }
                
                # Cache the result (without raw_data to save space)
                self.usage_tracker.cache_response(cache_key, result)
                
                return result
                
        except httpx.TimeoutException:
            self.usage_tracker.record_call(
                provider=self.APIProvider.RAPIDAPI_TIKTOK,
                endpoint="/video/details",
                success=False,
                video_id=video_id,
                metadata={"error": "timeout"}
            )
            return {"error": "Request timed out"}
        except Exception as e:
            logger.error(f"TikTok analytics fetch error: {e}")
            self.usage_tracker.record_call(
                provider=self.APIProvider.RAPIDAPI_TIKTOK,
                endpoint="/video/details",
                success=False,
                video_id=video_id,
                metadata={"error": str(e)}
            )
            return {"error": str(e)}
    
    async def fetch_analytics_by_url(self, url: str) -> Dict[str, Any]:
        """
        Fetch analytics for any supported platform URL
        
        Args:
            url: Post/video URL
            
        Returns:
            Dict with metrics
        """
        platform = self.detect_platform(url)
        
        if not platform:
            return {"error": f"Unsupported platform for URL: {url}"}
        
        if platform == 'tiktok':
            return await self.fetch_tiktok_analytics(url)
        elif platform == 'instagram':
            # TODO: Implement Instagram analytics via RapidAPI
            return {
                "error": "Instagram analytics not yet implemented",
                "platform": "instagram",
                "media_id": self.extract_instagram_media_id(url)
            }
        elif platform == 'youtube':
            # TODO: Implement YouTube analytics via official API or RapidAPI
            return {
                "error": "YouTube analytics not yet implemented",
                "platform": "youtube",
                "video_id": self.extract_youtube_video_id(url)
            }
        else:
            return {
                "error": f"Analytics not yet supported for platform: {platform}",
                "platform": platform
            }


# Singleton instance
_external_fetcher = None

def get_external_analytics_fetcher() -> ExternalAnalyticsFetcher:
    """Get singleton instance of ExternalAnalyticsFetcher"""
    global _external_fetcher
    if _external_fetcher is None:
        _external_fetcher = ExternalAnalyticsFetcher()
    return _external_fetcher


class AnalyticsService:
    """Service for calculating metrics and generating insights"""
    
    def __init__(self, db: Session):
        """
        Initialize analytics service
        
        Args:
            db: Database session
        """
        self.db = db
    
    def calculate_weekly_metrics(
        self,
        week_start: date,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Calculate North Star Metrics for a week
        
        North Star Metrics:
        1. Weekly Engaged Reach - Unique users who engaged
        2. Content Leverage Score - (comments + saves + shares + taps) / posts
        3. Warm Lead Flow - link_clicks + dm_starts + signups
        
        Args:
            week_start: Start of week (Monday)
            user_id: Optional user ID filter
            
        Returns:
            Calculated metrics
        """
        week_end = week_start + timedelta(days=7)
        
        logger.info(f"Calculating weekly metrics for {week_start} to {week_end}")
        
        # Get all posts in this week
        posts_query = self.db.query(PlatformPost).filter(
            PlatformPost.published_at >= week_start,
            PlatformPost.published_at < week_end
        )
        
        if user_id:
            # Join with VideoClip to filter by user
            # Note: This assumes posts are linked to clips. For pure text posts, we'd need to join ContentVariant -> ContentItem
            from database.models import VideoClip
            posts_query = posts_query.join(VideoClip, PlatformPost.clip_id == VideoClip.id).filter(VideoClip.user_id == user_id)
        
        posts = posts_query.all()
        total_posts = len(posts)
        
        if total_posts == 0:
            return {
                "week_start": week_start,
                "total_posts": 0,
                "message": "No posts this week"
            }
        
        post_ids = [p.id for p in posts]
        
        # Get latest checkback for each post
        total_views = 0
        total_likes = 0
        total_comments = 0
        total_shares = 0
        total_saves = 0
        total_profile_taps = 0
        total_link_clicks = 0
        
        engaged_user_ids = set()
        platform_reach = {}
        platform_posts = {}
        
        for post in posts:
            # Get latest checkback
            latest = self.db.query(PlatformCheckback)\
                .filter_by(platform_post_id=post.id)\
                .order_by(PlatformCheckback.checkback_h.desc())\
                .first()
            
            if latest:
                total_views += latest.views or 0
                total_likes += latest.likes or 0
                total_comments += latest.comments or 0
                total_shares += latest.shares or 0
                total_saves += latest.saves or 0
                total_profile_taps += latest.profile_taps or 0
                total_link_clicks += latest.link_clicks or 0
                
                # Track engaged users (simplified - in production, need actual user IDs)
                engaged_users = (latest.likes or 0) + (latest.comments or 0) + \
                               (latest.shares or 0) + (latest.saves or 0) + \
                               (latest.profile_taps or 0)
                engaged_user_ids.add(post.platform_post_id)  # Proxy for now
            
            # Track by platform
            platform = post.platform
            platform_reach[platform] = platform_reach.get(platform, 0) + (latest.views if latest else 0)
            platform_posts[platform] = platform_posts.get(platform, 0) + 1
        
        # Calculate North Star Metrics
        # NSM #1: Engaged Reach (unique users who engaged)
        engaged_reach = len(engaged_user_ids)
        
        # NSM #2: Content Leverage Score
        meaningful_engagement = total_comments + total_saves + total_shares + total_profile_taps
        content_leverage_score = meaningful_engagement / total_posts if total_posts > 0 else 0
        
        # NSM #3: Warm Lead Flow
        warm_lead_flow = total_link_clicks  # + dm_starts + signups (when available)
        
        # Calculate average retention
        avg_retention = self.db.query(func.avg(PlatformCheckback.avg_watch_pct))\
            .filter(PlatformCheckback.platform_post_id.in_(post_ids))\
            .scalar() or 0
        
        # Create/update weekly metric record
        weekly_metric = self.db.query(WeeklyMetric).filter_by(
            week_start_date=week_start,
            user_id=user_id
        ).first()
        
        if not weekly_metric:
            weekly_metric = WeeklyMetric(
                week_start_date=week_start,
                user_id=user_id
            )
            self.db.add(weekly_metric)
        
        # Update metrics
        weekly_metric.engaged_reach = engaged_reach
        weekly_metric.content_leverage_score = content_leverage_score
        weekly_metric.warm_lead_flow = warm_lead_flow
        weekly_metric.total_posts = total_posts
        weekly_metric.total_views = total_views
        weekly_metric.avg_retention_pct = avg_retention
        weekly_metric.platform_reach = platform_reach
        weekly_metric.platform_posts = platform_posts
        
        self.db.commit()
        
        logger.info(f"Weekly metrics calculated: {engaged_reach} engaged, CLS: {content_leverage_score:.2f}")
        
        return {
            "week_start": week_start,
            "engaged_reach": engaged_reach,
            "content_leverage_score": round(content_leverage_score, 2),
            "warm_lead_flow": warm_lead_flow,
            "total_posts": total_posts,
            "total_views": total_views,
            "avg_retention_pct": round(avg_retention, 3) if avg_retention else 0,
            "platform_breakdown": platform_reach
        }
    
    def get_overview_dashboard(
        self,
        weeks: int = 4,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Get overview dashboard data
        
        Args:
            weeks: Number of weeks to include
            user_id: Optional user ID filter
            
        Returns:
            Dashboard data
        """
        # Get weekly metrics for last N weeks
        end_date = date.today()
        start_date = end_date - timedelta(weeks=weeks)
        
        weekly_data = self.db.query(WeeklyMetric)\
            .filter(WeeklyMetric.week_start_date >= start_date)\
            .order_by(WeeklyMetric.week_start_date.desc())\
            .all()
        
        if not weekly_data:
            return {
                "message": "No data available",
                "weeks_analyzed": 0
            }
        
        # Latest week metrics
        latest = weekly_data[0] if weekly_data else None
        
        # Calculate trends
        if len(weekly_data) >= 2:
            prev = weekly_data[1]
            engaged_reach_delta = ((latest.engaged_reach - prev.engaged_reach) / prev.engaged_reach * 100) if prev.engaged_reach > 0 else 0
            cls_delta = ((latest.content_leverage_score - prev.content_leverage_score) / prev.content_leverage_score * 100) if prev.content_leverage_score > 0 else 0
            warm_lead_delta = ((latest.warm_lead_flow - prev.warm_lead_flow) / prev.warm_lead_flow * 100) if prev.warm_lead_flow > 0 else 0
        else:
            engaged_reach_delta = 0
            cls_delta = 0
            warm_lead_delta = 0
        
        return {
            "current_week": {
                "week_start": latest.week_start_date if latest else None,
                "engaged_reach": latest.engaged_reach if latest else 0,
                "engaged_reach_delta_pct": round(engaged_reach_delta, 1),
                "content_leverage_score": round(latest.content_leverage_score, 2) if latest else 0,
                "cls_delta_pct": round(cls_delta, 1),
                "warm_lead_flow": latest.warm_lead_flow if latest else 0,
                "warm_lead_delta_pct": round(warm_lead_delta, 1),
                "total_posts": latest.total_posts if latest else 0,
                "total_views": latest.total_views if latest else 0
            },
            "platform_breakdown": latest.platform_reach if latest else {},
            "weeks_analyzed": len(weekly_data),
            "trend_data": [
                {
                    "week": str(wm.week_start_date),
                    "engaged_reach": wm.engaged_reach,
                    "content_leverage_score": round(wm.content_leverage_score, 2),
                    "warm_lead_flow": wm.warm_lead_flow,
                    "posts": wm.total_posts
                }
                for wm in weekly_data
            ]
        }
    
    def get_post_performance_detail(
        self,
        post_id: uuid.UUID
    ) -> Dict[str, Any]:
        """
        Get detailed performance analysis for a post
        
        Args:
            post_id: Platform post ID
            
        Returns:
            Detailed performance data
        """
        post = self.db.query(PlatformPost).filter_by(id=post_id).first()
        
        if not post:
            return {"error": "Post not found"}
        
        # Get all checkbacks
        checkbacks = self.db.query(PlatformCheckback)\
            .filter_by(platform_post_id=post_id)\
            .order_by(PlatformCheckback.checkback_h)\
            .all()
        
        # Get comments summary
        comments = self.db.query(PostComment)\
            .filter_by(platform_post_id=post_id)\
            .all()
        
        avg_sentiment = sum(c.sentiment_score for c in comments if c.sentiment_score) / len(comments) if comments else None
        
        # Categorize comments
        positive = sum(1 for c in comments if c.sentiment_score and c.sentiment_score > 0.3)
        negative = sum(1 for c in comments if c.sentiment_score and c.sentiment_score < -0.3)
        neutral = len(comments) - positive - negative
        
        # CTA responses
        cta_responses = sum(1 for c in comments if c.is_cta_response)
        
        return {
            "post": {
                "id": str(post.id),
                "platform": post.platform,
                "title": post.title,
                "published_at": post.published_at,
                "post_url": post.platform_url
            },
            "metrics_timeline": [
                {
                    "checkback_hours": cb.checkback_h,
                    "views": cb.views,
                    "likes": cb.likes,
                    "comments": cb.comments,
                    "shares": cb.shares,
                    "saves": cb.saves,
                    "engagement_rate": (cb.like_rate or 0) + (cb.comment_rate or 0) + (cb.share_rate or 0)
                }
                for cb in checkbacks
            ],
            "comments_analysis": {
                "total": len(comments),
                "avg_sentiment": round(avg_sentiment, 2) if avg_sentiment else None,
                "positive": positive,
                "negative": negative,
                "neutral": neutral,
                "cta_responses": cta_responses
            },
            "latest_metrics": {
                "views": checkbacks[-1].views if checkbacks else 0,
                "engagement_rate": ((checkbacks[-1].like_rate or 0) + (checkbacks[-1].comment_rate or 0) + (checkbacks[-1].share_rate or 0)) if checkbacks else 0
            } if checkbacks else None
        }
