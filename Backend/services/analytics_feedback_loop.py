"""
Analytics Feedback Loop Service (ARCH-006)
===========================================
AI-powered analysis of content performance with optimization suggestions.

Features:
- Collects engagement metrics from all platforms
- AI analysis of what works and what doesn't
- Generates actionable optimization suggestions
- Learns from historical performance patterns
- Provides real-time feedback to content strategy

Integration:
- Monitors MasterOrchestrator pipeline outputs
- EventBus notifications for performance insights
- Database persistence for learning history
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from sqlalchemy import create_engine, text

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("OpenAI not available for analytics feedback")

try:
    from services.event_bus import EventBus, Topics
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class PerformanceRating(str, Enum):
    """Performance rating categories."""
    EXCELLENT = "excellent"  # Top 20%
    GOOD = "good"           # Top 20-50%
    AVERAGE = "average"     # Middle 50-80%
    POOR = "poor"          # Bottom 20%


class AnalyticsFeedbackLoop:
    """
    AI-powered analytics feedback system (ARCH-006).

    Analyzes content performance and provides optimization suggestions
    to improve future content strategy.
    """

    _instance: Optional['AnalyticsFeedbackLoop'] = None

    def __init__(self, event_bus: Optional['EventBus'] = None):
        self.event_bus = event_bus
        if EVENT_BUS_AVAILABLE and not self.event_bus:
            self.event_bus = EventBus.get_instance()

        # OpenAI client
        self.openai_client = None
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)

        # Database connection
        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)

        logger.info("🔄 Analytics Feedback Loop initialized (ARCH-006)")

    @classmethod
    def get_instance(cls, event_bus: Optional['EventBus'] = None) -> 'AnalyticsFeedbackLoop':
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance

    async def analyze_pipeline_performance(
        self,
        pipeline_id: str,
        wait_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Analyze performance of a pipeline's content after waiting period.

        Args:
            pipeline_id: Pipeline to analyze
            wait_hours: Hours to wait before analysis (default 24h for data collection)

        Returns:
            Analysis results with AI insights
        """
        # Get pipeline info
        pipeline_info = await self._get_pipeline_info(pipeline_id)
        if not pipeline_info:
            return {"error": "Pipeline not found"}

        # Check if enough time has passed
        started_at = pipeline_info.get("started_at")
        if started_at:
            elapsed = datetime.now(timezone.utc) - started_at
            if elapsed < timedelta(hours=wait_hours):
                return {
                    "status": "waiting",
                    "message": f"Waiting {wait_hours - elapsed.total_seconds() / 3600:.1f} more hours for data"
                }

        # Collect performance metrics
        metrics = await self._collect_performance_metrics(pipeline_id)

        # Analyze with AI
        analysis = await self._generate_ai_insights(
            pipeline_info=pipeline_info,
            metrics=metrics
        )

        # Rate performance
        rating = self._rate_performance(metrics)

        # Generate optimization suggestions
        suggestions = await self._generate_optimization_suggestions(
            pipeline_info=pipeline_info,
            metrics=metrics,
            rating=rating
        )

        # Save feedback to database
        feedback_id = await self._save_feedback(
            pipeline_id=pipeline_id,
            metrics=metrics,
            rating=rating,
            insights=analysis,
            suggestions=suggestions
        )

        # Emit event
        if self.event_bus and EVENT_BUS_AVAILABLE:
            await self.event_bus.publish(
                "analytics.feedback.generated",
                {
                    "pipeline_id": pipeline_id,
                    "feedback_id": feedback_id,
                    "rating": rating,
                    "total_views": metrics.get("total_views", 0),
                    "avg_engagement_rate": metrics.get("avg_engagement_rate", 0)
                },
                source="analytics_feedback_loop"
            )

        return {
            "feedback_id": feedback_id,
            "pipeline_id": pipeline_id,
            "rating": rating,
            "metrics": metrics,
            "ai_insights": analysis,
            "optimization_suggestions": suggestions,
            "analyzed_at": datetime.now(timezone.utc).isoformat()
        }

    async def _get_pipeline_info(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get pipeline information from database."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        pipeline_id, theme, num_parts, character,
                        publish_platforms, started_at, completed_at,
                        stitched_video, analysis_result, published_count
                    FROM orchestrator_pipelines
                    WHERE pipeline_id = :pipeline_id
                """), {"pipeline_id": pipeline_id})

                row = result.fetchone()
                if row:
                    return {
                        "pipeline_id": row[0],
                        "theme": row[1],
                        "num_parts": row[2],
                        "character": row[3],
                        "platforms": row[4],
                        "started_at": row[5],
                        "completed_at": row[6],
                        "stitched_video": row[7],
                        "analysis_result": row[8],
                        "published_count": row[9] or 0
                    }
        except Exception as e:
            logger.error(f"Failed to get pipeline info: {e}")

        return None

    async def _collect_performance_metrics(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Collect performance metrics across all platforms for a pipeline.

        Aggregates: views, likes, comments, shares, engagement rates
        """
        try:
            with self.engine.connect() as conn:
                # This query assumes there's a way to link platform posts back to pipeline
                # You may need to adjust based on actual schema
                result = conn.execute(text("""
                    SELECT
                        COUNT(DISTINCT pp.post_id) as post_count,
                        COUNT(DISTINCT pp.platform) as platform_count,
                        SUM(pm.views) as total_views,
                        SUM(pm.likes) as total_likes,
                        SUM(pm.comments) as total_comments,
                        SUM(pm.shares) as total_shares,
                        AVG(pm.engagement_rate) as avg_engagement_rate,
                        ARRAY_AGG(DISTINCT pp.platform) as platforms
                    FROM platform_posts pp
                    LEFT JOIN performance_metrics pm ON pp.post_id = pm.post_id
                    WHERE pp.platform_post_url LIKE :pipeline_pattern
                       OR pp.blotato_post_id IN (
                           SELECT DISTINCT blotato_post_id
                           FROM platform_posts
                           WHERE caption_used LIKE :caption_pattern
                       )
                """), {
                    "pipeline_pattern": f"%{pipeline_id}%",
                    "caption_pattern": f"%{pipeline_id}%"
                })

                row = result.fetchone()
                if row:
                    return {
                        "post_count": row[0] or 0,
                        "platform_count": row[1] or 0,
                        "total_views": row[2] or 0,
                        "total_likes": row[3] or 0,
                        "total_comments": row[4] or 0,
                        "total_shares": row[5] or 0,
                        "avg_engagement_rate": float(row[6]) if row[6] else 0.0,
                        "platforms": row[7] or []
                    }
        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")

        return {
            "post_count": 0,
            "platform_count": 0,
            "total_views": 0,
            "total_likes": 0,
            "total_comments": 0,
            "total_shares": 0,
            "avg_engagement_rate": 0.0,
            "platforms": []
        }

    def _rate_performance(self, metrics: Dict[str, Any]) -> str:
        """
        Rate performance based on metrics.

        Uses engagement rate as primary metric with views as secondary.
        """
        engagement_rate = metrics.get("avg_engagement_rate", 0)
        total_views = metrics.get("total_views", 0)

        # Engagement rate thresholds (adjust based on your benchmarks)
        if engagement_rate >= 5.0 and total_views >= 10000:
            return PerformanceRating.EXCELLENT
        elif engagement_rate >= 3.0 and total_views >= 5000:
            return PerformanceRating.GOOD
        elif engagement_rate >= 1.5 and total_views >= 1000:
            return PerformanceRating.AVERAGE
        else:
            return PerformanceRating.POOR

    async def _generate_ai_insights(
        self,
        pipeline_info: Dict[str, Any],
        metrics: Dict[str, Any]
    ) -> str:
        """
        Generate AI insights about what worked and what didn't.
        """
        if not self.openai_client or not OPENAI_AVAILABLE:
            return "AI insights unavailable (OpenAI not configured)"

        theme = pipeline_info.get("theme", "Unknown")
        platforms = metrics.get("platforms", [])
        engagement_rate = metrics.get("avg_engagement_rate", 0)
        total_views = metrics.get("total_views", 0)

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a social media analytics expert. Analyze performance data and provide actionable insights about what worked and what didn't. Be specific and data-driven."""
                    },
                    {
                        "role": "user",
                        "content": f"""Analyze this content performance:

Theme: {theme}
Platforms: {', '.join(platforms)}
Total Views: {total_views:,}
Engagement Rate: {engagement_rate:.2f}%
Posts: {metrics.get('post_count', 0)}

Provide 2-3 key insights about:
1. What aspects likely resonated with the audience
2. What could be improved
3. Platform-specific observations"""
                    }
                ],
                temperature=0.7,
                max_tokens=300
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"AI insights generation failed: {e}")
            return "Unable to generate AI insights at this time"

    async def _generate_optimization_suggestions(
        self,
        pipeline_info: Dict[str, Any],
        metrics: Dict[str, Any],
        rating: str
    ) -> List[Dict[str, str]]:
        """
        Generate specific, actionable optimization suggestions.
        """
        if not self.openai_client or not OPENAI_AVAILABLE:
            return []

        theme = pipeline_info.get("theme", "Unknown")

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a content optimization expert. Generate specific, actionable recommendations. Return JSON array of objects with "category" and "suggestion" fields."""
                    },
                    {
                        "role": "user",
                        "content": f"""Generate 3-5 optimization suggestions for:

