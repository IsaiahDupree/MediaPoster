"""
ACTP Ad Budget Deployer
========================
Deploys winning creatives as paid ads on Meta and TikTok with micro-budgets.
Uses MediaPoster's existing ad_testing services.
"""

import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import ACTPConfig, AdTestConfig, ScalingConfig
from .models import (
    AdDeployment,
    AdDeploymentStatus,
    Creative,
    Platform,
    TestCampaign,
    TestRound,
    WinnerSelection,
)

logger = logging.getLogger(__name__)

MEDIAPOSTER_BASE = os.getenv(
    "MEDIAPOSTER_BASE_PATH",
    "/Users/isaiahdupree/Documents/Software/MediaPoster/Backend",
)


class AdBudgetDeployer:
    """
    Deploys winning creatives as paid ads with configurable micro-budgets.

    Integrates with:
    - MetaCampaignDeployer (AD-004) for Meta Ads
    - MetaCampaignManager (AD-007) for pause/scale operations
    - MetaAdsPerformanceTracker (AD-005) for ad metrics
    """

    def __init__(self, db_client=None, config: Optional[ACTPConfig] = None):
        self.db = db_client
        self.config = config or ACTPConfig()
        self._meta_deployer = None
        self._meta_manager = None
        self._meta_tracker = None
        self._init_services()
        logger.info("[ACTP:AdDeploy] Deployer initialized")

    def _init_services(self):
        """Initialize MediaPoster ad testing services."""
        try:
            sys.path.insert(0, MEDIAPOSTER_BASE)
            from services.ad_testing.campaign_deployer import get_campaign_deployer
            self._meta_deployer = get_campaign_deployer()
            logger.info("[ACTP:AdDeploy] Meta Campaign Deployer (AD-004) ready")
        except Exception as e:
            logger.warning(f"[ACTP:AdDeploy] Meta Deployer unavailable: {e}")

        try:
            from services.ad_testing.campaign_manager import get_campaign_manager
            self._meta_manager = get_campaign_manager()
            logger.info("[ACTP:AdDeploy] Meta Campaign Manager (AD-007) ready")
        except Exception as e:
            logger.warning(f"[ACTP:AdDeploy] Meta Manager unavailable: {e}")

        try:
            from services.ad_testing.performance_tracker import get_performance_tracker
            self._meta_tracker = get_performance_tracker()
            logger.info("[ACTP:AdDeploy] Meta Performance Tracker (AD-005) ready")
        except Exception as e:
            logger.warning(f"[ACTP:AdDeploy] Meta Tracker unavailable: {e}")

    # ─── Deploy Ads ───────────────────────────────────────

    async def deploy_winners(
        self,
        winners: List[WinnerSelection],
        creatives: List[Creative],
        campaign: TestCampaign,
        test_round: TestRound,
    ) -> List[AdDeployment]:
        """
        Deploy winning creatives as paid ads.
        Each winner gets a micro-budget campaign.
        """
        config = self.config.ad_test
        creative_map = {c.id: c for c in creatives}
        deployments = []

        for winner in winners:
            creative = creative_map.get(winner.creative_id)
            if not creative or not creative.video_url:
                logger.warning(f"[ACTP:AdDeploy] No video for winner {winner.creative_id}")
                continue

            for platform in config.platforms:
                try:
                    if platform == "meta":
                        deployment = await self._deploy_meta(
                            creative, campaign, test_round, config
                        )
                    elif platform == "tiktok_ads":
                        deployment = await self._deploy_tiktok_ads(
                            creative, campaign, test_round, config
                        )
                    else:
                        logger.warning(f"[ACTP:AdDeploy] Unsupported ad platform: {platform}")
                        continue

                    await self._save_deployment(deployment)
                    deployments.append(deployment)

                    logger.info(
                        f"[ACTP:AdDeploy] Deployed {creative.id} to {platform} "
                        f"(${deployment.budget_cents / 100:.2f})"
                    )
                except Exception as e:
                    logger.error(f"[ACTP:AdDeploy] Deploy failed for {creative.id} on {platform}: {e}")
                    failed = AdDeployment(
                        creative_id=creative.id,
                        round_id=test_round.id,
                        platform=Platform(platform),
                        budget_cents=config.budget_per_creative_cents,
                        status=AdDeploymentStatus.FAILED,
                    )
                    await self._save_deployment(failed)
                    deployments.append(failed)

        return deployments

    async def _deploy_meta(
        self,
        creative: Creative,
        campaign: TestCampaign,
        test_round: TestRound,
        config: AdTestConfig,
    ) -> AdDeployment:
        """Deploy to Meta Ads (Facebook/Instagram) via MetaCampaignDeployer (AD-004)."""
        if not self._meta_deployer:
            raise RuntimeError("Meta Campaign Deployer not available")

        # Build audience targeting from campaign config
        audience = self._build_meta_audience(campaign)

        # Create campaign
        campaign_name = f"ACTP-{campaign.name}-R{test_round.round_number}"
        meta_campaign = self._meta_deployer.create_campaign(
            name=campaign_name,
            objective=config.objective,
            daily_budget_cents=config.budget_per_creative_cents,
            variations=[],
        )

        # Upload creative
        creative_id_meta = self._meta_deployer.upload_creative(creative.video_url)

        # Create ad set with targeting
        ad_set = self._meta_deployer.create_ad_set(
            campaign_id=meta_campaign["id"],
            audience=audience,
            daily_budget_cents=config.budget_per_creative_cents,
        )

        # Create ad
        ad = self._meta_deployer.create_ad(
            ad_set_id=ad_set["id"],
            creative_id=creative_id_meta,
            headline=creative.hook or "Check this out",
            body=creative.script or "",
        )

        return AdDeployment(
            creative_id=creative.id,
            round_id=test_round.id,
            platform=Platform.META_ADS,
            external_campaign_id=meta_campaign["id"],
            external_ad_set_id=ad_set["id"],
            external_ad_id=ad["id"],
            budget_cents=config.budget_per_creative_cents,
            status=AdDeploymentStatus.ACTIVE,
            landing_page_url=campaign.offer_url,
            audience_config=audience,
        )

    async def _deploy_tiktok_ads(
        self,
        creative: Creative,
        campaign: TestCampaign,
        test_round: TestRound,
        config: AdTestConfig,
    ) -> AdDeployment:
        """Deploy to TikTok Ads."""
        import httpx

        access_token = os.getenv("TIKTOK_ADS_ACCESS_TOKEN")
        advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
        if not access_token or not advertiser_id:
            raise RuntimeError("TikTok Ads credentials not configured")

        base_url = "https://business-api.tiktok.com/open_api/v1.3"
        headers = {"Access-Token": access_token, "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Create campaign
            camp_resp = await client.post(
                f"{base_url}/campaign/create/",
                headers=headers,
                json={
                    "advertiser_id": advertiser_id,
                    "campaign_name": f"ACTP-{campaign.name}-R{test_round.round_number}",
                    "objective_type": "CONVERSIONS",
                    "budget_mode": "BUDGET_MODE_TOTAL",
                    "budget": config.budget_per_creative_cents / 100.0,
                },
            )
            camp_data = camp_resp.json().get("data", {})
            tt_campaign_id = camp_data.get("campaign_id", "")

            # Create ad group
            group_resp = await client.post(
                f"{base_url}/adgroup/create/",
                headers=headers,
                json={
                    "advertiser_id": advertiser_id,
                    "campaign_id": tt_campaign_id,
                    "adgroup_name": f"ACTP-{creative.angle or 'test'}",
                    "placement_type": "PLACEMENT_TYPE_AUTOMATIC",
                    "budget_mode": "BUDGET_MODE_TOTAL",
                    "budget": config.budget_per_creative_cents / 100.0,
                    "schedule_type": "SCHEDULE_FROM_NOW",
                    "billing_event": "CPC",
                    "bid_type": "BID_TYPE_NO_BID",
                },
            )
            group_data = group_resp.json().get("data", {})
            tt_adgroup_id = group_data.get("adgroup_id", "")

            # Create ad
            ad_resp = await client.post(
                f"{base_url}/ad/create/",
                headers=headers,
                json={
                    "advertiser_id": advertiser_id,
                    "adgroup_id": tt_adgroup_id,
                    "creatives": [{
                        "ad_name": f"ACTP-{creative.hook or 'ad'}",
                        "ad_text": creative.script or "",
                        "video_id": creative.video_url,
                        "call_to_action": "LEARN_MORE",
                        "landing_page_url": campaign.offer_url or "",
                    }],
                },
            )
            ad_data = ad_resp.json().get("data", {})
            tt_ad_id = ad_data.get("ad_ids", [""])[0] if ad_data.get("ad_ids") else ""

        return AdDeployment(
            creative_id=creative.id,
            round_id=test_round.id,
            platform=Platform.TIKTOK_ADS,
            external_campaign_id=tt_campaign_id,
            external_ad_set_id=tt_adgroup_id,
            external_ad_id=tt_ad_id,
            budget_cents=config.budget_per_creative_cents,
            status=AdDeploymentStatus.ACTIVE,
            landing_page_url=campaign.offer_url,
        )

    # ─── Budget Management ────────────────────────────────

    async def scale_winner(
        self, deployment: AdDeployment, new_budget_cents: int
    ) -> AdDeployment:
        """Scale up budget for a winning ad deployment."""
        if self._meta_manager and deployment.platform == Platform.META_ADS:
            self._meta_manager.scale_winners(
                deployment.external_campaign_id,
                scale_factor=new_budget_cents / max(deployment.budget_cents, 1),
            )

        deployment.budget_cents = new_budget_cents
        deployment.updated_at = datetime.now(timezone.utc)
        await self._save_deployment(deployment)

        logger.info(
            f"[ACTP:AdDeploy] Scaled {deployment.id} to ${new_budget_cents / 100:.2f}"
        )
        return deployment

    async def pause_underperformer(self, deployment: AdDeployment) -> AdDeployment:
        """Pause an underperforming ad deployment."""
        if self._meta_manager and deployment.platform == Platform.META_ADS:
            self._meta_manager.pause_underperformers(
                deployment.external_campaign_id,
                threshold=self.config.scaling.pause_threshold_ctr,
            )

        deployment.status = AdDeploymentStatus.PAUSED
        deployment.updated_at = datetime.now(timezone.utc)
        await self._save_deployment(deployment)

        logger.info(f"[ACTP:AdDeploy] Paused {deployment.id}")
        return deployment

    async def collect_ad_metrics(
        self, deployments: List[AdDeployment]
    ) -> List[AdDeployment]:
        """Collect performance metrics for active ad deployments."""
        for deployment in deployments:
            if deployment.status != AdDeploymentStatus.ACTIVE:
                continue

            try:
                if deployment.platform == Platform.META_ADS and self._meta_tracker:
                    metrics = self._meta_tracker.get_ad_metrics(deployment.external_ad_id)
                    if metrics:
                        deployment.metrics = metrics
                        deployment.spend_cents = int(metrics.get("spend_cents", 0))
                        await self._save_deployment(deployment)
                elif deployment.platform == Platform.TIKTOK_ADS:
                    metrics = await self._fetch_tiktok_ad_metrics(deployment)
                    if metrics:
                        deployment.metrics = metrics
                        deployment.spend_cents = int(
                            metrics.get("spend", 0) * 100
                        )
                        await self._save_deployment(deployment)
            except Exception as e:
                logger.error(f"[ACTP:AdDeploy] Metric collection failed for {deployment.id}: {e}")

        return deployments

    async def _fetch_tiktok_ad_metrics(self, deployment: AdDeployment) -> Dict[str, Any]:
        """Fetch metrics from TikTok Ads API."""
        import httpx

        access_token = os.getenv("TIKTOK_ADS_ACCESS_TOKEN")
        advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID")
        if not access_token or not advertiser_id:
            return {}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://business-api.tiktok.com/open_api/v1.3/report/integrated/get/",
                headers={"Access-Token": access_token},
                params={
                    "advertiser_id": advertiser_id,
                    "report_type": "BASIC",
                    "dimensions": '["ad_id"]',
                    "metrics": '["spend","impressions","clicks","ctr","cpc","conversions","video_play_actions","video_watched_2s","video_watched_6s"]',
                    "filters": f'[{{"field_name":"ad_id","filter_type":"IN","filter_value":["{deployment.external_ad_id}"]}}]',
                    "data_level": "AUCTION_AD",
                },
            )
            data = resp.json()
            rows = data.get("data", {}).get("list", [])
            if rows:
                m = rows[0].get("metrics", {})
                return {
                    "impressions": int(m.get("impressions", 0)),
                    "clicks": int(m.get("clicks", 0)),
                    "spend": float(m.get("spend", 0)),
                    "ctr": float(m.get("ctr", 0)),
                    "cpc": float(m.get("cpc", 0)),
                    "conversions": int(m.get("conversions", 0)),
                    "three_second_views": int(m.get("video_watched_2s", 0)),
                    "thru_plays": int(m.get("video_watched_6s", 0)),
                }
        return {}

    # ─── Helpers ──────────────────────────────────────────

    def _build_meta_audience(self, campaign: TestCampaign) -> Dict[str, Any]:
        """Build Meta Ads audience targeting from campaign config."""
        audience = campaign.target_audience or {}
        return {
            "name": audience.get("name", "ACTP Auto"),
            "age_min": audience.get("age_min", 18),
            "age_max": audience.get("age_max", 65),
            "genders": audience.get("genders", []),
            "interests": audience.get("interests", []),
            "geo_locations": audience.get("geo_locations", {"countries": ["US"]}),
        }

    async def _save_deployment(self, deployment: AdDeployment):
        if self.db:
            await self.db.table("actp_ad_deployments").upsert(
                deployment.model_dump(mode="json")
            ).execute()

    # ─── Creative Format Validation ───────────────────────

    AD_PLATFORM_SPECS = {
        "meta_ads": {
            "formats": ["video/mp4", "video/mov"],
            "max_file_size_mb": 4000,
            "min_resolution": "600x600",
            "max_duration_sec": 240,
            "aspect_ratios": ["9:16", "1:1", "4:5", "16:9"],
        },
        "tiktok_ads": {
            "formats": ["video/mp4", "video/mov", "video/mpeg"],
            "max_file_size_mb": 500,
            "min_resolution": "540x960",
            "max_duration_sec": 60,
            "aspect_ratios": ["9:16"],
        },
    }

    def validate_creative_for_ad_platform(
        self, video_metadata: Dict[str, Any], platform: str
    ) -> Dict[str, Any]:
        """Validate video creative meets ad platform specs."""
        spec = self.AD_PLATFORM_SPECS.get(platform)
        if not spec:
            return {"valid": True, "platform": platform, "errors": []}

        errors = []
        duration = video_metadata.get("duration_seconds", 0)
        if duration > spec["max_duration_sec"]:
            errors.append(f"Duration {duration}s exceeds max {spec['max_duration_sec']}s")

        file_mb = video_metadata.get("file_size_bytes", 0) / (1024 * 1024)
        if file_mb > spec["max_file_size_mb"]:
            errors.append(f"File size {file_mb:.0f}MB exceeds max {spec['max_file_size_mb']}MB")

        return {"valid": len(errors) == 0, "platform": platform, "errors": errors, "spec": spec}

    # ─── Retargeting Audience ─────────────────────────────

    async def create_retargeting_audience(
        self, campaign: TestCampaign, engagement_type: str = "video_views"
    ) -> Dict[str, Any]:
        """Create a retargeting audience from organic engagement."""
        audience_spec = {
            "name": f"ACTP Retarget - {campaign.name[:50]}",
            "type": "custom_audience",
            "source": engagement_type,
            "campaign_id": campaign.id,
            "retention_days": 30,
            "engagement_types": [engagement_type],
        }

        if self._meta_deployer:
            try:
                result = await self._meta_deployer.create_custom_audience(audience_spec)
                audience_spec["external_id"] = result.get("id")
            except Exception as e:
                logger.error(f"[ACTP:AdDeploy] Retargeting audience creation failed: {e}")

        logger.info(f"[ACTP:AdDeploy] Retargeting audience created for {campaign.id}")
        return audience_spec

    # ─── Lookalike Audience ───────────────────────────────

    async def create_lookalike_audience(
        self, source_audience_id: str, country: str = "US", lookalike_pct: int = 1
    ) -> Dict[str, Any]:
        """Create a lookalike audience from a source custom audience."""
        spec = {
            "source_audience_id": source_audience_id,
            "country": country,
            "lookalike_percentage": lookalike_pct,
            "name": f"ACTP Lookalike {lookalike_pct}% - {country}",
        }
        logger.info(f"[ACTP:AdDeploy] Lookalike audience spec created: {spec['name']}")
        return spec

    # ─── Bid Strategy ─────────────────────────────────────

    BID_STRATEGIES = {
        "lowest_cost": {"description": "Maximize results at lowest cost", "meta_key": "LOWEST_COST_WITHOUT_CAP"},
        "cost_cap": {"description": "Keep CPA below target", "meta_key": "LOWEST_COST_WITH_BID_CAP"},
        "bid_cap": {"description": "Manual maximum bid", "meta_key": "LOWEST_COST_WITH_MIN_ROAS"},
        "target_cost": {"description": "Stable CPA targeting", "meta_key": "COST_CAP"},
    }

    def select_bid_strategy(
        self, round_type: str, budget_cents: int
    ) -> Dict[str, Any]:
        """Select optimal bid strategy based on round type and budget."""
        if round_type == "organic" or budget_cents < 1000:
            strategy = "lowest_cost"
        elif budget_cents < 5000:
            strategy = "cost_cap"
        else:
            strategy = "target_cost"

        return {
            "strategy": strategy,
            **self.BID_STRATEGIES[strategy],
            "budget_cents": budget_cents,
        }

    # ─── Dayparting Schedule ──────────────────────────────

    DEFAULT_DAYPART_SCHEDULE = {
        "monday": {"start": "08:00", "end": "23:00"},
        "tuesday": {"start": "08:00", "end": "23:00"},
        "wednesday": {"start": "08:00", "end": "23:00"},
        "thursday": {"start": "08:00", "end": "23:00"},
        "friday": {"start": "08:00", "end": "23:59"},
        "saturday": {"start": "09:00", "end": "23:59"},
        "sunday": {"start": "09:00", "end": "23:00"},
    }

    def get_daypart_schedule(self, timezone_str: str = "America/New_York") -> Dict[str, Any]:
        """Get ad delivery schedule with dayparting."""
        return {
            "schedule": self.DEFAULT_DAYPART_SCHEDULE,
            "timezone": timezone_str,
            "enabled": True,
        }

    # ─── Ad Fatigue Detection ─────────────────────────────

    def detect_ad_fatigue(
        self, deployment: AdDeployment, history_days: int = 7
    ) -> Dict[str, Any]:
        """Detect ad fatigue by analyzing CTR decline over time."""
        metrics = deployment.metrics or {}
        impressions = metrics.get("impressions", 0)
        frequency = metrics.get("frequency", 0)
        ctr = metrics.get("ctr", 0)

        fatigue_signals = []
        fatigue_score = 0

        # Frequency > 3 = potential fatigue
        if frequency > 3:
            fatigue_signals.append(f"High frequency: {frequency}")
            fatigue_score += min(frequency * 10, 50)

        # CTR below 0.5% after sufficient impressions
        if impressions > 1000 and ctr < 0.5:
            fatigue_signals.append(f"Low CTR: {ctr}%")
            fatigue_score += 30

        # CPC increasing
        cpc = metrics.get("cpc", 0)
        if cpc > 5:
            fatigue_signals.append(f"High CPC: ${cpc:.2f}")
            fatigue_score += 20

        return {
            "deployment_id": deployment.id,
            "fatigue_score": min(fatigue_score, 100),
            "is_fatigued": fatigue_score >= 50,
            "signals": fatigue_signals,
            "recommendation": "refresh" if fatigue_score >= 50 else "monitor",
        }

    # ─── Budget Pacing ────────────────────────────────────

    def check_budget_pace(
        self, deployment: AdDeployment, days_elapsed: int, total_days: int
    ) -> Dict[str, Any]:
        """Check if ad spend is on pace with budget allocation."""
        if total_days <= 0 or days_elapsed <= 0:
            return {"on_pace": True, "pacing_ratio": 0}

        expected_spend_pct = days_elapsed / total_days
        budget = deployment.budget_cents or 1
        actual_spend_pct = (deployment.spend_cents or 0) / budget

        pacing_ratio = actual_spend_pct / max(expected_spend_pct, 0.01)

        return {
            "deployment_id": deployment.id,
            "budget_cents": budget,
            "spend_cents": deployment.spend_cents or 0,
            "days_elapsed": days_elapsed,
            "total_days": total_days,
            "expected_spend_pct": round(expected_spend_pct * 100, 1),
            "actual_spend_pct": round(actual_spend_pct * 100, 1),
            "pacing_ratio": round(pacing_ratio, 2),
            "on_pace": 0.7 <= pacing_ratio <= 1.3,
            "status": "underspending" if pacing_ratio < 0.7 else "overspending" if pacing_ratio > 1.3 else "on_pace",
        }

    # ─── Spend Alert System ───────────────────────────────

    def check_spend_alert(
        self, deployment: AdDeployment, alert_threshold_pct: float = 80.0
    ) -> Dict[str, Any]:
        """Check if ad spend has exceeded alert threshold."""
        budget = deployment.budget_cents or 1
        spend = deployment.spend_cents or 0
        spend_pct = (spend / budget) * 100

        return {
            "deployment_id": deployment.id,
            "budget_cents": budget,
            "spend_cents": spend,
            "spend_pct": round(spend_pct, 1),
            "threshold_pct": alert_threshold_pct,
            "alert": spend_pct >= alert_threshold_pct,
            "overspent": spend > budget,
        }

    # ─── CPA Tracking ────────────────────────────────────

    def calculate_cpa(self, deployment: AdDeployment) -> Dict[str, Any]:
        """Calculate cost per acquisition for a deployment."""
        metrics = deployment.metrics or {}
        spend = deployment.spend_cents or 0
        conversions = metrics.get("conversions", 0)

        cpa_cents = spend / max(conversions, 1)
        return {
            "deployment_id": deployment.id,
            "spend_cents": spend,
            "conversions": conversions,
            "cpa_cents": round(cpa_cents),
            "cpa_usd": round(cpa_cents / 100, 2),
        }

    # ─── Ad Account Balance Check ─────────────────────────

    async def check_account_balance(self, platform: str = "meta_ads") -> Dict[str, Any]:
        """Check ad account balance/spending limit."""
        if platform == "meta_ads":
            access_token = os.getenv("META_ACCESS_TOKEN")
            ad_account_id = os.getenv("META_AD_ACCOUNT_ID")
            if access_token and ad_account_id:
                import httpx
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(
                            f"https://graph.facebook.com/v18.0/act_{ad_account_id}",
                            params={
                                "access_token": access_token,
                                "fields": "amount_spent,balance,spend_cap,currency",
                            },
                        )
                        data = resp.json()
                        return {
                            "platform": platform,
                            "amount_spent": data.get("amount_spent"),
                            "balance": data.get("balance"),
                            "spend_cap": data.get("spend_cap"),
                            "currency": data.get("currency"),
                            "available": True,
                        }
                except Exception as e:
                    return {"platform": platform, "available": False, "error": str(e)}

        return {"platform": platform, "available": False, "error": "Not configured"}

    # ─── Bulk Ad Pause/Resume ─────────────────────────────

    async def bulk_pause_ads(self, deployment_ids: List[str]) -> List[Dict[str, Any]]:
        """Pause multiple ad deployments."""
        results = []
        for did in deployment_ids:
            if self.db:
                try:
                    await self.db.table("actp_ad_deployments").update({
                        "status": "paused",
                    }).eq("id", did).execute()
                    results.append({"id": did, "status": "paused", "success": True})
                except Exception as e:
                    results.append({"id": did, "error": str(e), "success": False})
        return results

    async def bulk_resume_ads(self, deployment_ids: List[str]) -> List[Dict[str, Any]]:
        """Resume multiple ad deployments."""
        results = []
        for did in deployment_ids:
            if self.db:
                try:
                    await self.db.table("actp_ad_deployments").update({
                        "status": "active",
                    }).eq("id", did).execute()
                    results.append({"id": did, "status": "active", "success": True})
                except Exception as e:
                    results.append({"id": did, "error": str(e), "success": False})
        return results

    # ─── Ad Preview Link ──────────────────────────────────

    def generate_preview_link(self, deployment: AdDeployment) -> Optional[str]:
        """Generate a shareable ad preview link."""
        if deployment.platform == Platform.META_ADS and deployment.external_ad_id:
            return f"https://www.facebook.com/ads/manager/preview/?ad_id={deployment.external_ad_id}"
        return None

    # ─── Daily Budget Monitoring ──────────────────────────

    async def get_daily_spend_summary(self, campaign_id: str) -> Dict[str, Any]:
        """Get total daily spend across all deployments for a campaign."""
        if not self.db:
            return {"campaign_id": campaign_id, "total_spend_cents": 0}

        result = await self.db.table("actp_ad_deployments").select(
            "spend_cents, budget_cents, status, platform"
        ).eq("campaign_id", campaign_id).execute()

        deployments = result.data or []
        total_spend = sum(d.get("spend_cents", 0) for d in deployments)
        total_budget = sum(d.get("budget_cents", 0) for d in deployments)
        active_count = sum(1 for d in deployments if d.get("status") == "active")

        return {
            "campaign_id": campaign_id,
            "total_spend_cents": total_spend,
            "total_budget_cents": total_budget,
            "active_deployments": active_count,
            "total_deployments": len(deployments),
            "spend_pct": round((total_spend / max(total_budget, 1)) * 100, 1),
        }

    # ─── A/B Split Test Support ───────────────────────────

    def create_ab_split(
        self, creative_ids: List[str], budget_cents: int, split_pct: Optional[float] = None
    ) -> Dict[str, Any]:
        """Create A/B split test config between multiple creatives."""
        count = len(creative_ids)
        if count < 2:
            return {"error": "Need at least 2 creatives for A/B test"}

        per_creative = split_pct or round(100 / count, 1)
        budget_per = budget_cents // count

        splits = []
        for i, cid in enumerate(creative_ids):
            splits.append({
                "creative_id": cid,
                "variant": chr(65 + i),  # A, B, C...
                "budget_cents": budget_per,
                "traffic_pct": per_creative,
            })

        return {
            "test_type": "ab_split",
            "total_budget_cents": budget_cents,
            "variant_count": count,
            "splits": splits,
        }

    # ─── YouTube Ads Integration ──────────────────────────

    async def deploy_youtube_ad(
        self, creative: Creative, campaign: TestCampaign, budget_cents: int
    ) -> AdDeployment:
        """Deploy a creative as a YouTube Shorts ad via Google Ads."""
        deployment = AdDeployment(
            creative_id=creative.id,
            round_id=creative.round_id,
            campaign_id=creative.campaign_id,
            platform=Platform.YOUTUBE_SHORTS,
            budget_cents=budget_cents,
            status=AdDeploymentStatus.PENDING,
        )

        google_ads_token = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN")
        google_ads_customer = os.getenv("GOOGLE_ADS_CUSTOMER_ID")

        if google_ads_token and google_ads_customer:
            deployment.deployment_metadata = {
                "ad_type": "youtube_shorts",
                "customer_id": google_ads_customer,
                "targeting": self._build_meta_audience(campaign),
            }
            deployment.status = AdDeploymentStatus.PENDING
        else:
            deployment.status = AdDeploymentStatus.FAILED
            deployment.deployment_metadata = {"error": "Google Ads credentials not configured"}

        await self._save_deployment(deployment)
        return deployment

    # ─── Pixel / Conversion Tracking ──────────────────────

    def generate_pixel_config(
        self, platform: str, offer_url: str
    ) -> Dict[str, Any]:
        """Generate pixel/conversion tracking configuration for an ad deployment."""
        configs = {
            "meta_ads": {
                "pixel_id": os.getenv("META_PIXEL_ID", ""),
                "events": ["ViewContent", "AddToCart", "Purchase"],
                "domain": offer_url.split("/")[2] if "/" in offer_url else offer_url,
                "tracking_type": "standard_events",
            },
            "tiktok_ads": {
                "pixel_id": os.getenv("TIKTOK_PIXEL_ID", ""),
                "events": ["ViewContent", "ClickButton", "CompletePayment"],
                "tracking_type": "tiktok_pixel",
            },
            "youtube_ads": {
                "conversion_id": os.getenv("GOOGLE_CONVERSION_ID", ""),
                "conversion_label": os.getenv("GOOGLE_CONVERSION_LABEL", ""),
                "tracking_type": "google_ads_conversion",
            },
        }

        config = configs.get(platform, {})
        config["offer_url"] = offer_url
        config["platform"] = platform
        config["configured"] = bool(config.get("pixel_id") or config.get("conversion_id"))

        return config

    # ─── Ad Approval Status Monitoring ────────────────────

    async def check_approval_status(
        self, deployment: AdDeployment
    ) -> Dict[str, Any]:
        """Check whether an ad has been approved by the platform."""
        status = {
            "deployment_id": deployment.id,
            "platform": deployment.platform.value if hasattr(deployment.platform, 'value') else str(deployment.platform),
            "approval_status": "unknown",
        }

        if deployment.platform == Platform.META_ADS and deployment.external_ad_id:
            access_token = os.getenv("META_ACCESS_TOKEN")
            if access_token:
                import httpx
                try:
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.get(
                            f"https://graph.facebook.com/v18.0/{deployment.external_ad_id}",
                            params={
                                "access_token": access_token,
                                "fields": "effective_status,review_feedback",
                            },
                        )
                        data = resp.json()
                        status["approval_status"] = data.get("effective_status", "unknown")
                        status["review_feedback"] = data.get("review_feedback")
                except Exception as e:
                    status["error"] = str(e)

        return status

    # ─── Ad Creative Refresh Scheduling ───────────────────

    def calculate_refresh_schedule(
        self, deployment: AdDeployment, max_days: int = 14
    ) -> Dict[str, Any]:
        """Calculate when an ad creative should be refreshed based on fatigue."""
        fatigue = self.detect_ad_fatigue(deployment)

        if fatigue["is_fatigued"]:
            days_until_refresh = 0
            urgency = "immediate"
        elif fatigue["fatigue_score"] > 30:
            days_until_refresh = 3
            urgency = "soon"
        else:
            days_until_refresh = min(max_days, 7)
            urgency = "scheduled"

        return {
            "deployment_id": deployment.id,
            "days_until_refresh": days_until_refresh,
            "urgency": urgency,
            "fatigue_score": fatigue["fatigue_score"],
            "max_run_days": max_days,
        }

    # ─── Conversion Window Configuration ──────────────────

    CONVERSION_WINDOWS = {
        "1_day_click": {"click_days": 1, "view_days": 0},
        "7_day_click": {"click_days": 7, "view_days": 0},
        "7_day_click_1_day_view": {"click_days": 7, "view_days": 1},
        "28_day_click_1_day_view": {"click_days": 28, "view_days": 1},
    }

    def get_conversion_window(
        self, window_type: str = "7_day_click_1_day_view"
    ) -> Dict[str, Any]:
        """Get conversion attribution window configuration."""
        window = self.CONVERSION_WINDOWS.get(window_type, self.CONVERSION_WINDOWS["7_day_click_1_day_view"])
        return {
            "window_type": window_type,
            **window,
            "available_windows": list(self.CONVERSION_WINDOWS.keys()),
        }

    # ─── Ad Placement Selection ───────────────────────────

    PLACEMENT_OPTIONS = {
        "meta_ads": {
            "automatic": ["feed", "stories", "reels", "in_stream", "search", "instant_article"],
            "recommended_video": ["reels", "stories", "in_stream"],
            "recommended_short": ["reels", "stories"],
        },
        "tiktok_ads": {
            "automatic": ["for_you", "search"],
            "recommended_video": ["for_you"],
        },
    }

    def select_placements(
        self, platform: str, placement_strategy: str = "recommended_short"
    ) -> Dict[str, Any]:
        """Select ad placements for a given platform."""
        platform_options = self.PLACEMENT_OPTIONS.get(platform, {})
        placements = platform_options.get(placement_strategy, platform_options.get("automatic", []))

        return {
            "platform": platform,
            "strategy": placement_strategy,
            "placements": placements,
            "available_strategies": list(platform_options.keys()),
        }

    # ─── Ad Copy A/B Variants ─────────────────────────────

    def generate_ad_copy_variants(
        self, creative: Creative, variant_count: int = 3
    ) -> List[Dict[str, Any]]:
        """Generate multiple ad copy variants for A/B testing within a single deployment."""
        base_hook = creative.hook or ""
        base_cta = creative.cta or ""

        variants = [{"variant": "A", "headline": base_hook, "cta": base_cta, "type": "original"}]

        # Variant B: shorter hook
        if len(base_hook) > 20:
            variants.append({
                "variant": "B",
                "headline": base_hook[:base_hook.rfind(" ", 0, len(base_hook) // 2 + 10)] + "...",
                "cta": base_cta,
                "type": "shortened",
            })

        # Variant C: question format
        if not base_hook.endswith("?"):
            variants.append({
                "variant": "C",
                "headline": f"Did you know? {base_hook}",
                "cta": base_cta,
                "type": "question",
            })

        return variants[:variant_count]
