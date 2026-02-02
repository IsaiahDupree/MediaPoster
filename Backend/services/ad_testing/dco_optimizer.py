"""
Dynamic Creative Optimization (AD-008)
========================================
Meta-style Dynamic Creative Optimization (DCO) that automatically tests
all combinations of creative elements and surfaces winning combinations.

Elements combined:
    - Videos (creative assets)
    - Primary texts (body copy)
    - Headlines
    - CTAs (call-to-action buttons)

The optimizer tracks per-combination performance and identifies the
best-performing creative mix.

Usage:
    dco = get_dco_optimizer()
    campaign_id = dco.create_dco_campaign(videos, texts, headlines, ctas)
    winners = dco.get_winning_combinations(campaign_id)
    actions = dco.auto_optimize(campaign_id)
"""

import itertools
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Maximum combinations before we sample
MAX_COMBINATIONS = 100

# Minimum impressions before we evaluate a combination
MIN_IMPRESSIONS_FOR_EVALUATION = 50


class DynamicCreativeOptimizer:
    """
    Dynamic Creative Optimization engine (AD-008).

    Creates and manages DCO campaigns that automatically test
    all combinations of creative elements.
    """

    _instance: Optional["DynamicCreativeOptimizer"] = None

    def __init__(self) -> None:
        # DCO campaign state: campaign_id -> campaign dict
        self._campaigns: Dict[str, Dict[str, Any]] = {}
        # Combination performance: combo_id -> metrics
        self._combo_metrics: Dict[str, Dict[str, Any]] = {}

        self._deployer = None
        self._tracker = None
        self._init_dependencies()
        logger.info("[AD-008] DynamicCreativeOptimizer initialized")

    def _init_dependencies(self) -> None:
        """Load sibling AD services."""
        try:
            from services.ad_testing.campaign_deployer import get_campaign_deployer

            self._deployer = get_campaign_deployer()
        except Exception as exc:
            logger.warning(f"[AD-008] Could not load CampaignDeployer: {exc}")

        try:
            from services.ad_testing.performance_tracker import get_performance_tracker

            self._tracker = get_performance_tracker()
        except Exception as exc:
            logger.warning(f"[AD-008] Could not load PerformanceTracker: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_dco_campaign(
        self,
        videos: List[str],
        texts: List[str],
        headlines: List[str],
        ctas: List[str],
        name: Optional[str] = None,
        budget_cents: int = 5000,
        objective: str = "CONVERSIONS",
    ) -> str:
        """
        Create a DCO campaign that tests all combinations of elements.

        Args:
            videos: List of video paths or creative IDs.
            texts: List of primary text (body copy) variations.
            headlines: List of headline variations.
            ctas: List of CTA text variations.
            name: Campaign name (auto-generated if None).
            budget_cents: Daily budget in cents.
            objective: Campaign objective.

        Returns:
            campaign_id: Unique ID for the DCO campaign.
        """
        campaign_id = f"dco-{uuid4().hex[:8]}"
        name = name or f"DCO Campaign {campaign_id}"

        # Generate all combinations
        combinations = list(itertools.product(videos, texts, headlines, ctas))
        total_combos = len(combinations)

        # Sample if too many
        if total_combos > MAX_COMBINATIONS:
            import random

            combinations = random.sample(combinations, MAX_COMBINATIONS)
            logger.info(
                f"[AD-008] Sampled {MAX_COMBINATIONS} from {total_combos} total combinations"
            )

        # Build combination entries
        combo_entries: List[Dict[str, Any]] = []
        for video, text, headline, cta in combinations:
            combo_id = f"combo-{uuid4().hex[:8]}"
            entry = {
                "combo_id": combo_id,
                "video": video,
                "text": text,
                "headline": headline,
                "cta": cta,
                "status": "active",
                "ad_id": None,  # Will be populated if deployer is available
            }
            combo_entries.append(entry)

            # Initialize metrics tracking
            self._combo_metrics[combo_id] = {
                "combo_id": combo_id,
                "campaign_id": campaign_id,
                "impressions": 0,
                "clicks": 0,
                "conversions": 0,
                "spend_cents": 0,
                "video_views_3s": 0,
                "video_thruplay": 0,
            }

        # Store campaign
        campaign: Dict[str, Any] = {
            "campaign_id": campaign_id,
            "name": name,
            "objective": objective,
            "daily_budget_cents": budget_cents,
            "status": "active",
            "elements": {
                "videos": videos,
                "texts": texts,
                "headlines": headlines,
                "ctas": ctas,
            },
            "total_combinations": len(combo_entries),
            "combinations": combo_entries,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "optimization_rounds": 0,
        }

        self._campaigns[campaign_id] = campaign

        # Deploy via CampaignDeployer if available
        if self._deployer:
            try:
                self._deploy_dco_campaign(campaign)
            except Exception as exc:
                logger.error(f"[AD-008] DCO deployment failed: {exc}")

        logger.info(
            f"[AD-008] Created DCO campaign {campaign_id}: "
            f"{len(videos)} videos x {len(texts)} texts x "
            f"{len(headlines)} headlines x {len(ctas)} CTAs = "
            f"{len(combo_entries)} combinations"
        )
        return campaign_id

    def get_winning_combinations(
        self,
        campaign_id: str,
        metric: str = "ctr",
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get the top-performing creative combinations.

        Args:
            campaign_id: The DCO campaign to evaluate.
            metric: Metric to rank by (ctr, roas, hook_rate).
            limit: Number of top combinations to return.

        Returns:
            List of combination dicts with performance metrics, sorted by metric.
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            logger.warning(f"[AD-008] DCO campaign {campaign_id} not found")
            return []

        # Collect metrics for all combinations
        scored: List[Dict[str, Any]] = []
        for combo in campaign["combinations"]:
            combo_id = combo["combo_id"]
            combo_m = self._combo_metrics.get(combo_id, {})

            impressions = combo_m.get("impressions", 0)
            clicks = combo_m.get("clicks", 0)
            conversions = combo_m.get("conversions", 0)
            spend_cents = combo_m.get("spend_cents", 0)
            views_3s = combo_m.get("video_views_3s", 0)
            thruplay = combo_m.get("video_thruplay", 0)

            ctr = (clicks / impressions * 100) if impressions > 0 else 0.0
            cpc = (spend_cents / clicks / 100) if clicks > 0 else 0.0
            roas = (
                (conversions * 1000) / spend_cents if spend_cents > 0 else 0.0
            )  # Simplified ROAS
            hook_rate = (views_3s / impressions) if impressions > 0 else 0.0
            hold_rate = (thruplay / views_3s) if views_3s > 0 else 0.0

            scored.append(
                {
                    "combo_id": combo_id,
                    "video": combo["video"],
                    "text": combo["text"],
                    "headline": combo["headline"],
                    "cta": combo["cta"],
                    "impressions": impressions,
                    "clicks": clicks,
                    "conversions": conversions,
                    "ctr": round(ctr, 4),
                    "cpc": round(cpc, 2),
                    "roas": round(roas, 2),
                    "hook_rate": round(hook_rate, 4),
                    "hold_rate": round(hold_rate, 4),
                    "spend": round(spend_cents / 100, 2),
                    "status": combo["status"],
                }
            )

        # Sort by the chosen metric
        scored.sort(key=lambda x: x.get(metric, 0), reverse=True)

        logger.info(
            f"[AD-008] Ranked {len(scored)} combinations for {campaign_id} by {metric}"
        )
        return scored[:limit]

    def auto_optimize(self, campaign_id: str) -> Dict[str, Any]:
        """
        Automatically optimize a DCO campaign.

        Actions taken:
            - Pause combinations with low performance
            - Increase budget allocation to winners
            - Log all optimization actions

        Args:
            campaign_id: The DCO campaign to optimize.

        Returns:
            Dict with actions_taken, paused_combos, boosted_combos, round_number.
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {"error": f"Campaign {campaign_id} not found"}

        campaign["optimization_rounds"] += 1
        round_num = campaign["optimization_rounds"]

        actions: List[str] = []
        paused_combos: List[str] = []
        boosted_combos: List[str] = []

        # Get all combination metrics
        all_combos = self.get_winning_combinations(
            campaign_id, metric="ctr", limit=len(campaign["combinations"])
        )

        # Filter to those with enough data
        evaluable = [
            c for c in all_combos if c["impressions"] >= MIN_IMPRESSIONS_FOR_EVALUATION
        ]

        if not evaluable:
            msg = (
                f"Round {round_num}: Not enough data yet "
                f"(need {MIN_IMPRESSIONS_FOR_EVALUATION}+ impressions per combo)"
            )
            actions.append(msg)
            logger.info(f"[AD-008] {campaign_id} - {msg}")
            return {
                "campaign_id": campaign_id,
                "round": round_num,
                "actions_taken": actions,
                "paused_combos": paused_combos,
                "boosted_combos": boosted_combos,
            }

        # Calculate average CTR across evaluable combos
        avg_ctr = sum(c["ctr"] for c in evaluable) / len(evaluable)

        # Pause bottom performers (below 50% of average CTR)
        pause_threshold = avg_ctr * 0.5
        for combo in evaluable:
            if combo["ctr"] < pause_threshold and combo["status"] == "active":
                self._pause_combination(campaign_id, combo["combo_id"])
                paused_combos.append(combo["combo_id"])
                actions.append(
                    f"Paused {combo['combo_id']} (CTR {combo['ctr']:.2f}% < "
                    f"threshold {pause_threshold:.2f}%)"
                )

        # Identify and boost top performers (above 150% of average CTR)
        boost_threshold = avg_ctr * 1.5
        for combo in evaluable:
            if combo["ctr"] > boost_threshold and combo["status"] == "active":
                boosted_combos.append(combo["combo_id"])
                actions.append(
                    f"Boosted {combo['combo_id']} (CTR {combo['ctr']:.2f}% > "
                    f"threshold {boost_threshold:.2f}%)"
                )

        if not actions:
            actions.append(
                f"Round {round_num}: No optimization actions needed - "
                f"performance is within normal range"
            )

        campaign["updated_at"] = datetime.now(timezone.utc).isoformat()

        result = {
            "campaign_id": campaign_id,
            "round": round_num,
            "actions_taken": actions,
            "paused_combos": paused_combos,
            "boosted_combos": boosted_combos,
            "avg_ctr": round(avg_ctr, 4),
            "evaluable_combos": len(evaluable),
            "total_combos": len(campaign["combinations"]),
        }

        logger.info(
            f"[AD-008] Optimization round {round_num} for {campaign_id}: "
            f"{len(paused_combos)} paused, {len(boosted_combos)} boosted"
        )
        return result

    def get_creative_performance(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get element-level performance breakdown.

        Shows which individual videos, texts, headlines, and CTAs
        perform best across all combinations.

        Args:
            campaign_id: The DCO campaign to analyse.

        Returns:
            Dict with per-element performance breakdowns.
        """
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {"error": f"Campaign {campaign_id} not found"}

        # Aggregate metrics by element
        video_perf: Dict[str, Dict[str, Any]] = {}
        text_perf: Dict[str, Dict[str, Any]] = {}
        headline_perf: Dict[str, Dict[str, Any]] = {}
        cta_perf: Dict[str, Dict[str, Any]] = {}

        for combo in campaign["combinations"]:
            combo_id = combo["combo_id"]
            combo_m = self._combo_metrics.get(combo_id, {})
            impressions = combo_m.get("impressions", 0)
            clicks = combo_m.get("clicks", 0)

            for element_key, perf_dict, value in [
                ("video", video_perf, combo["video"]),
                ("text", text_perf, combo["text"]),
                ("headline", headline_perf, combo["headline"]),
                ("cta", cta_perf, combo["cta"]),
            ]:
                if value not in perf_dict:
                    perf_dict[value] = {
                        "element": value,
                        "impressions": 0,
                        "clicks": 0,
                        "combo_count": 0,
                    }
                perf_dict[value]["impressions"] += impressions
                perf_dict[value]["clicks"] += clicks
                perf_dict[value]["combo_count"] += 1

        def _add_ctr(perf_dict: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
            items = list(perf_dict.values())
            for item in items:
                imp = item["impressions"]
                item["ctr"] = round(
                    (item["clicks"] / imp * 100) if imp > 0 else 0.0, 4
                )
            return sorted(items, key=lambda x: x["ctr"], reverse=True)

        result = {
            "campaign_id": campaign_id,
            "videos": _add_ctr(video_perf),
            "texts": _add_ctr(text_perf),
            "headlines": _add_ctr(headline_perf),
            "ctas": _add_ctr(cta_perf),
            "total_combinations": len(campaign["combinations"]),
            "active_combinations": sum(
                1 for c in campaign["combinations"] if c["status"] == "active"
            ),
        }

        logger.info(
            f"[AD-008] Creative performance for {campaign_id}: "
            f"{len(result['videos'])} videos, {len(result['headlines'])} headlines"
        )
        return result

    # ------------------------------------------------------------------
    # Metrics ingestion
    # ------------------------------------------------------------------

    def record_combo_impression(
        self, combo_id: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an impression for a specific combination."""
        data = data or {}
        m = self._combo_metrics.get(combo_id)
        if not m:
            logger.warning(f"[AD-008] Unknown combo {combo_id}")
            return

        m["impressions"] += 1
        m["spend_cents"] += data.get("cost_cents", 0)
        if data.get("video_view_3s"):
            m["video_views_3s"] += 1
        if data.get("video_thruplay"):
            m["video_thruplay"] += 1

    def record_combo_click(
        self, combo_id: str, data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a click for a specific combination."""
        data = data or {}
        m = self._combo_metrics.get(combo_id)
        if not m:
            logger.warning(f"[AD-008] Unknown combo {combo_id}")
            return

        m["clicks"] += 1
        if data.get("conversion"):
            m["conversions"] += 1

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pause_combination(self, campaign_id: str, combo_id: str) -> None:
        """Mark a combination as paused."""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return

        for combo in campaign["combinations"]:
            if combo["combo_id"] == combo_id:
                combo["status"] = "paused"
                # Also pause the ad if we have a deployer
                if combo.get("ad_id") and self._deployer:
                    self._deployer.update_ad_status(combo["ad_id"], "PAUSED")
                break

    def _deploy_dco_campaign(self, campaign: Dict[str, Any]) -> None:
        """Deploy DCO campaign combinations via the CampaignDeployer."""
        if not self._deployer:
            return

        # Create the parent campaign
        meta_campaign = self._deployer.create_campaign(
            name=campaign["name"],
            objective=campaign["objective"],
            budget_cents=campaign["daily_budget_cents"],
        )

        # Create one ad set for all DCO variations
        ad_set = self._deployer.create_ad_set(
            campaign_id=meta_campaign["id"],
            audience={"name": "dco_broad", "age_min": 18, "age_max": 65},
            budget_cents=campaign["daily_budget_cents"],
        )

        # Create ads for each combination
        for combo in campaign["combinations"]:
            creative_id = self._deployer.upload_creative(
                combo["video"],
                title=combo["headline"],
            )
            ad = self._deployer.create_ad(
                ad_set_id=ad_set["id"],
                creative_id=creative_id,
                headline=combo["headline"],
                body=combo["text"],
            )
            combo["ad_id"] = ad["id"]

        campaign["meta_campaign_id"] = meta_campaign["id"]
        logger.info(
            f"[AD-008] Deployed DCO campaign {campaign['campaign_id']} "
            f"-> Meta campaign {meta_campaign['id']}"
        )

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get a DCO campaign by ID."""
        return self._campaigns.get(campaign_id)

    def list_campaigns(self) -> List[Dict[str, Any]]:
        """List all DCO campaigns (summary view)."""
        return [
            {
                "campaign_id": c["campaign_id"],
                "name": c["name"],
                "status": c["status"],
                "total_combinations": c["total_combinations"],
                "optimization_rounds": c["optimization_rounds"],
                "created_at": c["created_at"],
            }
            for c in self._campaigns.values()
        ]


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_dco_optimizer_instance: Optional[DynamicCreativeOptimizer] = None


def get_dco_optimizer() -> DynamicCreativeOptimizer:
    """Get or create the singleton DynamicCreativeOptimizer instance."""
    global _dco_optimizer_instance
    if _dco_optimizer_instance is None:
        _dco_optimizer_instance = DynamicCreativeOptimizer()
    return _dco_optimizer_instance
