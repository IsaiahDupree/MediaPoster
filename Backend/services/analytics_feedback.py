"""
Analytics Feedback Service (ARCH-006)
======================================
AI-powered analytics feedback loop that learns from post performance.

Features:
    - Analyzes post performance metrics (views, engagement, conversions)
    - Identifies patterns in successful vs. unsuccessful content
    - Generates insights and recommendations
    - Feeds learnings back into content generation
    - Auto-optimizes future content based on performance

Usage:
    feedback = get_analytics_feedback()
    await feedback.start()

    # Analyze post performance
    insights = await feedback.analyze_post_performance(post_id)

    # Get optimization recommendations
    recommendations = feedback.get_recommendations(
        platform="tiktok",
        content_type="hook"
    )
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from services.event_bus import EventBus, Event, Topics

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    """Performance classification levels"""
    VIRAL = "viral"  # Top 10%
    HIGH = "high"  # Top 25%
    MEDIUM = "medium"  # Top 50%
    LOW = "low"  # Bottom 50%
    POOR = "poor"  # Bottom 25%


@dataclass
class PostPerformance:
    """Post performance metrics"""
    post_id: str
    platform: str
    account_id: str
    published_at: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    engagement_rate: float = 0.0
    viral_score: float = 0.0
    performance_level: PerformanceLevel = PerformanceLevel.MEDIUM


@dataclass
class ContentPattern:
    """Identified content pattern"""
    pattern_id: str
    name: str
    description: str
    performance_level: PerformanceLevel
    occurrence_count: int
    avg_viral_score: float
    examples: List[str]
    recommendation: str


@dataclass
class ContentRecommendation:
    """Content optimization recommendation"""
    name: str
    category: str
    description: str
    confidence: float
    supporting_data: Dict[str, Any]


class AnalyticsFeedback:
    """
    AI-powered analytics feedback loop for content optimization.

    Integrates with:
        - Master Orchestrator (ARCH-001) for pipeline optimization
        - OfferTracker (ARCH-005) for conversion tracking
        - ContentAnalyzer for pattern detection
        - Twitter/Content services for optimization
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus.get_instance()
        self.post_performances: Dict[str, PostPerformance] = {}
        self.content_patterns: Dict[str, ContentPattern] = {}
        self.recommendations: List[ContentRecommendation] = []
        self._subscriptions: List[str] = []  # List of subscribed topics
        self._running = False
        self._analysis_interval = 3600  # Analyze every hour

        logger.info("[AnalyticsFeedback] Initialized")

    async def start(self) -> None:
        """Start the feedback loop service"""
        if self._running:
            logger.warning("[AnalyticsFeedback] Already running")
            return

        self._running = True

        # Subscribe to analytics events
        self.event_bus.subscribe(Topics.CHECKBACK_COMPLETED, self._handle_checkback)
        self.event_bus.subscribe(Topics.PUBLISH_COMPLETED, self._handle_publish)

        # Track subscriptions for testing
        self._subscriptions = [Topics.CHECKBACK_COMPLETED, Topics.PUBLISH_COMPLETED]

        logger.info("[AnalyticsFeedback] Started and subscribed to analytics events")

        # Start periodic analysis
        asyncio.create_task(self._periodic_analysis())

    async def stop(self) -> None:
        """Stop the feedback loop service"""
        self._running = False
        logger.info("[AnalyticsFeedback] Stopped")

    async def _periodic_analysis(self):
        """Periodically analyze performance and update recommendations"""
        while self._running:
            try:
                await asyncio.sleep(self._analysis_interval)
                await self._update_recommendations()
            except Exception as e:
                logger.error(f"[AnalyticsFeedback] Periodic analysis error: {e}")

    async def _handle_checkback(self, event: Event):
        """Handle checkback completion event"""
        post_id = event.payload.get("post_id")
        metrics = event.payload.get("metrics", {})

        logger.debug(f"[AnalyticsFeedback] Checkback for {post_id}: {metrics}")

        # Store performance data
        self.post_performances[post_id] = PostPerformance(
            post_id=post_id,
            platform=metrics.get("platform", "unknown"),
            account_id=metrics.get("account_id", ""),
            published_at=metrics.get("published_at", ""),
            views=metrics.get("views", 0),
            likes=metrics.get("likes", 0),
            comments=metrics.get("comments", 0),
            shares=metrics.get("shares", 0),
            engagement_rate=metrics.get("engagement_rate", 0.0),
            viral_score=metrics.get("viral_score", 0.0)
        )

        # Trigger analysis if we have enough data
        if len(self.post_performances) >= 10:
            await self._update_recommendations()

    async def _handle_publish(self, event: Event):
        """Handle publish completion event"""
        post_id = event.payload.get("media_id")
        platform = event.payload.get("platform")

        logger.debug(f"[AnalyticsFeedback] Post published: {post_id} on {platform}")

    async def analyze_post_performance(self, post_id: str) -> Optional[Dict]:
        """
        Analyze the performance of a specific post.

        Args:
            post_id: Post identifier

        Returns:
            Performance analysis dict or None
        """
        if post_id not in self.post_performances:
            logger.warning(f"[AnalyticsFeedback] No performance data for {post_id}")
            return None

        perf = self.post_performances[post_id]

        # Calculate performance level
        if perf.viral_score >= 90:
            level = PerformanceLevel.VIRAL
        elif perf.viral_score >= 75:
            level = PerformanceLevel.HIGH
        elif perf.viral_score >= 50:
            level = PerformanceLevel.MEDIUM
        elif perf.viral_score >= 25:
            level = PerformanceLevel.LOW
        else:
            level = PerformanceLevel.POOR

        return {
            "post_id": post_id,
            "platform": perf.platform,
            "performance_level": level.value,
            "viral_score": perf.viral_score,
            "engagement_rate": perf.engagement_rate,
            "views": perf.views,
            "metrics": {
                "likes": perf.likes,
                "comments": perf.comments,
                "shares": perf.shares
            }
        }

    def get_recommendations(
        self,
        platform: Optional[str] = None,
        content_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get content optimization recommendations.

        Args:
            platform: Filter by platform
            content_type: Filter by content type
            limit: Max recommendations to return

        Returns:
            List of recommendation dicts
        """
        recommendations = []

        if len(self.post_performances) < 10:
            # Not enough data yet
            recommendations.append({
                "name": "Collect More Data",
                "category": "general",
                "description": f"Need at least 10 posts to generate insights. Currently have {len(self.post_performances)}.",
                "confidence": 1.0,
                "action": "continue_posting"
            })
            return recommendations

        # Analyze top-performing posts
        sorted_posts = sorted(
            self.post_performances.values(),
            key=lambda x: x.viral_score,
            reverse=True
        )

        top_posts = sorted_posts[:3]
        avg_viral_score = sum(p.viral_score for p in top_posts) / len(top_posts)

        # Generate recommendations based on patterns
        if avg_viral_score >= 80:
            recommendations.append({
                "name": "Continue Current Strategy",
                "category": "strategy",
                "description": f"Your content is performing exceptionally well (avg viral score: {avg_viral_score:.1f}). Keep doing what you're doing!",
                "confidence": 0.9,
                "action": "maintain"
            })
        else:
            recommendations.append({
                "name": "Experiment with New Formats",
                "category": "strategy",
                "description": f"Current avg viral score: {avg_viral_score:.1f}. Try testing new content formats or hooks.",
                "confidence": 0.7,
                "action": "experiment"
            })

        # Platform-specific recommendations
        if platform:
            platform_posts = [p for p in self.post_performances.values() if p.platform == platform]
            if platform_posts:
                avg_platform_score = sum(p.viral_score for p in platform_posts) / len(platform_posts)
                recommendations.append({
                    "name": f"Optimize {platform.title()} Content",
                    "category": "platform",
                    "description": f"{platform.title()} avg score: {avg_platform_score:.1f}",
                    "confidence": 0.8,
                    "action": "optimize",
                    "platform": platform
                })

        # Engagement rate recommendations
        avg_engagement = sum(p.engagement_rate for p in self.post_performances.values()) / len(self.post_performances)
        if avg_engagement < 5.0:
            recommendations.append({
                "name": "Improve Engagement Tactics",
                "category": "engagement",
                "description": f"Avg engagement rate: {avg_engagement:.2f}%. Try stronger CTAs or questions.",
                "confidence": 0.75,
                "action": "improve_ctas"
            })

        return recommendations[:limit]

    async def _update_recommendations(self):
        """Update recommendations based on latest performance data"""
        if len(self.post_performances) < 5:
            logger.debug("[AnalyticsFeedback] Not enough data for recommendations")
            return

        logger.info(f"[AnalyticsFeedback] Updating recommendations based on {len(self.post_performances)} posts")

        # Generate new recommendations
        self.recommendations = [
            ContentRecommendation(
                name=rec["name"],
                category=rec["category"],
                description=rec["description"],
                confidence=rec["confidence"],
                supporting_data=rec
            )
            for rec in self.get_recommendations()
        ]

        logger.info(f"[AnalyticsFeedback] Generated {len(self.recommendations)} recommendations")

    def get_performance_summary(self) -> Dict:
        """Get overall performance summary"""
        if not self.post_performances:
            return {
                "total_posts": 0,
                "avg_viral_score": 0,
                "avg_engagement_rate": 0
            }

        posts = list(self.post_performances.values())

        return {
            "total_posts": len(posts),
            "avg_viral_score": sum(p.viral_score for p in posts) / len(posts),
            "avg_engagement_rate": sum(p.engagement_rate for p in posts) / len(posts),
            "total_views": sum(p.views for p in posts),
            "total_likes": sum(p.likes for p in posts),
            "total_comments": sum(p.comments for p in posts),
            "total_shares": sum(p.shares for p in posts)
        }


# Global instance
_analytics_feedback_instance: Optional[AnalyticsFeedback] = None


def get_analytics_feedback(event_bus: Optional[EventBus] = None) -> AnalyticsFeedback:
    """Get or create the global AnalyticsFeedback instance"""
    global _analytics_feedback_instance

    if _analytics_feedback_instance is None:
        _analytics_feedback_instance = AnalyticsFeedback(event_bus)

    return _analytics_feedback_instance
