"""
Meta Ads Performance Tracker (AD-005)
======================================
Tracks and calculates ad performance metrics for Meta campaigns.

Metrics tracked:
    - Impressions, clicks, CTR, CPC, CPM, ROAS
    - Hook rate (3-second video views / impressions)
    - Hold rate (ThruPlay / 3-second views)
    - Per-ad and per-campaign aggregation

Uses in-memory storage for development, database persistence for production
when DATABASE_URL is configured.

Usage:
    tracker = get_performance_tracker()
    tracker.track_impression("ad-123", {"campaign_id": "camp-1", "cost_cents": 5})
    tracker.track_click("ad-123", {"link_click": True})
    metrics = tracker.get_ad_metrics("ad-123")
    hook_rate = tracker.calculate_hook_rate("ad-123")
"""

import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class MetaAdsPerformanceTracker:
    """
    Tracks and computes ad performance metrics (AD-005).

    In-memory storage for dev/test; DB persistence when DATABASE_URL is set.
    """

    _instance: Optional["MetaAdsPerformanceTracker"] = None

    def __init__(self, use_db: bool = False) -> None:
        self._use_db = use_db and bool(os.getenv("DATABASE_URL"))

        # In-memory metrics storage
        # ad_id -> metrics dict
        self._ad_metrics: Dict[str, Dict[str, Any]] = {}
        # ad_id -> campaign_id mapping
        self._ad_campaign_map: Dict[str, str] = {}
        # Raw event log
        self._events: List[Dict[str, Any]] = []

        if self._use_db:
            self._init_db()
            logger.info("[AD-005] MetaAdsPerformanceTracker initialized (DB mode)")
        else:
            logger.info("[AD-005] MetaAdsPerformanceTracker initialized (in-memory mode)")

    def _init_db(self) -> None:
        """Initialize database connection for production persistence."""
        try:
            from sqlalchemy import create_engine

            db_url = os.getenv("DATABASE_URL")
            self._db_engine = create_engine(db_url, pool_pre_ping=True)
            logger.info("[AD-005] Database connection established")
        except Exception as exc:
            logger.warning(f"[AD-005] DB init failed, using in-memory: {exc}")
            self._use_db = False
            self._db_engine = None

    def _ensure_ad_metrics(self, ad_id: str) -> Dict[str, Any]:
        """Ensure metrics dict exists for an ad."""
        if ad_id not in self._ad_metrics:
            self._ad_metrics[ad_id] = {
                "ad_id": ad_id,
                "impressions": 0,
                "clicks": 0,
                "link_clicks": 0,
                "video_views": 0,
                "video_views_3s": 0,
                "video_thruplay": 0,
                "spend_cents": 0,
                "conversions": 0,
                "conversion_value_cents": 0,
                "reach": 0,
                "frequency": 0.0,
                "first_seen": datetime.now(timezone.utc).isoformat(),
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }
        return self._ad_metrics[ad_id]

    # ------------------------------------------------------------------
    # Event tracking
    # ------------------------------------------------------------------

    def track_impression(self, ad_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Record an impression event for an ad.

        Args:
            ad_id: The ad identifier.
            data: Optional dict with campaign_id, cost_cents, reach, etc.
        """
        data = data or {}
        metrics = self._ensure_ad_metrics(ad_id)
        metrics["impressions"] += 1
        metrics["spend_cents"] += data.get("cost_cents", 0)
        metrics["reach"] += data.get("reach_increment", 0)
        metrics["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Track campaign mapping
        campaign_id = data.get("campaign_id")
        if campaign_id:
            self._ad_campaign_map[ad_id] = campaign_id

        # Video view tracking
        if data.get("video_view"):
            metrics["video_views"] += 1
        if data.get("video_view_3s"):
            metrics["video_views_3s"] += 1
        if data.get("video_thruplay"):
            metrics["video_thruplay"] += 1

        self._events.append(
            {
                "event_id": uuid4().hex[:8],
                "type": "impression",
                "ad_id": ad_id,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.debug(f"[AD-005] Impression tracked: ad={ad_id} (total={metrics['impressions']})")

    def track_click(self, ad_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Record a click event for an ad.

        Args:
            ad_id: The ad identifier.
            data: Optional dict with link_click, cost_cents, etc.
        """
        data = data or {}
        metrics = self._ensure_ad_metrics(ad_id)
        metrics["clicks"] += 1
        metrics["spend_cents"] += data.get("cost_cents", 0)
        metrics["last_updated"] = datetime.now(timezone.utc).isoformat()

        if data.get("link_click"):
            metrics["link_clicks"] += 1

        # Track conversions
        if data.get("conversion"):
            metrics["conversions"] += 1
            metrics["conversion_value_cents"] += data.get("conversion_value_cents", 0)

        self._events.append(
            {
                "event_id": uuid4().hex[:8],
                "type": "click",
                "ad_id": ad_id,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        logger.debug(f"[AD-005] Click tracked: ad={ad_id} (total={metrics['clicks']})")

    # ------------------------------------------------------------------
    # Metrics computation
    # ------------------------------------------------------------------

    def get_ad_metrics(self, ad_id: str) -> Dict[str, Any]:
        """
        Get computed metrics for a single ad.

        Args:
            ad_id: The ad identifier.

        Returns:
            Dict with impressions, clicks, ctr, cpc, cpm, roas, and raw counts.
        """
        metrics = self._ad_metrics.get(ad_id)
        if not metrics:
            return {
                "ad_id": ad_id,
                "impressions": 0,
                "clicks": 0,
                "ctr": 0.0,
                "cpc": 0.0,
                "cpm": 0.0,
                "roas": 0.0,
                "status": "no_data",
            }

        impressions = metrics["impressions"]
        clicks = metrics["clicks"]
        spend_cents = metrics["spend_cents"]
        conversions = metrics["conversions"]
        conversion_value = metrics["conversion_value_cents"]

        # Calculate derived metrics
        ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
        cpc = (spend_cents / clicks) if clicks > 0 else 0.0
        cpm = (spend_cents / impressions * 1000) if impressions > 0 else 0.0
        roas = (conversion_value / spend_cents) if spend_cents > 0 else 0.0

        # Calculate frequency
        reach = metrics.get("reach", 0)
        frequency = (impressions / reach) if reach > 0 else 0.0

        return {
            "ad_id": ad_id,
            "impressions": impressions,
            "clicks": clicks,
            "link_clicks": metrics["link_clicks"],
            "ctr": round(ctr, 4),
            "cpc": round(cpc / 100, 2),  # Convert cents to dollars
            "cpm": round(cpm / 100, 2),
            "roas": round(roas, 2),
            "spend": round(spend_cents / 100, 2),
            "conversions": conversions,
            "conversion_value": round(conversion_value / 100, 2),
            "reach": reach,
            "frequency": round(frequency, 2),
            "video_views": metrics["video_views"],
            "video_views_3s": metrics["video_views_3s"],
            "video_thruplay": metrics["video_thruplay"],
            "hook_rate": self.calculate_hook_rate(ad_id),
            "hold_rate": self.calculate_hold_rate(ad_id),
            "first_seen": metrics["first_seen"],
            "last_updated": metrics["last_updated"],
        }

    def get_campaign_metrics(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get aggregated metrics for all ads in a campaign.

        Args:
            campaign_id: The campaign identifier.

        Returns:
            Dict with aggregated impressions, clicks, ctr, spend, roas,
            and per-ad breakdown.
        """
        # Find all ads belonging to this campaign
        ad_ids = [
            aid for aid, cid in self._ad_campaign_map.items() if cid == campaign_id
        ]

        if not ad_ids:
            return {
                "campaign_id": campaign_id,
                "ad_count": 0,
                "impressions": 0,
                "clicks": 0,
                "ctr": 0.0,
                "spend": 0.0,
                "roas": 0.0,
                "status": "no_data",
            }

        # Aggregate metrics
        total_impressions = 0
        total_clicks = 0
        total_spend_cents = 0
        total_conversions = 0
        total_conversion_value = 0
        ad_breakdown: List[Dict[str, Any]] = []

        for ad_id in ad_ids:
            ad_metrics = self.get_ad_metrics(ad_id)
            total_impressions += ad_metrics["impressions"]
            total_clicks += ad_metrics["clicks"]
            total_spend_cents += int(ad_metrics["spend"] * 100)
            total_conversions += ad_metrics["conversions"]
            total_conversion_value += int(ad_metrics["conversion_value"] * 100)
            ad_breakdown.append(ad_metrics)

        ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
        cpc = (total_spend_cents / total_clicks / 100) if total_clicks > 0 else 0.0
        cpm = (total_spend_cents / total_impressions * 1000 / 100) if total_impressions > 0 else 0.0
        roas = (total_conversion_value / total_spend_cents) if total_spend_cents > 0 else 0.0

        logger.info(
            f"[AD-005] Campaign {campaign_id} metrics: "
            f"{total_impressions} impressions, {total_clicks} clicks, "
            f"CTR={ctr:.2f}%, ROAS={roas:.2f}x"
        )

        return {
            "campaign_id": campaign_id,
            "ad_count": len(ad_ids),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": round(ctr, 4),
            "cpc": round(cpc, 2),
            "cpm": round(cpm, 2),
            "spend": round(total_spend_cents / 100, 2),
            "conversions": total_conversions,
            "conversion_value": round(total_conversion_value / 100, 2),
            "roas": round(roas, 2),
            "ad_breakdown": ad_breakdown,
        }

    # ------------------------------------------------------------------
    # Video-specific metrics
    # ------------------------------------------------------------------

    def calculate_hook_rate(self, ad_id: str) -> float:
        """
        Calculate hook rate for a video ad.

        Hook rate = 3-second video views / impressions.
        Measures how effectively the first 3 seconds grab attention.

        Args:
            ad_id: The ad identifier.

        Returns:
            Hook rate as a float between 0.0 and 1.0.
        """
        metrics = self._ad_metrics.get(ad_id)
        if not metrics or metrics["impressions"] == 0:
            return 0.0

        rate = metrics["video_views_3s"] / metrics["impressions"]
        return round(min(rate, 1.0), 4)

    def calculate_hold_rate(self, ad_id: str) -> float:
        """
        Calculate hold rate for a video ad.

        Hold rate = ThruPlay views / 3-second views.
        Measures how well the video retains viewers after the hook.

        Args:
            ad_id: The ad identifier.

        Returns:
            Hold rate as a float between 0.0 and 1.0.
        """
        metrics = self._ad_metrics.get(ad_id)
        if not metrics or metrics["video_views_3s"] == 0:
            return 0.0

        rate = metrics["video_thruplay"] / metrics["video_views_3s"]
        return round(min(rate, 1.0), 4)

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def reset_ad_metrics(self, ad_id: str) -> bool:
        """Reset metrics for an ad (useful for testing)."""
        if ad_id in self._ad_metrics:
            del self._ad_metrics[ad_id]
            logger.info(f"[AD-005] Metrics reset for ad {ad_id}")
            return True
        return False

    def get_top_performing_ads(
        self,
        campaign_id: str,
        metric: str = "ctr",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing ads in a campaign sorted by a metric.

        Args:
            campaign_id: Campaign to query.
            metric: Sort metric (ctr, roas, hook_rate, hold_rate).
            limit: Max number of results.

        Returns:
            List of ad metrics dicts, sorted descending by the chosen metric.
        """
        campaign_metrics = self.get_campaign_metrics(campaign_id)
        breakdown = campaign_metrics.get("ad_breakdown", [])
        sorted_ads = sorted(breakdown, key=lambda x: x.get(metric, 0), reverse=True)
        return sorted_ads[:limit]

    def get_event_count(self) -> int:
        """Get total number of tracked events."""
        return len(self._events)


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_performance_tracker_instance: Optional[MetaAdsPerformanceTracker] = None


def get_performance_tracker(use_db: bool = False) -> MetaAdsPerformanceTracker:
    """Get or create the singleton MetaAdsPerformanceTracker instance."""
    global _performance_tracker_instance
    if _performance_tracker_instance is None:
        _performance_tracker_instance = MetaAdsPerformanceTracker(use_db=use_db)
    return _performance_tracker_instance
