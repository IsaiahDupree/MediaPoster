"""
Offer Traffic Tracking Service (ARCH-005)
===========================================

Tracks traffic and conversions from social media posts to offer URLs.
Generates tracked/shortened URLs with UTM parameters for attribution.

Provides:
    - create_tracked_link() - Generate tracked URL with UTM params
    - track_click() - Record click event
    - track_conversion() - Record conversion event
    - get_campaign_report() - Aggregate metrics by campaign
    - get_link_stats() - Per-link statistics

Database Tables:
    - offer_traffic_tracking - Main tracking table
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
import json

logger = logging.getLogger(__name__)


class OfferTracker:
    """
    Offer traffic tracking service for UTM parameter generation,
    click tracking, and conversion attribution.

    Usage:
        tracker = OfferTracker()

        # Create a tracked link
        tracked_url = await tracker.create_tracked_link(
            offer_url="https://example.com/offer",
            campaign="ai_automation_sora",
            source="twitter",
            metadata={"post_id": "123"}
        )

        # In the publish payload, use tracked_url instead of offer_url

        # Get report
        report = await tracker.get_campaign_report("ai_automation_sora")
    """

    def __init__(self):
        """Initialize offer tracker with database connection."""
        self.db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        self._engine = None
        self._init_db()

    def _init_db(self):
        """Initialize database connection."""
        try:
            from sqlalchemy import create_engine
            self._engine = create_engine(self.db_url, pool_pre_ping=True)
            logger.info("✅ OfferTracker database connection initialized")
        except Exception as e:
            logger.warning(f"⚠️ OfferTracker database initialization failed: {e}")
            self._engine = None

    async def create_tracked_link(
        self,
        offer_url: str,
        campaign: str,
        source: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Create a tracked URL with UTM parameters.

        Args:
            offer_url: Base offer URL to track
            campaign: Campaign identifier (e.g., "ai_automation_sora")
            source: Source platform (e.g., "twitter", "tiktok")
            metadata: Optional metadata dict to store

        Returns:
            Tracked URL with UTM parameters appended
        """
        if not self._engine:
            logger.warning("Database not initialized, returning original URL")
            return offer_url

        metadata = metadata or {}

        # Generate UTM parameters
        utm_params = {
            "utm_source": source,
            "utm_medium": "social",
            "utm_campaign": campaign,
        }

        # Build tracked URL with UTM parameters
        separator = "&" if "?" in offer_url else "?"
        tracked_url = f"{offer_url}{separator}" + "&".join(
            [f"{k}={v}" for k, v in utm_params.items()]
        )

        try:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                conn.execute(
                    text("""
                        INSERT INTO offer_traffic_tracking (
                            offer_url, campaign, platform, metadata
                        ) VALUES (
                            :offer_url, :campaign, :platform, :metadata::jsonb
                        )
                        ON CONFLICT (offer_url, campaign, platform) DO NOTHING
                    """),
                    {
                        "offer_url": offer_url,
                        "campaign": campaign,
                        "platform": source,
                        "metadata": json.dumps(metadata),
                    },
                )
                conn.commit()

            logger.info(
                f"Created tracked link: {campaign}/{source} → {offer_url[:50]}..."
            )
            return tracked_url

        except Exception as e:
            logger.error(f"Failed to create tracked link: {e}")
            return offer_url

    async def track_click(
        self,
        offer_url: str,
        campaign: str,
        platform: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a click event for a tracked link.

        Args:
            offer_url: Original offer URL
            campaign: Campaign identifier
            platform: Platform name
            metadata: Click metadata (IP, user agent, referrer, etc.)

        Returns:
            True if click was recorded
        """
        if not self._engine:
            return False

        metadata = metadata or {}

        try:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE offer_traffic_tracking
                        SET 
                            clicks = COALESCE(clicks, 0) + 1,
                            last_click_at = NOW()
                        WHERE offer_url = :offer_url 
                          AND campaign = :campaign 
                          AND platform = :platform
                    """),
                    {
                        "offer_url": offer_url,
                        "campaign": campaign,
                        "platform": platform,
                    },
                )
                conn.commit()

            logger.debug(f"Tracked click: {campaign}/{platform}")
            return True

        except Exception as e:
            logger.error(f"Failed to track click: {e}")
            return False

    async def track_conversion(
        self,
        offer_url: str,
        campaign: str,
        platform: str,
        conversion_type: str = "purchase",
        revenue: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a conversion event.

        Args:
            offer_url: Original offer URL
            campaign: Campaign identifier
            platform: Platform name
            conversion_type: Type of conversion (purchase, signup, etc.)
            revenue: Optional revenue amount
            metadata: Additional metadata

        Returns:
            True if conversion was recorded
        """
        if not self._engine:
            return False

        metadata = metadata or {}

        try:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                conn.execute(
                    text("""
                        UPDATE offer_traffic_tracking
                        SET 
                            conversions = COALESCE(conversions, 0) + 1,
                            revenue_usd = COALESCE(revenue_usd, 0) + COALESCE(:revenue, 0)
                        WHERE offer_url = :offer_url 
                          AND campaign = :campaign 
                          AND platform = :platform
                    """),
                    {
                        "offer_url": offer_url,
                        "campaign": campaign,
                        "platform": platform,
                        "revenue": revenue or 0,
                    },
                )
                conn.commit()

            logger.info(f"Tracked conversion: {campaign}/{platform} ({conversion_type})")
            return True

        except Exception as e:
            logger.error(f"Failed to track conversion: {e}")
            return False

    async def get_campaign_report(
        self, campaign: str, limit_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Get aggregated metrics for a campaign.

        Args:
            campaign: Campaign identifier
            limit_days: Optional limit to last N days

        Returns:
            Campaign metrics dict
        """
        if not self._engine:
            return {"error": "Database not initialized"}

        try:
            from sqlalchemy import text
            with self._engine.connect() as conn:
                query = """
                    SELECT
                        campaign,
                        COUNT(DISTINCT platform) as platforms,
                        COALESCE(SUM(clicks), 0) as total_clicks,
                        COALESCE(SUM(conversions), 0) as total_conversions,
                        COALESCE(SUM(revenue_usd), 0) as total_revenue,
                        MIN(tracked_at) as first_tracked,
                        MAX(last_click_at) as last_click
                    FROM offer_traffic_tracking
                    WHERE campaign = :campaign
                """

                params = {"campaign": campaign}

                if limit_days:
                    query += f" AND tracked_at >= NOW() - INTERVAL '{limit_days} days'"

                query += " GROUP BY campaign"

                result = conn.execute(text(query), params).fetchone()

                if not result:
                    return {
                        "campaign": campaign,
                        "total_clicks": 0,
                        "total_conversions": 0,
                        "total_revenue": 0,
                        "conversion_rate": 0,
                        "avg_revenue_per_conversion": 0,
                    }

                clicks = result[2]
                conversions = result[3]
                revenue = float(result[4]) if result[4] else 0.0

                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
                avg_revenue = (revenue / conversions) if conversions > 0 else 0

                return {
                    "campaign": campaign,
                    "platforms": result[1],
                    "total_clicks": clicks,
                    "total_conversions": conversions,
                    "total_revenue": round(revenue, 2),
                    "conversion_rate": round(conversion_rate, 2),
                    "avg_revenue_per_conversion": round(avg_revenue, 2),
                    "first_tracked": result[5].isoformat() if result[5] else None,
                    "last_click": result[6].isoformat() if result[6] else None,
                }

        except Exception as e:
            logger.error(f"Failed to get campaign report: {e}")
            return {"error": str(e)}

    async def get_platform_report(
        self, campaign: str, platform: str
    ) -> Dict[str, Any]:
        """
        Get metrics for a specific platform within a campaign.

        Args:
            campaign: Campaign identifier
            platform: Platform name (twitter, tiktok, instagram, etc.)

        Returns:
            Platform metrics dict
        """
        if not self._engine:
            return {"error": "Database not initialized"}

        try:
            from sqlalchemy import text
            result = self._engine.connect().execute(
                text("""
                    SELECT
                        platform,
                        COUNT(DISTINCT offer_url) as urls,
                        COALESCE(SUM(clicks), 0) as clicks,
                        COALESCE(SUM(conversions), 0) as conversions,
                        COALESCE(SUM(revenue_usd), 0) as revenue,
                        MIN(tracked_at) as first_tracked,
                        MAX(last_click_at) as last_click
                    FROM offer_traffic_tracking
                    WHERE campaign = :campaign AND platform = :platform
                    GROUP BY platform
                """),
                {"campaign": campaign, "platform": platform},
            ).fetchone()

            if not result:
                return {
                    "campaign": campaign,
                    "platform": platform,
                    "clicks": 0,
                    "conversions": 0,
                    "revenue": 0,
                    "conversion_rate": 0,
                }

            clicks = result[2]
            conversions = result[3]
            revenue = float(result[4]) if result[4] else 0.0

            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0

            return {
                "campaign": campaign,
                "platform": platform,
                "urls": result[1],
                "clicks": clicks,
                "conversions": conversions,
                "revenue": round(revenue, 2),
                "conversion_rate": round(conversion_rate, 2),
                "first_tracked": result[5].isoformat() if result[5] else None,
                "last_click": result[6].isoformat() if result[6] else None,
            }

        except Exception as e:
            logger.error(f"Failed to get platform report: {e}")
            return {"error": str(e)}

    async def get_all_campaigns(self) -> List[Dict[str, Any]]:
        """
        Get summary metrics for all campaigns.

        Returns:
            List of campaign summaries
        """
        if not self._engine:
            return []

        try:
            from sqlalchemy import text
            results = self._engine.connect().execute(
                text("""
                    SELECT
                        campaign,
                        COUNT(DISTINCT platform) as platforms,
                        COALESCE(SUM(clicks), 0) as clicks,
                        COALESCE(SUM(conversions), 0) as conversions,
                        COALESCE(SUM(revenue_usd), 0) as revenue,
                        MAX(last_click_at) as last_activity
                    FROM offer_traffic_tracking
                    WHERE campaign IS NOT NULL
                    GROUP BY campaign
                    ORDER BY last_activity DESC NULLS LAST
                """)
            ).fetchall()

            campaigns = []
            for row in results:
                clicks = row[2]
                conversions = row[3]
                revenue = float(row[4]) if row[4] else 0.0

                conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0

                campaigns.append({
                    "campaign": row[0],
                    "platforms": row[1],
                    "clicks": clicks,
                    "conversions": conversions,
                    "revenue": round(revenue, 2),
                    "conversion_rate": round(conversion_rate, 2),
                    "last_activity": row[5].isoformat() if row[5] else None,
                })

            return campaigns

        except Exception as e:
            logger.error(f"Failed to get all campaigns: {e}")
            return []


# Singleton instance
_offer_tracker_instance: Optional[OfferTracker] = None


def get_offer_tracker() -> OfferTracker:
    """Get or create singleton OfferTracker instance."""
    global _offer_tracker_instance
    if _offer_tracker_instance is None:
        _offer_tracker_instance = OfferTracker()
    return _offer_tracker_instance
