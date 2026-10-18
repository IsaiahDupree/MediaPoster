"""
Cross-Platform Analytics Dashboard Service
============================================
Provides aggregated analytics data for the unified dashboard.
Queries posted_content, scheduled_posts, and content_metrics_snapshots
to surface: overview stats, top posts, growth trends, and content performance.

Integrates with:
- SmartPostingTimesService for heatmap data
- PostTracker for performance scores
- MultiPlatformAnalyticsAggregator for live API data
"""

import os
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple

from loguru import logger


class CrossPlatformDashboardService:
    """Aggregated analytics queries for the dashboard UI."""

    def __init__(self):
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres",
        )

    # ── Overview ─────────────────────────────────────────────────────────

    async def get_overview(self, period_days: int = 7) -> Dict[str, Any]:
        """
        Dashboard scorecard: total views, engagement, posts published,
        follower growth (all within period).
        """
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self.db_url)
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

            with engine.connect() as conn:
                # Posts published in period
                row = conn.execute(text("""
                    SELECT
                        COUNT(*) as posts_published,
                        COALESCE(SUM(views), 0) as total_views,
                        COALESCE(SUM(likes), 0) as total_likes,
                        COALESCE(SUM(comments), 0) as total_comments,
                        COALESCE(SUM(shares), 0) as total_shares,
                        COALESCE(SUM(saves), 0) as total_saves,
                        COALESCE(AVG(engagement_rate), 0) as avg_engagement_rate
                    FROM posted_content
                    WHERE COALESCE(published_at, posted_at) > :cutoff
                """), {"cutoff": cutoff}).fetchone()

                # Platform breakdown
                platform_rows = conn.execute(text("""
                    SELECT
                        platform,
                        COUNT(*) as posts,
                        COALESCE(SUM(views), 0) as views,
                        COALESCE(SUM(likes), 0) as likes,
                        COALESCE(AVG(engagement_rate), 0) as avg_er
                    FROM posted_content
                    WHERE COALESCE(published_at, posted_at) > :cutoff
                    GROUP BY platform
                    ORDER BY SUM(views) DESC NULLS LAST
                """), {"cutoff": cutoff}).fetchall()

                # Scheduled posts in queue
                queued = conn.execute(text("""
                    SELECT COUNT(*) FROM scheduled_posts
                    WHERE status IN ('scheduled', 'pending')
                      AND scheduled_time > NOW()
                """)).scalar() or 0

            return {
                "period_days": period_days,
                "posts_published": row[0] if row else 0,
                "total_views": int(row[1]) if row else 0,
                "total_likes": int(row[2]) if row else 0,
                "total_comments": int(row[3]) if row else 0,
                "total_shares": int(row[4]) if row else 0,
                "total_saves": int(row[5]) if row else 0,
                "avg_engagement_rate": round(float(row[6]), 4) if row else 0,
                "scheduled_queue": queued,
                "platform_breakdown": [
                    {
                        "platform": r[0],
                        "posts": r[1],
                        "views": int(r[2]),
                        "likes": int(r[3]),
                        "avg_engagement_rate": round(float(r[4]), 4),
                    }
                    for r in platform_rows
                ],
            }

        except Exception as e:
            logger.error(f"[Dashboard] Overview query failed: {e}")
            return {"error": str(e)}

    # ── Top Posts ────────────────────────────────────────────────────────

    async def get_top_posts(
        self, period_days: int = 7, limit: int = 10, sort_by: str = "views"
    ) -> List[Dict[str, Any]]:
        """Top-performing posts across all platforms."""
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self.db_url)
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

            order_col = {
                "views": "pc.views",
                "likes": "pc.likes",
                "engagement": "pc.engagement_rate",
                "comments": "pc.comments",
            }.get(sort_by, "pc.views")

            with engine.connect() as conn:
                rows = conn.execute(text(f"""
                    SELECT
                        pc.id,
                        pc.platform,
                        pc.platform_url,
                        pc.caption,
                        pc.title,
                        COALESCE(pc.published_at, pc.posted_at) as published_at,
                        COALESCE(pc.views, 0) as views,
                        COALESCE(pc.likes, 0) as likes,
                        COALESCE(pc.comments, 0) as comments,
                        COALESCE(pc.shares, 0) as shares,
                        COALESCE(pc.saves, 0) as saves,
                        COALESCE(pc.engagement_rate, 0) as engagement_rate
                    FROM posted_content pc
                    WHERE COALESCE(pc.published_at, pc.posted_at) > :cutoff
                    ORDER BY {order_col} DESC NULLS LAST
                    LIMIT :limit
                """), {"cutoff": cutoff, "limit": limit}).fetchall()

            return [
                {
                    "id": str(r[0]),
                    "platform": r[1],
                    "platform_url": r[2],
                    "caption_preview": (r[3] or r[4] or "")[:120],
                    "published_at": r[5].isoformat() if r[5] else None,
                    "views": r[6],
                    "likes": r[7],
                    "comments": r[8],
                    "shares": r[9],
                    "saves": r[10],
                    "engagement_rate": round(float(r[11]), 4),
                }
                for r in rows
            ]

        except Exception as e:
            logger.error(f"[Dashboard] Top posts query failed: {e}")
            return []

    # ── Growth Trends ────────────────────────────────────────────────────

    async def get_growth_trends(
        self,
        platform: Optional[str] = None,
        period_days: int = 30,
        granularity: str = "day",
    ) -> Dict[str, Any]:
        """
        Time-series data: posts published, views, likes per day/week.
        """
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self.db_url)
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

            trunc = "day" if granularity == "day" else "week"

            query = f"""
                SELECT
                    DATE_TRUNC('{trunc}', COALESCE(published_at, posted_at)) as period,
                    COUNT(*) as posts,
                    COALESCE(SUM(views), 0) as views,
                    COALESCE(SUM(likes), 0) as likes,
                    COALESCE(SUM(comments), 0) as comments,
                    COALESCE(AVG(engagement_rate), 0) as avg_er
                FROM posted_content
                WHERE COALESCE(published_at, posted_at) > :cutoff
            """
            params: Dict[str, Any] = {"cutoff": cutoff}

            if platform:
                query += " AND platform = :platform"
                params["platform"] = platform

            query += f" GROUP BY DATE_TRUNC('{trunc}', COALESCE(published_at, posted_at)) ORDER BY period"

            with engine.connect() as conn:
                rows = conn.execute(text(query), params).fetchall()

            return {
                "platform": platform or "all",
                "period_days": period_days,
                "granularity": granularity,
                "data_points": [
                    {
                        "date": r[0].isoformat() if r[0] else None,
                        "posts": r[1],
                        "views": int(r[2]),
                        "likes": int(r[3]),
                        "comments": int(r[4]),
                        "avg_engagement_rate": round(float(r[5]), 4),
                    }
                    for r in rows
                ],
            }

        except Exception as e:
            logger.error(f"[Dashboard] Growth trends query failed: {e}")
            return {"error": str(e)}

    # ── Content Performance ──────────────────────────────────────────────

    async def get_content_performance(
        self, media_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cross-platform comparison for a single piece of content,
        or overall content leaderboard.
        """
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self.db_url)

            if media_id:
                # Find all posts referencing this media across platforms
                with engine.connect() as conn:
                    rows = conn.execute(text("""
                        SELECT
                            pc.platform,
                            pc.platform_url,
                            COALESCE(pc.views, 0) as views,
                            COALESCE(pc.likes, 0) as likes,
                            COALESCE(pc.comments, 0) as comments,
                            COALESCE(pc.shares, 0) as shares,
                            COALESCE(pc.engagement_rate, 0) as er,
                            COALESCE(pc.published_at, pc.posted_at) as published_at
                        FROM posted_content pc
                        JOIN scheduled_posts sp ON sp.id = pc.scheduled_post_id
                        WHERE sp.content_id = :media_id OR sp.media_path LIKE :media_pattern
                        ORDER BY pc.views DESC NULLS LAST
                    """), {"media_id": media_id, "media_pattern": f"%{media_id}%"}).fetchall()

                return {
                    "media_id": media_id,
                    "platforms": [
                        {
                            "platform": r[0],
                            "url": r[1],
                            "views": r[2],
                            "likes": r[3],
                            "comments": r[4],
                            "shares": r[5],
                            "engagement_rate": round(float(r[6]), 4),
                            "published_at": r[7].isoformat() if r[7] else None,
                        }
                        for r in rows
                    ],
                }
            else:
                # Content leaderboard — all-time top
                with engine.connect() as conn:
                    rows = conn.execute(text("""
                        SELECT
                            pc.id,
                            pc.platform,
                            pc.caption,
                            pc.title,
                            pc.platform_url,
                            COALESCE(pc.views, 0) as views,
                            COALESCE(pc.likes, 0) as likes,
                            COALESCE(pc.engagement_rate, 0) as er,
                            COALESCE(pc.published_at, pc.posted_at) as published_at
                        FROM posted_content pc
                        ORDER BY pc.views DESC NULLS LAST
                        LIMIT 25
                    """)).fetchall()

                return {
                    "leaderboard": [
                        {
                            "id": str(r[0]),
                            "platform": r[1],
                            "caption_preview": (r[2] or r[3] or "")[:100],
                            "url": r[4],
                            "views": r[5],
                            "likes": r[6],
                            "engagement_rate": round(float(r[7]), 4),
                            "published_at": r[8].isoformat() if r[8] else None,
                        }
                        for r in rows
                    ],
                }

        except Exception as e:
            logger.error(f"[Dashboard] Content performance query failed: {e}")
            return {"error": str(e)}

    # ── Account Comparison ───────────────────────────────────────────────

    async def compare_accounts(
        self,
        platform: str,
        period_days: int = 30,
    ) -> Dict[str, Any]:
        """Compare performance between accounts on the same platform."""
        try:
            from sqlalchemy import create_engine, text

            engine = create_engine(self.db_url)
            cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

            with engine.connect() as conn:
                rows = conn.execute(text("""
                    SELECT
                        sp.account_username,
                        sp.blotato_account_id,
                        COUNT(*) as posts,
                        COALESCE(SUM(pc.views), 0) as views,
                        COALESCE(SUM(pc.likes), 0) as likes,
                        COALESCE(SUM(pc.comments), 0) as comments,
                        COALESCE(AVG(pc.engagement_rate), 0) as avg_er
                    FROM posted_content pc
                    JOIN scheduled_posts sp ON sp.id = pc.scheduled_post_id
                    WHERE pc.platform = :platform
                      AND COALESCE(pc.published_at, pc.posted_at) > :cutoff
                    GROUP BY sp.account_username, sp.blotato_account_id
                    ORDER BY SUM(pc.views) DESC NULLS LAST
                """), {"platform": platform, "cutoff": cutoff}).fetchall()

            return {
                "platform": platform,
                "period_days": period_days,
                "accounts": [
                    {
                        "username": r[0] or f"Account {r[1]}",
                        "account_id": r[1],
                        "posts": r[2],
                        "views": int(r[3]),
                        "likes": int(r[4]),
                        "comments": int(r[5]),
                        "avg_engagement_rate": round(float(r[6]), 4),
                    }
                    for r in rows
                ],
            }

        except Exception as e:
            logger.error(f"[Dashboard] Account comparison failed: {e}")
            return {"error": str(e)}
