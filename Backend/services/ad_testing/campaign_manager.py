"""
Meta Campaign Manager (AD-007)
================================
Operational campaign management: pause under-performers, scale winners,
duplicate ad sets, update bids, and monitor campaign health.

Integrates with:
    - MetaCampaignDeployer (AD-004) for campaign state
    - MetaAdsPerformanceTracker (AD-005) for metrics
    - AdAILearner (AD-006) for intelligent decisions

Usage:
    manager = get_campaign_manager()
    paused = manager.pause_underperformers("camp-123", threshold=0.5)
    scaled = manager.scale_winners("camp-123", scale_factor=1.5)
    health = manager.get_campaign_health("camp-123")
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Default thresholds
DEFAULT_UNDERPERFORMER_CTR_THRESHOLD = 0.5  # CTR % below which we pause
DEFAULT_WINNER_CTR_THRESHOLD = 1.5  # CTR % above which we consider scaling
MIN_IMPRESSIONS_FOR_DECISION = 100  # Minimum impressions before acting


class MetaCampaignManager:
    """
    Operational campaign management service (AD-007).

    Provides automated and manual campaign operations:
    pausing, scaling, duplicating, and bid management.
    """

    _instance: Optional["MetaCampaignManager"] = None

    def __init__(self) -> None:
        self._deployer = None
        self._tracker = None
        self._action_log: List[Dict[str, Any]] = []
        self._init_dependencies()
        logger.info("[AD-007] MetaCampaignManager initialized")

    def _init_dependencies(self) -> None:
        """Load sibling AD services."""
        try:
            from services.ad_testing.campaign_deployer import get_campaign_deployer

            self._deployer = get_campaign_deployer()
        except Exception as exc:
            logger.warning(f"[AD-007] Could not load CampaignDeployer: {exc}")

        try:
            from services.ad_testing.performance_tracker import get_performance_tracker

            self._tracker = get_performance_tracker()
        except Exception as exc:
            logger.warning(f"[AD-007] Could not load PerformanceTracker: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def pause_underperformers(
        self,
        campaign_id: str,
        threshold: Optional[float] = None,
        min_impressions: int = MIN_IMPRESSIONS_FOR_DECISION,
    ) -> List[str]:
        """
        Pause ads that are under-performing relative to a CTR threshold.

        Args:
            campaign_id: The campaign to evaluate.
            threshold: CTR percentage below which ads are paused.
                       Defaults to DEFAULT_UNDERPERFORMER_CTR_THRESHOLD.
            min_impressions: Minimum impressions before an ad is evaluated.

        Returns:
            List of ad IDs that were paused.
        """
        threshold = threshold if threshold is not None else DEFAULT_UNDERPERFORMER_CTR_THRESHOLD
        paused_ids: List[str] = []

        metrics = self._get_campaign_metrics(campaign_id)
        if not metrics:
            logger.warning(f"[AD-007] No metrics for campaign {campaign_id}")
            return paused_ids

        for ad in metrics.get("ad_breakdown", []):
            ad_id = ad.get("ad_id")
            impressions = ad.get("impressions", 0)
            ctr = ad.get("ctr", 0)

            if impressions < min_impressions:
                logger.debug(
                    f"[AD-007] Skipping {ad_id} - only {impressions} impressions"
                )
                continue

            if ctr < threshold:
                success = self._pause_ad(ad_id)
                if success:
                    paused_ids.append(ad_id)
                    self._log_action(
                        "pause",
                        campaign_id,
                        ad_id,
                        f"CTR {ctr:.2f}% below threshold {threshold:.2f}%",
                    )

        logger.info(
            f"[AD-007] Paused {len(paused_ids)} underperformers in {campaign_id} "
            f"(threshold={threshold}%)"
        )
        return paused_ids

    def scale_winners(
        self,
        campaign_id: str,
        scale_factor: float = 1.5,
        ctr_threshold: Optional[float] = None,
        min_impressions: int = MIN_IMPRESSIONS_FOR_DECISION,
    ) -> List[str]:
        """
        Scale budget for winning ads by increasing their ad set budget.

        Args:
            campaign_id: The campaign to evaluate.
            scale_factor: Multiplier for the ad set budget (e.g., 1.5 = +50%).
            ctr_threshold: Minimum CTR to qualify as a winner.
            min_impressions: Minimum impressions before an ad is evaluated.

        Returns:
            List of ad IDs whose ad sets were scaled.
        """
        ctr_threshold = ctr_threshold if ctr_threshold is not None else DEFAULT_WINNER_CTR_THRESHOLD
        scaled_ids: List[str] = []

        metrics = self._get_campaign_metrics(campaign_id)
        if not metrics:
            logger.warning(f"[AD-007] No metrics for campaign {campaign_id}")
            return scaled_ids

        # Track which ad sets have already been scaled to avoid double-scaling
        scaled_ad_sets: set = set()

        for ad in metrics.get("ad_breakdown", []):
            ad_id = ad.get("ad_id")
            impressions = ad.get("impressions", 0)
            ctr = ad.get("ctr", 0)

            if impressions < min_impressions:
                continue

            if ctr >= ctr_threshold:
                # Find the ad's ad set and scale it
                ad_set_id = self._get_ad_set_for_ad(ad_id)
                if ad_set_id and ad_set_id not in scaled_ad_sets:
                    success = self._scale_ad_set(ad_set_id, scale_factor)
                    if success:
                        scaled_ids.append(ad_id)
                        scaled_ad_sets.add(ad_set_id)
                        self._log_action(
                            "scale",
                            campaign_id,
                            ad_id,
                            f"CTR {ctr:.2f}% above threshold, "
                            f"budget x{scale_factor}",
                        )

        logger.info(
            f"[AD-007] Scaled {len(scaled_ids)} winners in {campaign_id} "
            f"(factor={scale_factor}x)"
        )
        return scaled_ids

    def duplicate_ad_set(self, ad_set_id: str) -> str:
        """
        Duplicate an ad set (and its ads) for further testing.

        Args:
            ad_set_id: The ad set to duplicate.

        Returns:
            New ad set ID (empty string if duplication failed).
        """
        if not self._deployer:
            logger.error("[AD-007] No deployer available for duplication")
            return ""

        original = self._deployer.get_ad_set(ad_set_id)
        if not original:
            logger.error(f"[AD-007] Ad set {ad_set_id} not found")
            return ""

        # Create new ad set with same params
        new_ad_set = self._deployer.create_ad_set(
            campaign_id=original["campaign_id"],
            audience=original["audience"],
            budget_cents=original["daily_budget_cents"],
            optimization_goal=original.get("optimization_goal", "CONVERSIONS"),
            bid_amount_cents=original.get("bid_amount_cents"),
            placements=original.get("placements"),
        )

        new_ad_set_id = new_ad_set["id"]

        # Duplicate ads
        for ad_id in original.get("ads", []):
            original_ad = self._deployer.get_ad(ad_id)
            if original_ad:
                self._deployer.create_ad(
                    ad_set_id=new_ad_set_id,
                    creative_id=original_ad["creative_id"],
                    headline=original_ad["headline"],
                    body=original_ad["body"],
                    cta_type=original_ad.get("cta_type", "LEARN_MORE"),
                    link_url=original_ad.get("link_url"),
                )

        self._log_action(
            "duplicate",
            original["campaign_id"],
            ad_set_id,
            f"Duplicated to {new_ad_set_id}",
        )

        logger.info(
            f"[AD-007] Duplicated ad set {ad_set_id} -> {new_ad_set_id} "
            f"({len(original.get('ads', []))} ads)"
        )
        return new_ad_set_id

    def update_bid(self, ad_set_id: str, new_bid_cents: int) -> bool:
        """
        Update the bid amount for an ad set.

        Args:
            ad_set_id: The ad set to update.
            new_bid_cents: New bid amount in cents.

        Returns:
            True if updated successfully.
        """
        if not self._deployer:
            logger.error("[AD-007] No deployer available for bid update")
            return False

        ad_set = self._deployer.get_ad_set(ad_set_id)
        if not ad_set:
            logger.error(f"[AD-007] Ad set {ad_set_id} not found")
            return False

        old_bid = ad_set.get("bid_amount_cents")
        ad_set["bid_amount_cents"] = new_bid_cents
        ad_set["updated_at"] = datetime.now(timezone.utc).isoformat()

        self._log_action(
            "bid_update",
            ad_set.get("campaign_id", ""),
            ad_set_id,
            f"Bid: {old_bid} -> {new_bid_cents} cents",
        )

        logger.info(
            f"[AD-007] Updated bid for {ad_set_id}: "
            f"{old_bid} -> {new_bid_cents} cents"
        )
        return True

    def get_campaign_health(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get comprehensive health report for a campaign.

        Args:
            campaign_id: The campaign to evaluate.

        Returns:
            Dict with status, metrics_summary, alerts, active_ad_count,
            paused_ad_count, and action_history.
        """
        health: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "status": "unknown",
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "metrics_summary": {},
            "alerts": [],
            "active_ad_count": 0,
            "paused_ad_count": 0,
            "total_ad_count": 0,
            "action_history": [],
        }

        # Get campaign from deployer
        if self._deployer:
            campaign = self._deployer.get_campaign(campaign_id)
            if campaign:
                health["status"] = campaign.get("status", "unknown")

                # Count ad statuses
                for ad_set_id in campaign.get("ad_sets", []):
                    ad_set = self._deployer.get_ad_set(ad_set_id)
                    if ad_set:
                        for ad_id in ad_set.get("ads", []):
                            ad = self._deployer.get_ad(ad_id)
                            if ad:
                                health["total_ad_count"] += 1
                                if ad.get("status") == "ACTIVE":
                                    health["active_ad_count"] += 1
                                elif ad.get("status") == "PAUSED":
                                    health["paused_ad_count"] += 1

        # Get metrics
        metrics = self._get_campaign_metrics(campaign_id)
        if metrics and metrics.get("status") != "no_data":
            health["metrics_summary"] = {
                "impressions": metrics.get("impressions", 0),
                "clicks": metrics.get("clicks", 0),
                "ctr": metrics.get("ctr", 0),
                "spend": metrics.get("spend", 0),
                "roas": metrics.get("roas", 0),
                "ad_count": metrics.get("ad_count", 0),
            }

            # Generate alerts
            if metrics.get("ctr", 0) < 0.3 and metrics.get("impressions", 0) > 500:
                health["alerts"].append(
                    {
                        "level": "warning",
                        "message": f"Low CTR ({metrics['ctr']:.2f}%) - consider refreshing creatives",
                    }
                )

            if metrics.get("roas", 0) < 1.0 and metrics.get("spend", 0) > 10:
                health["alerts"].append(
                    {
                        "level": "critical",
                        "message": f"Below-breakeven ROAS ({metrics['roas']:.2f}x) - review campaign",
                    }
                )

            if health["active_ad_count"] == 0 and health["total_ad_count"] > 0:
                health["alerts"].append(
                    {
                        "level": "critical",
                        "message": "All ads are paused - campaign is not running",
                    }
                )

            if metrics.get("spend", 0) == 0 and metrics.get("impressions", 0) == 0:
                health["alerts"].append(
                    {
                        "level": "info",
                        "message": "Campaign has not started delivering yet",
                    }
                )

        # Recent actions
        health["action_history"] = [
            a for a in self._action_log if a.get("campaign_id") == campaign_id
        ][-10:]

        logger.info(
            f"[AD-007] Health check for {campaign_id}: "
            f"status={health['status']}, alerts={len(health['alerts'])}"
        )
        return health

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pause_ad(self, ad_id: str) -> bool:
        """Pause a single ad."""
        if self._deployer:
            return self._deployer.update_ad_status(ad_id, "PAUSED")
        logger.warning(f"[AD-007] Cannot pause {ad_id} - no deployer")
        return False

    def _scale_ad_set(self, ad_set_id: str, factor: float) -> bool:
        """Scale an ad set's budget by a factor."""
        if not self._deployer:
            return False

        ad_set = self._deployer.get_ad_set(ad_set_id)
        if not ad_set:
            return False

        old_budget = ad_set["daily_budget_cents"]
        new_budget = int(old_budget * factor)
        ad_set["daily_budget_cents"] = new_budget
        ad_set["updated_at"] = datetime.now(timezone.utc).isoformat()

        logger.debug(
            f"[AD-007] Scaled ad set {ad_set_id}: "
            f"${old_budget / 100:.2f} -> ${new_budget / 100:.2f}"
        )
        return True

    def _get_ad_set_for_ad(self, ad_id: str) -> Optional[str]:
        """Find which ad set contains an ad."""
        if not self._deployer:
            return None

        ad = self._deployer.get_ad(ad_id)
        if ad:
            return ad.get("ad_set_id")
        return None

    def _get_campaign_metrics(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve campaign metrics from the performance tracker."""
        if self._tracker:
            return self._tracker.get_campaign_metrics(campaign_id)
        return None

    def _log_action(
        self,
        action_type: str,
        campaign_id: str,
        target_id: str,
        details: str,
    ) -> None:
        """Log a management action."""
        self._action_log.append(
            {
                "action_id": uuid4().hex[:8],
                "action_type": action_type,
                "campaign_id": campaign_id,
                "target_id": target_id,
                "details": details,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def get_action_log(
        self, campaign_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get management action history, optionally filtered by campaign."""
        log = self._action_log
        if campaign_id:
            log = [a for a in log if a.get("campaign_id") == campaign_id]
        return log[-limit:]


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_campaign_manager_instance: Optional[MetaCampaignManager] = None


def get_campaign_manager() -> MetaCampaignManager:
    """Get or create the singleton MetaCampaignManager instance."""
    global _campaign_manager_instance
    if _campaign_manager_instance is None:
        _campaign_manager_instance = MetaCampaignManager()
    return _campaign_manager_instance
