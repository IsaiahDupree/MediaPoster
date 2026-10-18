"""
Multi-Platform Analytics Aggregator (ANALYTICS-001)
====================================================
Aggregates analytics metrics across all platforms (Instagram, TikTok,
YouTube, Twitter/X) for unified cross-platform comparison.

Uses real database queries against the metrics_snapshots and
platform_metrics tables populated by platform adapters.
"""

import logging
import os
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional, Any

from pydantic import BaseModel
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:54322/postgres"
)


class ContentRollup(BaseModel):
    content_id: UUID
    total_views: int = 0
    total_impressions: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_saves: int = 0
    total_clicks: int = 0
    avg_watch_time_seconds: float = 0.0
    global_sentiment: float = 0.0
    best_platform: Optional[str] = None
    last_updated_at: datetime


class PlatformMetrics(BaseModel):
    """Metrics for a single platform variant."""
    platform: str
    views: int = 0
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    clicks: int = 0
    watch_time_seconds: float = 0.0
    engagement_rate: float = 0.0
    sentiment: float = 0.0


def _get_engine():
    """Get or create database engine."""
    return create_engine(DATABASE_URL, pool_pre_ping=True)


def _fetch_platform_metrics(engine, content_id: UUID) -> List[Dict[str, Any]]:
    """
    Fetch latest metrics snapshots for a content item from the database.

    Queries the metrics_snapshots table (populated by platform adapters)
    for the most recent snapshot per platform.
    """
    query = text("""
        SELECT DISTINCT ON (platform)
            platform,
            COALESCE(views, 0) as views,
            COALESCE(impressions, 0) as impressions,
            COALESCE(likes, 0) as likes,
            COALESCE(comments, 0) as comments,
            COALESCE(shares, 0) as shares,
            COALESCE(saves, 0) as saves,
            COALESCE(clicks, 0) as clicks,
            COALESCE(watch_time_seconds, 0) as watch_time_seconds,
            COALESCE(engagement_rate, 0) as engagement_rate,
            COALESCE(sentiment_score, 0) as sentiment
        FROM metrics_snapshots
        WHERE content_id = :content_id
        ORDER BY platform, snapshot_at DESC
    """)

    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"content_id": str(content_id)})
            rows = result.mappings().all()
            return [dict(row) for row in rows]
    except Exception as e:
        logger.warning(f"Failed to fetch metrics from DB for {content_id}: {e}")
        return []


async def aggregate_metrics_for_content(content_id: UUID) -> ContentRollup:
    """
    Compute aggregated metrics (rollups) for a single content item
    across all its platform variants.

    Fetches real metrics from the metrics_snapshots table populated
    by platform adapters. Returns zeros if no data is available yet.
    """
    engine = _get_engine()
    platform_data = _fetch_platform_metrics(engine, content_id)

    rollup = ContentRollup(
        content_id=content_id,
        last_updated_at=datetime.now(timezone.utc)
    )

    if not platform_data:
        logger.info(f"No metrics data found for content {content_id}")
        return rollup

    total_sentiment_weighted = 0.0
    total_interactions = 0
    best_platform_score = -1.0

    for m in platform_data:
        rollup.total_views += m.get("views", 0)
        rollup.total_impressions += m.get("impressions", 0)
        rollup.total_likes += m.get("likes", 0)
        rollup.total_comments += m.get("comments", 0)
        rollup.total_shares += m.get("shares", 0)
        rollup.total_saves += m.get("saves", 0)
        rollup.total_clicks += m.get("clicks", 0)
        rollup.avg_watch_time_seconds += m.get("watch_time_seconds", 0)

        interactions = (
            m.get("likes", 0)
            + m.get("comments", 0)
            + m.get("shares", 0)
        )
        total_interactions += interactions
        sentiment = m.get("sentiment", 0)
        total_sentiment_weighted += sentiment * interactions

        engagement = m.get("engagement_rate", 0)
        views = m.get("views", 0)
        score = views * (1 + engagement)
        if score > best_platform_score:
            best_platform_score = score
            rollup.best_platform = m.get("platform")

    if total_interactions > 0:
        rollup.global_sentiment = total_sentiment_weighted / total_interactions

    if len(platform_data) > 0:
        rollup.avg_watch_time_seconds /= len(platform_data)

    # Persist rollup to database
    _save_rollup(engine, rollup)

    logger.info(
        f"Aggregated metrics for {content_id}: "
        f"{rollup.total_views} views, best={rollup.best_platform}"
    )
    return rollup