Theme: {theme}
Performance Rating: {rating}
Engagement Rate: {metrics.get('avg_engagement_rate', 0):.2f}%
Views: {metrics.get('total_views', 0):,}

Focus on: content structure, posting times, platform optimization, hook improvement, CTA effectiveness.

Return JSON format:
[
  {{"category": "Content", "suggestion": "..."}},
  {{"category": "Timing", "suggestion": "..."}},
  ...
]"""
                    }
                ],
                temperature=0.8,
                max_tokens=400,
                response_format={"type": "json_object"}
            )

            import json
            result = json.loads(response.choices[0].message.content)

            # Handle both array and object responses
            if isinstance(result, dict):
                suggestions = result.get("suggestions", [])
            else:
                suggestions = result

            return suggestions if isinstance(suggestions, list) else []

        except Exception as e:
            logger.error(f"Optimization suggestions generation failed: {e}")
            return [
                {
                    "category": "General",
                    "suggestion": "Continue experimenting with different content formats and posting times"
                }
            ]

    async def _save_feedback(
        self,
        pipeline_id: str,
        metrics: Dict[str, Any],
        rating: str,
        insights: str,
        suggestions: List[Dict[str, str]]
    ) -> int:
        """Save analytics feedback to database."""
        try:
            import json

            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO analytics_feedback (
                        pipeline_id, platform, views, likes, comments, shares,
                        engagement_rate, performance_rating, ai_insights,
                        optimization_suggestions, measured_at, analyzed_at
                    ) VALUES (
                        :pipeline_id, :platform, :views, :likes, :comments, :shares,
                        :engagement_rate, :performance_rating, :ai_insights,
                        :optimization_suggestions, NOW(), NOW()
                    )
                    RETURNING id
                """), {
                    "pipeline_id": pipeline_id,
                    "platform": "multi-platform",  # Aggregated across platforms
                    "views": metrics.get("total_views", 0),
                    "likes": metrics.get("total_likes", 0),
                    "comments": metrics.get("total_comments", 0),
                    "shares": metrics.get("total_shares", 0),
                    "engagement_rate": metrics.get("avg_engagement_rate", 0),
                    "performance_rating": rating,
                    "ai_insights": insights,
                    "optimization_suggestions": json.dumps(suggestions)
                })
                conn.commit()

                feedback_id = result.fetchone()[0]
                logger.info(f"📊 Feedback saved: feedback_id={feedback_id}, rating={rating}")
                return feedback_id

        except Exception as e:
            logger.error(f"Failed to save feedback: {e}")
            return -1

    def get_historical_insights(
        self,
        days: int = 30,
        min_rating: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get historical performance insights for learning.

        Args:
            days: Number of days to look back
            min_rating: Filter by minimum performance rating

        Returns:
            List of historical feedback entries
        """
        start_date = datetime.now(timezone.utc) - timedelta(days=days)

        try:
            with self.engine.connect() as conn:
                query = """
                    SELECT
                        id, pipeline_id, performance_rating,
                        views, engagement_rate, ai_insights,
                        optimization_suggestions, analyzed_at
                    FROM analytics_feedback
                    WHERE analyzed_at >= :start_date
                """

                params = {"start_date": start_date}

                if min_rating:
                    # Filter by rating hierarchy: excellent > good > average > poor
                    rating_order = {
                        PerformanceRating.EXCELLENT: 4,
                        PerformanceRating.GOOD: 3,
                        PerformanceRating.AVERAGE: 2,
                        PerformanceRating.POOR: 1
                    }
                    min_level = rating_order.get(min_rating, 1)
                    query += " AND performance_rating IN (:ratings)"

                    ratings = [r for r, level in rating_order.items() if level >= min_level]
                    params["ratings"] = tuple(ratings)

                query += " ORDER BY analyzed_at DESC"

                result = conn.execute(text(query), params)

                insights = []
                for row in result:
                    import json
                    insights.append({
                        "feedback_id": row[0],
                        "pipeline_id": row[1],
                        "rating": row[2],
                        "views": row[3] or 0,
                        "engagement_rate": float(row[4]) if row[4] else 0.0,
                        "ai_insights": row[5],
                        "suggestions": json.loads(row[6]) if row[6] else [],
                        "analyzed_at": row[7].isoformat() if row[7] else None
                    })

                return insights

        except Exception as e:
            logger.error(f"Failed to get historical insights: {e}")
            return []

    def get_top_performing_themes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get themes with best performance for future content ideas."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        op.theme,
                        COUNT(*) as usage_count,
                        AVG(af.views) as avg_views,
                        AVG(af.engagement_rate) as avg_engagement_rate,
                        MODE() WITHIN GROUP (ORDER BY af.performance_rating) as most_common_rating
                    FROM analytics_feedback af
                    JOIN orchestrator_pipelines op ON af.pipeline_id = op.pipeline_id
                    WHERE af.performance_rating IN ('excellent', 'good')
                    GROUP BY op.theme
                    HAVING COUNT(*) >= 1
                    ORDER BY avg_engagement_rate DESC, avg_views DESC
                    LIMIT :limit
                """), {"limit": limit})

                themes = []
                for row in result:
                    themes.append({
                        "theme": row[0],
                        "usage_count": row[1],
                        "avg_views": int(row[2]) if row[2] else 0,
                        "avg_engagement_rate": float(row[3]) if row[3] else 0.0,
                        "most_common_rating": row[4]
                    })

                return themes

        except Exception as e:
            logger.error(f"Failed to get top themes: {e}")
            return []


# Convenience function
def get_feedback_loop() -> AnalyticsFeedbackLoop:
    """Get singleton instance of analytics feedback loop."""
    return AnalyticsFeedbackLoop.get_instance()
