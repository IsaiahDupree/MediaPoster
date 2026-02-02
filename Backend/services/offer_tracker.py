"""
Offer Traffic Tracking Service (ARCH-005)
==========================================
Tracks traffic, conversions, and ROI from promotional tweets driving to offers.

Workflow:
    1. Tweets with UTM parameters drive traffic to offers
    2. Track clicks via UTM parameters
    3. Track conversions (purchases, signups, etc.)
    4. Calculate ROI and optimize future campaigns

Database tables:
    - offer_campaigns: Campaign metadata
    - offer_traffic: Click/visit tracking
    - offer_conversions: Conversion events
    - campaign_analytics: Aggregated metrics
"""
import os
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, text
from loguru import logger

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@127.0.0.1:54322/postgres")


class OfferTracker:
    """
    Track offer traffic and conversions from promotional tweets.

    Usage:
        tracker = OfferTracker()

        # Track a click
        tracker.track_click(
            utm_campaign="jan2026_promo",
            utm_source="twitter",
            utm_content="v1"
        )

        # Track a conversion
        tracker.track_conversion(
            utm_campaign="jan2026_promo",
            conversion_type="purchase",
            revenue=49.99
        )

        # Get analytics
        analytics = tracker.get_campaign_analytics("jan2026_promo")
    """

    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        logger.info("[OfferTracker] Initialized")

    async def create_tracked_link(
        self,
        offer_url: str,
        campaign: str,
        source: str = "mediaposter",
        medium: str = "social",
        content: Optional[str] = None
    ) -> str:
        """
        Create a tracked link with UTM parameters for an offer URL.

        Args:
            offer_url: Base offer URL to track
            campaign: Campaign name/identifier
            source: Traffic source (default: "mediaposter")
            medium: Marketing medium (default: "social")
            content: Optional content/variant identifier

        Returns:
            Full URL with UTM parameters appended
        """
        from urllib.parse import urlencode, urlparse, urlunparse, parse_qs

        # Parse the URL
        parsed = urlparse(offer_url)
        query_params = parse_qs(parsed.query)

        # Add UTM parameters
        utm_params = {
            "utm_campaign": campaign,
            "utm_source": source,
            "utm_medium": medium
        }
        if content:
            utm_params["utm_content"] = content

        # Merge with existing query params
        query_params.update({k: [v] for k, v in utm_params.items()})

        # Flatten query params (take first value if list)
        flat_params = {k: v[0] if isinstance(v, list) else v for k, v in query_params.items()}

        # Rebuild URL
        new_query = urlencode(flat_params)
        tracked_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))

        logger.info(f"[OfferTracker] Created tracked link: {campaign} -> {tracked_url}")
        return tracked_url

    def track_click(
        self,
        utm_campaign: str,
        utm_source: str = "twitter",
        utm_medium: str = "social",
        utm_content: Optional[str] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referrer: Optional[str] = None
    ) -> str:
        """
        Track a click/visit to an offer URL.

        Args:
            utm_campaign: Campaign identifier
            utm_source: Traffic source
            utm_medium: Marketing medium
            utm_content: Content/variant identifier
            user_id: Optional user ID
            ip_address: Optional IP address for deduplication
            user_agent: Optional user agent string
            referrer: Optional referrer URL

        Returns:
            Click ID
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO offer_traffic (
                        utm_campaign, utm_source, utm_medium, utm_content,
                        user_id, ip_address, user_agent, referrer, clicked_at
                    ) VALUES (
                        :utm_campaign, :utm_source, :utm_medium, :utm_content,
                        :user_id, :ip_address, :user_agent, :referrer, NOW()
                    )
                    RETURNING id
                """), {
                    "utm_campaign": utm_campaign,
                    "utm_source": utm_source,
                    "utm_medium": utm_medium,
                    "utm_content": utm_content,
                    "user_id": user_id,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                    "referrer": referrer
                })
                conn.commit()

                click_id = str(result.fetchone()[0])
                logger.info(f"[OfferTracker] Click tracked: {utm_campaign}/{utm_content} -> {click_id}")
                return click_id

        except Exception as e:
            logger.error(f"[OfferTracker] Failed to track click: {e}")
            raise

    def track_conversion(
        self,
        utm_campaign: str,
        conversion_type: str = "purchase",
        utm_content: Optional[str] = None,
        user_id: Optional[str] = None,
        revenue: Optional[float] = None,
        conversion_data: Optional[Dict] = None
    ) -> str:
        """
        Track a conversion event (purchase, signup, etc.).

        Args:
            utm_campaign: Campaign identifier
            conversion_type: Type of conversion (purchase, signup, trial, etc.)
            utm_content: Content/variant identifier
            user_id: Optional user ID
            revenue: Optional revenue amount
            conversion_data: Optional additional conversion metadata

        Returns:
            Conversion ID
        """
        try:
            import json

            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO offer_conversions (
                        utm_campaign, utm_content, conversion_type,
                        user_id, revenue, conversion_data, converted_at
                    ) VALUES (
                        :utm_campaign, :utm_content, :conversion_type,
                        :user_id, :revenue, :conversion_data, NOW()
                    )
                    RETURNING id
                """), {
                    "utm_campaign": utm_campaign,
                    "utm_content": utm_content,
                    "conversion_type": conversion_type,
                    "user_id": user_id,
                    "revenue": revenue,
                    "conversion_data": json.dumps(conversion_data or {})
                })
                conn.commit()

                conversion_id = str(result.fetchone()[0])
                logger.info(
                    f"[OfferTracker] Conversion tracked: {utm_campaign} -> "
                    f"{conversion_type} ${revenue or 0}"
                )
                return conversion_id

        except Exception as e:
            logger.error(f"[OfferTracker] Failed to track conversion: {e}")
            raise

    def get_campaign_analytics(
        self,
        utm_campaign: str,
        days: int = 30
    ) -> Dict:
        """
        Get analytics for a specific campaign.

        Args:
            utm_campaign: Campaign identifier
            days: Number of days to include

        Returns:
            Campaign analytics dict
        """
        try:
            with self.engine.connect() as conn:
                # Get click metrics
                click_result = conn.execute(text("""
                    SELECT
                        COUNT(*) as total_clicks,
                        COUNT(DISTINCT ip_address) as unique_clicks,
                        COUNT(DISTINCT utm_content) as variants_tested
                    FROM offer_traffic
                    WHERE utm_campaign = :campaign
                      AND clicked_at > NOW() - INTERVAL ':days days'
                """), {"campaign": utm_campaign, "days": days})

                click_row = click_result.fetchone()

                # Get conversion metrics
                conversion_result = conn.execute(text("""
                    SELECT
                        COUNT(*) as total_conversions,
                        SUM(revenue) as total_revenue,
                        AVG(revenue) as avg_order_value,
                        COUNT(DISTINCT conversion_type) as conversion_types
                    FROM offer_conversions
                    WHERE utm_campaign = :campaign
                      AND converted_at > NOW() - INTERVAL ':days days'
                """), {"campaign": utm_campaign, "days": days})

                conversion_row = conversion_result.fetchone()

                # Get performance by content variant
                variant_result = conn.execute(text("""
                    SELECT
                        t.utm_content,
                        COUNT(DISTINCT t.id) as clicks,
                        COUNT(DISTINCT c.id) as conversions,
                        SUM(c.revenue) as revenue
                    FROM offer_traffic t
                    LEFT JOIN offer_conversions c
                        ON t.utm_campaign = c.utm_campaign
                        AND t.utm_content = c.utm_content
                    WHERE t.utm_campaign = :campaign
                      AND t.clicked_at > NOW() - INTERVAL ':days days'
                    GROUP BY t.utm_content
                    ORDER BY clicks DESC
                """), {"campaign": utm_campaign, "days": days})

                variants = []
                for row in variant_result.fetchall():
                    variants.append({
                        "content_id": row[0],
                        "clicks": row[1],
                        "conversions": row[2] or 0,
                        "revenue": float(row[3] or 0),
                        "conversion_rate": (row[2] or 0) / row[1] * 100 if row[1] > 0 else 0
                    })

                # Calculate overall metrics
                total_clicks = click_row[0] or 0
                unique_clicks = click_row[1] or 0
                total_conversions = conversion_row[0] or 0
                total_revenue = float(conversion_row[1] or 0)
                avg_order_value = float(conversion_row[2] or 0)

                conversion_rate = (total_conversions / unique_clicks * 100) if unique_clicks > 0 else 0

                return {
                    "campaign": utm_campaign,
                    "period_days": days,
                    "traffic": {
                        "total_clicks": total_clicks,
                        "unique_clicks": unique_clicks,
                        "variants_tested": click_row[2] or 0
                    },
                    "conversions": {
                        "total": total_conversions,
                        "conversion_rate": round(conversion_rate, 2),
                        "types": conversion_row[3] or 0
                    },
                    "revenue": {
                        "total": round(total_revenue, 2),
                        "avg_order_value": round(avg_order_value, 2)
                    },
                    "variants": variants,
                    "roi": self._calculate_roi(total_revenue, total_clicks)
                }

        except Exception as e:
            logger.error(f"[OfferTracker] Failed to get analytics: {e}")
            raise

    def _calculate_roi(self, revenue: float, clicks: int) -> Dict:
        """Calculate ROI metrics."""
        # Assume $0.10 cost per click (Twitter ad cost estimate)
        cost_per_click = 0.10
        total_cost = clicks * cost_per_click

        if total_cost == 0:
            return {
                "total_cost": 0,
                "profit": revenue,
                "roi_percentage": 0
            }

        profit = revenue - total_cost
        roi_percentage = (profit / total_cost) * 100

        return {
            "total_cost": round(total_cost, 2),
            "profit": round(profit, 2),
            "roi_percentage": round(roi_percentage, 2)
        }

    def get_top_performing_content(
        self,
        utm_campaign: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Get top-performing content variants by conversion rate.

        Args:
            utm_campaign: Campaign identifier
            limit: Number of variants to return

        Returns:
            List of top-performing content variants
        """
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT
                        t.utm_content,
                        COUNT(DISTINCT t.id) as clicks,
                        COUNT(DISTINCT c.id) as conversions,
                        SUM(c.revenue) as revenue,
                        CASE
                            WHEN COUNT(DISTINCT t.id) > 0
                            THEN (COUNT(DISTINCT c.id)::float / COUNT(DISTINCT t.id)) * 100
                            ELSE 0
                        END as conversion_rate
                    FROM offer_traffic t
                    LEFT JOIN offer_conversions c
                        ON t.utm_campaign = c.utm_campaign
                        AND t.utm_content = c.utm_content
                    WHERE t.utm_campaign = :campaign
                    GROUP BY t.utm_content
                    ORDER BY conversion_rate DESC, conversions DESC
                    LIMIT :limit
                """), {"campaign": utm_campaign, "limit": limit})

                return [
                    {
                        "content_id": row[0],
                        "clicks": row[1],
                        "conversions": row[2] or 0,
                        "revenue": float(row[3] or 0),
                        "conversion_rate": round(row[4], 2)
                    }
                    for row in result.fetchall()
                ]

        except Exception as e:
            logger.error(f"[OfferTracker] Failed to get top content: {e}")
            raise

    # ARCH-005: Alias for get_campaign_analytics
    def get_offer_stats(self, campaign_name: str = None, days: int = 30) -> Dict[str, Any]:
        """
        Get offer statistics (ARCH-005).

        This is an alias for get_campaign_analytics that provides a simplified
        interface for getting offer performance stats.

        Args:
            campaign_name: Campaign to get stats for (or None for all)
            days: Number of days to look back

        Returns:
            Dictionary with offer statistics
        """
        if campaign_name:
            return self.get_campaign_analytics(campaign_name)
        else:
            # Get aggregated stats across all campaigns
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT
                            COUNT(DISTINCT t.id) as total_clicks,
                            COUNT(DISTINCT c.id) as total_conversions,
                            SUM(c.revenue) as total_revenue,
                            CASE
                                WHEN COUNT(DISTINCT t.id) > 0
                                THEN (COUNT(DISTINCT c.id)::float / COUNT(DISTINCT t.id)) * 100
                                ELSE 0
                            END as conversion_rate
                        FROM offer_traffic t
                        LEFT JOIN offer_conversions c ON t.utm_campaign = c.utm_campaign
                        WHERE t.clicked_at >= NOW() - INTERVAL ':days days'
                    """), {"days": days})

                    row = result.fetchone()
                    if row:
                        return {
                            "period_days": days,
                            "total_clicks": row[0] or 0,
                            "total_conversions": row[1] or 0,
                            "total_revenue": float(row[2] or 0),
                            "conversion_rate": round(float(row[3] or 0), 2)
                        }

                    return {
                        "period_days": days,
                        "total_clicks": 0,
                        "total_conversions": 0,
                        "total_revenue": 0.0,
                        "conversion_rate": 0.0
                    }

            except Exception as e:
                logger.error(f"[OfferTracker] Failed to get offer stats: {e}")
                return {
                    "period_days": days,
                    "total_clicks": 0,
                    "total_conversions": 0,
                    "total_revenue": 0.0,
                    "conversion_rate": 0.0,
                    "error": str(e)
                }


    # ------------------------------------------------------------------
    # Method aliases for compatibility with different test suites
    # ------------------------------------------------------------------

    async def generate_utm_link(self, offer_url: str, campaign: str, **kwargs) -> str:
        """Alias for create_tracked_link."""
        return await self.create_tracked_link(offer_url, campaign, **kwargs)

    def record_click(self, **kwargs):
        """Alias for track_click."""
        return self.track_click(**kwargs)

    def record_conversion(self, **kwargs):
        """Alias for track_conversion."""
        return self.track_conversion(**kwargs)

    def get_campaign_stats(self, campaign: str = None, **kwargs) -> Dict:
        """Alias for get_campaign_analytics / get_offer_stats."""
        if campaign:
            return self.get_campaign_analytics(campaign, **kwargs)
        return self.get_offer_stats(campaign_name=campaign, **kwargs)

    def get_roi_report(self, campaign: str = None, days: int = 30) -> Dict:
        """Get ROI report for a campaign or all campaigns."""
        stats = self.get_offer_stats(campaign_name=campaign, days=days)
        revenue = stats.get("total_revenue", 0)
        clicks = stats.get("total_clicks", 0)
        roi = self._calculate_roi(revenue, clicks) if clicks > 0 else {"roi": 0, "cpc": 0}
        return {**stats, **roi}


# Singleton instance
_tracker_instance: Optional[OfferTracker] = None


def get_offer_tracker() -> OfferTracker:
    """Get the global offer tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = OfferTracker()
    return _tracker_instance