def _save_rollup(engine, rollup: ContentRollup):
    """Save computed rollup to the content_rollups table."""
    query = text("""
        INSERT INTO content_rollups (
            content_id, total_views, total_impressions, total_likes,
            total_comments, total_shares, total_saves, total_clicks,
            avg_watch_time_seconds, global_sentiment, best_platform,
            last_updated_at
        ) VALUES (
            :content_id, :total_views, :total_impressions, :total_likes,
            :total_comments, :total_shares, :total_saves, :total_clicks,
            :avg_watch_time_seconds, :global_sentiment, :best_platform,
            :last_updated_at
        )
        ON CONFLICT (content_id) DO UPDATE SET
            total_views = EXCLUDED.total_views,
            total_impressions = EXCLUDED.total_impressions,
            total_likes = EXCLUDED.total_likes,
            total_comments = EXCLUDED.total_comments,
            total_shares = EXCLUDED.total_shares,
            total_saves = EXCLUDED.total_saves,
            total_clicks = EXCLUDED.total_clicks,
            avg_watch_time_seconds = EXCLUDED.avg_watch_time_seconds,
            global_sentiment = EXCLUDED.global_sentiment,
            best_platform = EXCLUDED.best_platform,
            last_updated_at = EXCLUDED.last_updated_at
    """)
    try:
        with engine.connect() as conn:
            conn.execute(query, {
                "content_id": str(rollup.content_id),
                "total_views": rollup.total_views,
                "total_impressions": rollup.total_impressions,
                "total_likes": rollup.total_likes,
                "total_comments": rollup.total_comments,
                "total_shares": rollup.total_shares,
                "total_saves": rollup.total_saves,
                "total_clicks": rollup.total_clicks,
                "avg_watch_time_seconds": rollup.avg_watch_time_seconds,
                "global_sentiment": rollup.global_sentiment,
                "best_platform": rollup.best_platform,
                "last_updated_at": rollup.last_updated_at.isoformat(),
            })
            conn.commit()
    except Exception as e:
        logger.warning(f"Failed to save rollup for {rollup.content_id}: {e}")


async def get_cross_platform_comparison(content_id: UUID) -> Dict[str, Any]:
    """
    Get per-platform breakdown for a content item.

    Returns metrics for each platform so the user can compare
    performance across Instagram, TikTok, YouTube, Twitter, etc.
    """
    engine = _get_engine()
    platform_data = _fetch_platform_metrics(engine, content_id)

    platforms = {}
    for m in platform_data:
        platform = m.get("platform", "unknown")
        views = m.get("views", 0)
        likes = m.get("likes", 0)
        comments = m.get("comments", 0)
        shares = m.get("shares", 0)
        engagement_rate = (
            (likes + comments + shares) / views * 100 if views > 0 else 0.0
        )
        platforms[platform] = {
            "views": views,
            "impressions": m.get("impressions", 0),
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "saves": m.get("saves", 0),
            "clicks": m.get("clicks", 0),
            "watch_time_seconds": m.get("watch_time_seconds", 0),
            "engagement_rate": round(engagement_rate, 2),
            "sentiment": m.get("sentiment", 0),
        }

    return {
        "content_id": str(content_id),
        "platform_count": len(platforms),
        "platforms": platforms,
    }


async def run_nightly_aggregation():
    """
    Job to update rollups for all active content.

    Fetches content IDs with recent metrics and recomputes rollups.
    """
    engine = _get_engine()

    query = text("""
        SELECT DISTINCT content_id
        FROM metrics_snapshots
        WHERE snapshot_at > :since
        ORDER BY content_id
    """)

    try:
        with engine.connect() as conn:
            since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            result = conn.execute(query, {"since": since})
            content_ids = [UUID(str(row[0])) for row in result]
    except Exception as e:
        logger.error(f"Failed to fetch content IDs for aggregation: {e}")
        content_ids = []

    logger.info(f"Running nightly aggregation for {len(content_ids)} content items")

    for cid in content_ids:
        try:
            await aggregate_metrics_for_content(cid)
        except Exception as e:
            logger.error(f"Failed to aggregate metrics for {cid}: {e}")

    logger.info(f"Nightly aggregation complete: {len(content_ids)} items processed")
