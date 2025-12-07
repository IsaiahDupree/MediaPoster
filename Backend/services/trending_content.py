"""
Trending Content Discovery Service
Analyzes TikTok trends to provide content recommendations
"""
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from services.api_rate_limiter import CachedTikTokScraperAPI
from database.models import ContentInsight
import uuid

logger = logging.getLogger(__name__)


class TrendingContentService:
    """
    Service for discovering and analyzing trending content
    Integrates with TikTok Scraper to provide actionable insights
    """
    
    def __init__(self, db: Session, api_key: Optional[str] = None):
        """
        Initialize trending content service
        
        Args:
            db: Database session
            api_key: RapidAPI key for TikTok Scraper
        """
        self.db = db
        self.tiktok_api = CachedTikTokScraperAPI(db=db, api_key=api_key)
    
    async def discover_trending_topics(
        self,
        region: str = "US",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Discover what's trending on TikTok right now
        
        Args:
            region: Region code
            limit: Number of videos to analyze
            
        Returns:
            List of trending topics with metrics
        """
        topics = await self.tiktok_api.analyze_trending_topics(
            region=region,
            limit=limit
        )
        
        # Store insights in database
        for topic in topics[:10]:  # Store top 10
            self._store_trending_insight(topic, region)
        
        return topics
    
    async def analyze_competitor_content(
        self,
        username: str,
        count: int = 20
    ) -> Dict[str, Any]:
        """
        Analyze a competitor's content strategy
        
        Args:
            username: TikTok username to analyze
            count: Number of posts to analyze
            
        Returns:
            Analysis of competitor's content
        """
        result = await self.tiktok_api.get_user_posts(
            username=username,
            count=count
        )
        
        videos = result.get("videos", [])
        user = result.get("user", {})
        
        if not videos:
            return {"error": "No videos found"}
        
        # Analyze performance patterns
        total_views = sum(v["stats"]["views"] for v in videos)
        total_likes = sum(v["stats"]["likes"] for v in videos)
        total_shares = sum(v["stats"]["shares"] for v in videos)
        
        avg_views = total_views / len(videos)
        engagement_rate = (total_likes + total_shares) / total_views if total_views > 0 else 0
        
        # Find most common hashtags
        hashtag_usage = {}
        for video in videos:
            for tag in video.get("hashtags", []):
                hashtag_usage[tag] = hashtag_usage.get(tag, 0) + 1
        
        top_hashtags = sorted(
            hashtag_usage.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Find best performing content
        best_videos = sorted(
            videos,
            key=lambda x: x["stats"]["views"],
            reverse=True
        )[:5]
        
        return {
            "username": username,
            "user_info": user,
            "total_videos_analyzed": len(videos),
            "avg_views_per_video": int(avg_views),
            "engagement_rate": round(engagement_rate * 100, 2),
            "top_hashtags": [{"tag": tag, "count": count} for tag, count in top_hashtags],
            "best_performing_videos": [
                {
                    "id": v["id"],
                    "description": v["description"][:100],
                    "views": v["stats"]["views"],
                    "likes": v["stats"]["likes"],
                    "url": v["url"]
                }
                for v in best_videos
            ]
        }
    
    async def get_hashtag_insights(
        self,
        hashtag: str,
        count: int = 30
    ) -> Dict[str, Any]:
        """
        Get detailed insights about a specific hashtag
        
        Args:
            hashtag: Hashtag to analyze
            count: Number of videos to analyze
            
        Returns:
            Hashtag performance insights
        """
        result = await self.tiktok_api.search_hashtag(
            hashtag=hashtag,
            count=count
        )
        
        videos = result.get("videos", [])
        
        if not videos:
            return {"error": "No videos found for hashtag"}
        
        total_views = sum(v["stats"]["views"] for v in videos)
        total_likes = sum(v["stats"]["likes"] for v in videos)
        total_shares = sum(v["stats"]["shares"] for v in videos)
        
        avg_views = total_views / len(videos)
        engagement_rate = (total_likes + total_shares) / total_views if total_views > 0 else 0
        
        # Analyze posting patterns
        posting_times = [
            datetime.fromtimestamp(v["create_time"]).hour
            for v in videos
            if v.get("create_time")
        ]
        
        best_time = max(set(posting_times), key=posting_times.count) if posting_times else None
        
        return {
            "hashtag": hashtag,
            "total_videos": len(videos),
            "avg_views": int(avg_views),
            "engagement_rate": round(engagement_rate * 100, 2),
            "total_views": total_views,
            "total_engagement": total_likes + total_shares,
            "best_posting_hour": best_time,
            "recommendation": self._generate_hashtag_recommendation(
                hashtag,
                avg_views,
                engagement_rate
            )
        }
    
    async def generate_content_ideas(
        self,
        region: str = "US",
        niche: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate content ideas based on trending content
        
        Args:
            region: Region to analyze
            niche: Optional niche/topic filter
            
        Returns:
            List of content ideas with reasoning
        """
        trending_videos = await self.tiktok_api.get_trending_feed(
            region=region,
            count=30
        )
        
        if not trending_videos:
            return []
        
        ideas = []
        
        # Analyze trending videos for patterns
        for video in trending_videos[:10]:
            idea = {
                "title": f"Create content similar to: {video['description'][:50]}...",
                "inspiration": {
                    "original_url": video["url"],
                    "views": video["stats"]["views"],
                    "engagement_rate": self._calculate_engagement_rate(video["stats"])
                },
                "suggested_hashtags": video["hashtags"][:5],
                "why_trending": f"This format is performing well with {video['stats']['views']:,} views and {self._calculate_engagement_rate(video['stats'])}% engagement",
                "action": "Put your own spin on this concept"
            }
            ideas.append(idea)
        
        return ideas
    
    def _store_trending_insight(
        self,
        topic_data: Dict[str, Any],
        region: str
    ):
        """Store trending topic as an insight in the database"""
        try:
            insight = ContentInsight(
                insight_type="trending_topic",
                title=f"Trending: #{topic_data['hashtag']}",
                description=f"This hashtag is trending in {region} with {topic_data['video_count']} recent videos",
                metric_impact=f"{round(topic_data['avg_engagement_rate'] * 100, 2)}% engagement rate",
                sample_size=topic_data['video_count'],
                confidence_score=min(topic_data['video_count'] / 50, 1.0),
                pattern_data={
                    "hashtag": topic_data['hashtag'],
                    "region": region,
                    "video_count": topic_data['video_count'],
                    "total_views": topic_data['total_views'],
                    "engagement_rate": topic_data['avg_engagement_rate']
                },
                recommended_action=f"Consider creating content using #{topic_data['hashtag']}",
                status="active",
                expires_at=datetime.now() + timedelta(days=3)  # Trends expire quickly
            )
            
            self.db.add(insight)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Error storing trending insight: {e}")
            self.db.rollback()
    
    def _calculate_engagement_rate(self, stats: Dict[str, int]) -> float:
        """Calculate engagement rate from video stats"""
        views = stats.get("views", 0)
        if views == 0:
            return 0.0
        
        engagement = stats.get("likes", 0) + stats.get("shares", 0) + stats.get("comments", 0)
        return round((engagement / views) * 100, 2)
    
    def _generate_hashtag_recommendation(
        self,
        hashtag: str,
        avg_views: int,
        engagement_rate: float
    ) -> str:
        """Generate recommendation for hashtag usage"""
        if avg_views > 1000000 and engagement_rate > 0.05:
            return f"#{hashtag} is a high-performing hashtag with excellent reach and engagement. Strongly recommend using it."
        elif avg_views > 500000:
            return f"#{hashtag} has good reach potential. Consider using it in combination with niche hashtags."
        elif engagement_rate > 0.08:
            return f"#{hashtag} has high engagement despite moderate reach. Great for building community."
        else:
            return f"#{hashtag} shows moderate performance. Use strategically with other stronger hashtags."
