"""
Offer Traffic Tracking Service (ARCH-005)
==========================================
Tracks traffic and conversions from social media posts to offer URLs.

Features:
- Track clicks from different platforms and campaigns
- Monitor conversion metrics
- Generate traffic reports
- Link tracking with UTM parameters
- Real-time analytics dashboard support

Integration:
- Wired into MasterOrchestrator pipeline
- EventBus notifications for traffic events
- Database persistence for analytics
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urlencode, parse_qs
from uuid import uuid4

from sqlalchemy import create_engine, text

try:
    from services.event_bus import EventBus, Topics
    EVENT_BUS_AVAILABLE = True
except ImportError:
    EVENT_BUS_AVAILABLE = False

logger = logging.getLogger(__name__)


class OfferTrafficTracker:
    """
    Tracks traffic to offer URLs from social media campaigns.

    Features (ARCH-005):
    - Automatic UTM parameter injection
    - Click tracking
    - Conversion tracking
    - Platform-specific analytics
    - Campaign performance reports
    """

    _instance: Optional['OfferTrafficTracker'] = None

    def __init__(self, event_bus: Optional['EventBus'] = None):
        self.event_bus = event_bus
        if EVENT_BUS_AVAILABLE and not self.event_bus:
            self.event_bus = EventBus.get_instance()

        # Database connection
        DATABASE_URL = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:54322/postgres"
        )
        self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)

        logger.info("🔗 Offer Traffic Tracker initialized (ARCH-005)")

    @classmethod
    def get_instance(cls, event_bus: Optional['EventBus'] = None) -> 'OfferTrafficTracker':
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance

    def create_tracked_link(
        self,
        offer_url: str,
        pipeline_id: Optional[str] = None,
        platform: str = "twitter",
        campaign_id: Optional[str] = None,
        post_url: Optional[str] = None
    ) -> str:
        """
        Create a tracked link with UTM parameters for analytics.

        Args:
            offer_url: Base offer URL
            pipeline_id: Pipeline that generated this link
            platform: Social media platform
            campaign_id: Campaign identifier
            post_url: URL of the post containing the link

        Returns:
            Tracked URL with UTM parameters
        """
        # Generate unique tracking ID
        tracking_id = str(uuid4())[:8]

        # Parse existing URL
        parsed = urlparse(offer_url)
        query_params = parse_qs(parsed.query) if parsed.query else {}

        # Add UTM parameters
        utm_params = {
            'utm_source': platform,
            'utm_medium': 'social',
            'utm_campaign': campaign_id or f'pipeline_{pipeline_id}',
            'utm_content': tracking_id
        }

        # Merge with existing params
        for key, value in utm_params.items():
            query_params[key] = [value]

        # Rebuild URL
        query_string = urlencode({k: v[0] for k, v in query_params.items()})
        tracked_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        if query_string:
            tracked_url += f"?{query_string}"

        # Register tracking entry
        try:
            with self.engine.connect() as conn:
                conn.execute(text("""
                    INSERT INTO offer_traffic_tracking (
                        pipeline_id, offer_url, offer_name, platform,
                        post_url, campaign_id, metadata
                    ) VALUES (
                        :pipeline_id, :offer_url, :offer_name, :platform,
                        :post_url, :campaign_id, :metadata
                    )
                """), {
                    "pipeline_id": pipeline_id,
                    "offer_url": offer_url,
                    "offer_name": self._extract_offer_name(offer_url),
                    "platform": platform,
                    "post_url": post_url,
                    "campaign_id": campaign_id or tracking_id,
                    "metadata": f'{{"tracking_id": "{tracking_id}", "tracked_url": "{tracked_url}"}}'
                })
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to register tracked link: {e}")

        return tracked_url

    def _extract_offer_name(self, url: str) -> str:
        """Extract offer name from URL."""
        parsed = urlparse(url)
        # Use domain as offer name
        domain = parsed.netloc.replace('www.', '')
        return domain or "Unknown Offer"

    async def track_click(
        self,
        campaign_id: str,
        platform: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record a click on a tracked offer link.

        Args:
            campaign_id: Campaign identifier
            platform: Platform where click originated
            timestamp: When the click occurred

        Returns:
            True if tracked successfully
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        try:
            with self.engine.connect() as conn:
                # Update click count
                result = conn.execute(text("""
                    UPDATE offer_traffic_tracking
                    SET clicks = clicks + 1,
                        last_click_at = :timestamp,
                        first_click_at = COALESCE(first_click_at, :timestamp),
                        updated_at = NOW()
                    WHERE campaign_id = :campaign_id AND platform = :platform
                    RETURNING id
                """), {
                    "campaign_id": campaign_id,
                    "platform": platform,
                    "timestamp": timestamp
                })
                conn.commit()

                if result.rowcount > 0:
                    logger.info(f"📊 Click tracked: campaign={campaign_id}, platform={platform}")

                    # Emit event
                    if self.event_bus and EVENT_BUS_AVAILABLE:
                        await self.event_bus.publish(
                            "offer.click.tracked",
                            {
                                "campaign_id": campaign_id,
                                "platform": platform,
                                "timestamp": timestamp.isoformat()
                            },
                            source="offer_traffic_tracker"
                        )

                    return True
        except Exception as e:
            logger.error(f"Failed to track click: {e}")

        return False

    async def track_conversion(
        self,
        campaign_id: str,
        platform: str,
        revenue_usd: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Record a conversion (purchase, signup, etc.) from a tracked link.

        Args:
            campaign_id: Campaign identifier
            platform: Platform where conversion originated
            revenue_usd: Revenue from conversion
            metadata: Additional conversion data
            timestamp: When the conversion occurred

        Returns:
            True if tracked successfully
        """
        timestamp = timestamp or datetime.now(timezone.utc)

        try:
            with self.engine.connect() as conn:
                # Update conversion metrics
                conn.execute(text("""
                    UPDATE offer_traffic_tracking
                    SET conversions = conversions + 1,
                        revenue_usd = revenue_usd + :revenue,
                        metadata = COALESCE(metadata, '{}'::jsonb) || :metadata::jsonb,
                        updated_at = NOW()
                    WHERE campaign_id = :campaign_id AND platform = :platform
                """), {
                    "campaign_id": campaign_id,
                    "platform": platform,
                    "revenue": revenue_usd,
                    "metadata": str(metadata or {})
                })
                conn.commit()

                logger.info(f"💰 Conversion tracked: campaign={campaign_id}, revenue=${revenue_usd}")

                # Emit event
                if self.event_bus and EVENT_BUS_AVAILABLE:
                    await self.event_bus.publish(
                        "offer.conversion.tracked",
                        {
                            "campaign_id": campaign_id,
                            "platform": platform,
                            "revenue_usd": revenue_usd,
                            "timestamp": timestamp.isoformat()
                        },
                        source="offer_traffic_tracker"
                    )

                return True
        except Exception as e:
            logger.error(f"Failed to track conversion: {e}")

        return False

    def get_campaign_stats(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get traffic statistics for a campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            Campaign stats dict or None
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        pipeline_id, offer_url, offer_name, platform,
                        clicks, conversions, revenue_usd,
                        first_click_at, last_click_at, tracked_at
                    FROM offer_traffic_tracking
                    WHERE campaign_id = :campaign_id
                """), {"campaign_id": campaign_id})

                row = result.fetchone()
                if row:
                    conversion_rate = (row[5] / row[4] * 100) if row[4] > 0 else 0

                    return {
                        "campaign_id": campaign_id,
                        "pipeline_id": row[0],
                        "offer_url": row[1],
                        "offer_name": row[2],
                        "platform": row[3],
                        "clicks": row[4],
                        "conversions": row[5],
                        "revenue_usd": float(row[6]) if row[6] else 0.0,
                        "conversion_rate": conversion_rate,
                        "first_click_at": row[7].isoformat() if row[7] else None,
                        "last_click_at": row[8].isoformat() if row[8] else None,
                        "tracked_at": row[9].isoformat() if row[9] else None
                    }
        except Exception as e:
            logger.error(f"Failed to get campaign stats: {e}")

        return None

    def get_pipeline_traffic_report(self, pipeline_id: str) -> Dict[str, Any]:
        """
        Get traffic report for all campaigns in a pipeline.

        Args:
            pipeline_id: Pipeline identifier

        Returns:
            Aggregated traffic report
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        COUNT(*) as campaign_count,
                        SUM(clicks) as total_clicks,
                        SUM(conversions) as total_conversions,
                        SUM(revenue_usd) as total_revenue,
                        ARRAY_AGG(DISTINCT platform) as platforms
                    FROM offer_traffic_tracking
                    WHERE pipeline_id = :pipeline_id
                """), {"pipeline_id": pipeline_id})

                row = result.fetchone()
                if row:
                    total_clicks = row[1] or 0
                    total_conversions = row[2] or 0
                    conversion_rate = (total_conversions / total_clicks * 100) if total_clicks > 0 else 0

                    return {
                        "pipeline_id": pipeline_id,
                        "campaign_count": row[0] or 0,
                        "total_clicks": total_clicks,
                        "total_conversions": total_conversions,
                        "total_revenue_usd": float(row[3]) if row[3] else 0.0,
                        "conversion_rate": conversion_rate,
                        "platforms": row[4] or []
                    }
        except Exception as e:
            logger.error(f"Failed to get pipeline traffic report: {e}")

        return {
            "pipeline_id": pipeline_id,
            "campaign_count": 0,
            "total_clicks": 0,
            "total_conversions": 0,
            "total_revenue_usd": 0.0,
            "conversion_rate": 0.0,
            "platforms": []
        }

    def get_platform_performance(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics by platform.

        Args:
            start_date: Filter from this date
            end_date: Filter to this date

        Returns:
            List of platform performance dicts
        """
        start_date = start_date or datetime.now(timezone.utc) - timedelta(days=30)
        end_date = end_date or datetime.now(timezone.utc)

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        platform,
                        COUNT(*) as campaign_count,
                        SUM(clicks) as total_clicks,
                        SUM(conversions) as total_conversions,
                        SUM(revenue_usd) as total_revenue,
                        AVG(CASE WHEN clicks > 0 THEN conversions::float / clicks * 100 ELSE 0 END) as avg_conversion_rate
                    FROM offer_traffic_tracking
                    WHERE tracked_at BETWEEN :start_date AND :end_date
                    GROUP BY platform
                    ORDER BY total_clicks DESC
                """), {
                    "start_date": start_date,
                    "end_date": end_date
                })

                platforms = []
                for row in result:
                    platforms.append({
                        "platform": row[0],
                        "campaign_count": row[1],
                        "total_clicks": row[2] or 0,
                        "total_conversions": row[3] or 0,
                        "total_revenue_usd": float(row[4]) if row[4] else 0.0,
                        "avg_conversion_rate": float(row[5]) if row[5] else 0.0
                    })

                return platforms
        except Exception as e:
            logger.error(f"Failed to get platform performance: {e}")

        return []

    def get_top_performing_campaigns(
        self,
        limit: int = 10,
        metric: str = "clicks"
    ) -> List[Dict[str, Any]]:
        """
        Get top performing campaigns by specified metric.

        Args:
            limit: Number of campaigns to return
            metric: Sort metric (clicks, conversions, revenue_usd)

        Returns:
            List of campaign stats
        """
        if metric not in ["clicks", "conversions", "revenue_usd"]:
            metric = "clicks"

        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"""
                    SELECT
                        campaign_id, pipeline_id, offer_name, platform,
                        clicks, conversions, revenue_usd,
                        tracked_at
                    FROM offer_traffic_tracking
                    WHERE {metric} > 0
                    ORDER BY {metric} DESC
                    LIMIT :limit
                """), {"limit": limit})

                campaigns = []
                for row in result:
                    conversion_rate = (row[5] / row[4] * 100) if row[4] > 0 else 0
                    campaigns.append({
                        "campaign_id": row[0],
                        "pipeline_id": row[1],
                        "offer_name": row[2],
                        "platform": row[3],
                        "clicks": row[4] or 0,
                        "conversions": row[5] or 0,
                        "revenue_usd": float(row[6]) if row[6] else 0.0,
                        "conversion_rate": conversion_rate,
                        "tracked_at": row[7].isoformat() if row[7] else None
                    })

                return campaigns
        except Exception as e:
            logger.error(f"Failed to get top campaigns: {e}")

        return []


# Convenience function
def get_tracker() -> OfferTrafficTracker:
    """Get singleton instance of offer traffic tracker."""
    return OfferTrafficTracker.get_instance()
