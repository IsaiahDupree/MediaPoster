"""
ACTP Pipeline Orchestrator
===========================
Central controller managing the full test campaign lifecycle.
Handles state transitions across rounds: generate → publish → measure → select → iterate.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .config import ACTPConfig
from .models import (
    AdDeployment,
    CampaignStatus,
    Creative,
    CreateCampaignRequest,
    OrganicPost,
    RoundStatus,
    RoundType,
    TestCampaign,
    TestRound,
    WinnerSelection,
)

logger = logging.getLogger(__name__)


# Valid state transitions for campaigns
CAMPAIGN_TRANSITIONS = {
    CampaignStatus.DRAFT: [CampaignStatus.GENERATING, CampaignStatus.FAILED],
    CampaignStatus.GENERATING: [CampaignStatus.ORGANIC_TESTING, CampaignStatus.FAILED, CampaignStatus.PAUSED],
    CampaignStatus.ORGANIC_TESTING: [CampaignStatus.AD_TESTING, CampaignStatus.ITERATING, CampaignStatus.FAILED, CampaignStatus.PAUSED],
    CampaignStatus.AD_TESTING: [CampaignStatus.ITERATING, CampaignStatus.SCALING, CampaignStatus.FAILED, CampaignStatus.PAUSED],
    CampaignStatus.ITERATING: [CampaignStatus.GENERATING, CampaignStatus.COMPLETED, CampaignStatus.FAILED, CampaignStatus.PAUSED],
    CampaignStatus.SCALING: [CampaignStatus.ITERATING, CampaignStatus.COMPLETED, CampaignStatus.FAILED, CampaignStatus.PAUSED],
    CampaignStatus.PAUSED: [CampaignStatus.GENERATING, CampaignStatus.ORGANIC_TESTING, CampaignStatus.AD_TESTING, CampaignStatus.ITERATING],
    CampaignStatus.COMPLETED: [],
    CampaignStatus.FAILED: [CampaignStatus.DRAFT],
}

# Valid state transitions for rounds
ROUND_TRANSITIONS = {
    RoundStatus.PENDING: [RoundStatus.GENERATING, RoundStatus.FAILED],
    RoundStatus.GENERATING: [RoundStatus.PUBLISHING, RoundStatus.FAILED],
    RoundStatus.PUBLISHING: [RoundStatus.WAITING, RoundStatus.FAILED],
    RoundStatus.WAITING: [RoundStatus.COLLECTING, RoundStatus.FAILED],
    RoundStatus.COLLECTING: [RoundStatus.SELECTING, RoundStatus.WAITING, RoundStatus.FAILED],
    RoundStatus.SELECTING: [RoundStatus.DEPLOYING, RoundStatus.COMPLETED, RoundStatus.FAILED],
    RoundStatus.DEPLOYING: [RoundStatus.WAITING, RoundStatus.COMPLETED, RoundStatus.FAILED],
    RoundStatus.COMPLETED: [],
    RoundStatus.FAILED: [RoundStatus.PENDING],
}


class PipelineOrchestrator:
    """
    Manages the ACTP campaign lifecycle.

    Coordinates between:
    - Creative Engine (video generation)
    - Organic Publisher (YouTube/TikTok posting)
    - Analytics Collector (metric gathering)
    - Winner Selector (scoring and ranking)
    - Ad Deployer (budget allocation)
    - Iteration Engine (variation generation)
    """

    def __init__(self, db_client=None, config: Optional[ACTPConfig] = None):
        self.db = db_client
        self.config = config or ACTPConfig()
        logger.info("[ACTP] Pipeline Orchestrator initialized")

    # ─── Campaign Management ──────────────────────────────

    async def create_campaign(self, request: CreateCampaignRequest) -> TestCampaign:
        """Create a new test campaign and its first organic round."""
        config = self.config
        if request.config:
            config = ACTPConfig.from_dict(request.config)

        campaign = TestCampaign(
            name=request.name,
            offer_id=request.offer_id,
            offer_name=request.offer_name,
            offer_url=request.offer_url,
            angles=request.angles,
            target_audience=request.target_audience,
            mode=request.mode,
            config=config.to_dict(),
        )

        # Persist campaign
        await self._save_campaign(campaign)

        # Create first round (organic test)
        round_1 = TestRound(
            campaign_id=campaign.id,
            round_number=1,
            round_type=RoundType.ORGANIC,
            config={"platforms": config.organic_test.platforms},
        )
        await self._save_round(round_1)

        campaign.total_rounds = 1
        await self._save_campaign(campaign)

        logger.info(f"[ACTP] Created campaign '{campaign.name}' ({campaign.id}) with round 1")
        return campaign

    async def start_campaign(self, campaign_id: str) -> TestCampaign:
        """Start a campaign — triggers creative generation for round 1."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        self._validate_transition(campaign.status, CampaignStatus.GENERATING)
        campaign.status = CampaignStatus.GENERATING
        campaign.updated_at = datetime.now(timezone.utc)
        await self._save_campaign(campaign)

        # Start round 1 generation
        rounds = await self._get_rounds(campaign_id)
        if rounds:
            round_1 = rounds[0]
            round_1.status = RoundStatus.GENERATING
            round_1.started_at = datetime.now(timezone.utc)
            await self._save_round(round_1)

        logger.info(f"[ACTP] Started campaign {campaign_id}")
        return campaign

    async def pause_campaign(self, campaign_id: str) -> TestCampaign:
        """Pause a running campaign."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        self._validate_transition(campaign.status, CampaignStatus.PAUSED)
        campaign.status = CampaignStatus.PAUSED
        campaign.updated_at = datetime.now(timezone.utc)
        await self._save_campaign(campaign)

        logger.info(f"[ACTP] Paused campaign {campaign_id}")
        return campaign

    async def resume_campaign(self, campaign_id: str) -> TestCampaign:
        """Resume a paused campaign."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        if campaign.status != CampaignStatus.PAUSED:
            raise ValueError(f"Campaign is not paused: {campaign.status}")

        # Determine what status to resume to based on current round
        rounds = await self._get_rounds(campaign_id)
        current_round = self._get_current_round(rounds)

        if current_round:
            if current_round.round_type == RoundType.ORGANIC:
                campaign.status = CampaignStatus.ORGANIC_TESTING
            elif current_round.round_type == RoundType.AD:
                campaign.status = CampaignStatus.AD_TESTING
            else:
                campaign.status = CampaignStatus.SCALING
        else:
            campaign.status = CampaignStatus.GENERATING

        campaign.updated_at = datetime.now(timezone.utc)
        await self._save_campaign(campaign)

        logger.info(f"[ACTP] Resumed campaign {campaign_id} → {campaign.status}")
        return campaign

    # ─── Round Management ─────────────────────────────────

    async def advance_round(self, round_id: str) -> TestRound:
        """
        Advance a round to its next state.
        Called by the scheduler or manually.
        """
        test_round = await self._get_round(round_id)
        if not test_round:
            raise ValueError(f"Round not found: {round_id}")

        campaign = await self._get_campaign(test_round.campaign_id)
        config = ACTPConfig.from_dict(campaign.config) if campaign.config else self.config

        current = test_round.status
        next_status = self._determine_next_round_status(test_round, config)

        if next_status:
            self._validate_round_transition(current, next_status)
            test_round.status = next_status

            # Set wait_until for waiting states
            if next_status == RoundStatus.WAITING:
                wait_hours = (
                    config.organic_test.wait_hours
                    if test_round.round_type == RoundType.ORGANIC
                    else config.ad_test.wait_hours
                )
                test_round.wait_until = datetime.now(timezone.utc) + timedelta(hours=wait_hours)

            if next_status == RoundStatus.COMPLETED:
                test_round.completed_at = datetime.now(timezone.utc)

            await self._save_round(test_round)
            logger.info(f"[ACTP] Round {round_id}: {current} → {next_status}")

        return test_round

    async def create_next_round(self, campaign_id: str) -> TestRound:
        """Create the next round for a campaign based on previous results."""
        campaign = await self._get_campaign(campaign_id)
        rounds = await self._get_rounds(campaign_id)
        config = ACTPConfig.from_dict(campaign.config) if campaign.config else self.config

        last_round = max(rounds, key=lambda r: r.round_number) if rounds else None
        next_number = (last_round.round_number + 1) if last_round else 1

        # Determine round type
        if not last_round or last_round.round_type == RoundType.ORGANIC:
            # After organic → ad test
            round_type = RoundType.AD
            budget = config.ad_test.budget_per_creative_cents
        elif last_round.round_type == RoundType.AD:
            # After ad → iterate with new organic
            round_type = RoundType.ORGANIC
            budget = 0
        else:
            # Scaling round
            round_type = RoundType.SCALE
            tier_idx = min(next_number // 2, len(config.scaling.budget_tiers_cents) - 1)
            budget = config.scaling.budget_tiers_cents[tier_idx]

        # Check max rounds
        if next_number > config.iteration.max_rounds:
            campaign.status = CampaignStatus.COMPLETED
            campaign.completed_at = datetime.now(timezone.utc)
            await self._save_campaign(campaign)
            logger.info(f"[ACTP] Campaign {campaign_id} completed (max rounds reached)")
            return last_round

        new_round = TestRound(
            campaign_id=campaign_id,
            round_number=next_number,
            round_type=round_type,
            budget_per_creative_cents=budget,
        )
        await self._save_round(new_round)

        campaign.total_rounds = next_number
        campaign.updated_at = datetime.now(timezone.utc)
        await self._save_campaign(campaign)

        logger.info(f"[ACTP] Created round {next_number} ({round_type}) for campaign {campaign_id}")
        return new_round

    # ─── Status & Queries ─────────────────────────────────

    async def get_campaign_detail(self, campaign_id: str) -> Dict[str, Any]:
        """Get full campaign detail with rounds, creatives, and metrics."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return None

        rounds = await self._get_rounds(campaign_id)
        round_details = []

        for r in sorted(rounds, key=lambda x: x.round_number):
            creatives = await self._get_creatives_for_round(r.id)
            winners = await self._get_winners_for_round(r.id)
            organic_posts = await self._get_organic_posts_for_round(r.id, creatives)
            ad_deployments = await self._get_ad_deployments_for_round(r.id)

            round_details.append({
                "round": r,
                "creatives": creatives,
                "winners": winners,
                "organic_posts": organic_posts,
                "ad_deployments": ad_deployments,
            })

        return {
            "campaign": campaign,
            "rounds": round_details,
        }

    async def list_campaigns(self, status: Optional[str] = None) -> List[TestCampaign]:
        """List all campaigns, optionally filtered by status."""
        return await self._list_campaigns(status)

    # ─── State Machine Helpers ────────────────────────────

    def _validate_transition(self, current: CampaignStatus, target: CampaignStatus):
        """Validate a campaign state transition."""
        allowed = CAMPAIGN_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise ValueError(
                f"Invalid campaign transition: {current} → {target}. "
                f"Allowed: {allowed}"
            )

    def _validate_round_transition(self, current: RoundStatus, target: RoundStatus):
        """Validate a round state transition."""
        allowed = ROUND_TRANSITIONS.get(current, [])
        if target not in allowed:
            raise ValueError(
                f"Invalid round transition: {current} → {target}. "
                f"Allowed: {allowed}"
            )

    def _determine_next_round_status(
        self, test_round: TestRound, config: ACTPConfig
    ) -> Optional[RoundStatus]:
        """Determine what the next status should be for a round."""
        current = test_round.status

        if current == RoundStatus.GENERATING:
            return RoundStatus.PUBLISHING

        if current == RoundStatus.PUBLISHING:
            return RoundStatus.WAITING

        if current == RoundStatus.WAITING:
            # Check if wait time has elapsed
            if test_round.wait_until and datetime.now(timezone.utc) >= test_round.wait_until:
                return RoundStatus.COLLECTING
            return None  # Still waiting

        if current == RoundStatus.COLLECTING:
            return RoundStatus.SELECTING

        if current == RoundStatus.SELECTING:
            if test_round.round_type == RoundType.ORGANIC:
                return RoundStatus.COMPLETED  # Organic round done, next round deploys ads
            return RoundStatus.DEPLOYING

        if current == RoundStatus.DEPLOYING:
            return RoundStatus.WAITING  # Wait for ad results

        return None

    def _get_current_round(self, rounds: List[TestRound]) -> Optional[TestRound]:
        """Get the current (non-completed) round."""
        for r in sorted(rounds, key=lambda x: x.round_number, reverse=True):
            if r.status != RoundStatus.COMPLETED:
                return r
        return None

    # ─── Database Operations (to be connected to Supabase) ─

    async def _save_campaign(self, campaign: TestCampaign):
        """Persist campaign to database."""
        if self.db:
            await self.db.table("actp_campaigns").upsert(
                campaign.model_dump(mode="json")
            ).execute()
        logger.debug(f"[ACTP] Saved campaign {campaign.id}")

    async def _get_campaign(self, campaign_id: str) -> Optional[TestCampaign]:
        """Load campaign from database."""
        if self.db:
            result = await self.db.table("actp_campaigns").select("*").eq("id", campaign_id).single().execute()
            if result.data:
                return TestCampaign(**result.data)
        return None

    async def _list_campaigns(self, status: Optional[str] = None) -> List[TestCampaign]:
        """List campaigns from database."""
        if self.db:
            query = self.db.table("actp_campaigns").select("*").order("created_at", desc=True)
            if status:
                query = query.eq("status", status)
            result = await query.execute()
            return [TestCampaign(**row) for row in (result.data or [])]
        return []

    async def _save_round(self, test_round: TestRound):
        """Persist round to database."""
        if self.db:
            await self.db.table("actp_rounds").upsert(
                test_round.model_dump(mode="json")
            ).execute()
        logger.debug(f"[ACTP] Saved round {test_round.id}")

    async def _get_round(self, round_id: str) -> Optional[TestRound]:
        """Load round from database."""
        if self.db:
            result = await self.db.table("actp_rounds").select("*").eq("id", round_id).single().execute()
            if result.data:
                return TestRound(**result.data)
        return None

    async def _get_rounds(self, campaign_id: str) -> List[TestRound]:
        """Load all rounds for a campaign."""
        if self.db:
            result = await self.db.table("actp_rounds").select("*").eq("campaign_id", campaign_id).order("round_number").execute()
            return [TestRound(**row) for row in (result.data or [])]
        return []

    async def _get_creatives_for_round(self, round_id: str) -> List[Creative]:
        """Load creatives for a round."""
        if self.db:
            result = await self.db.table("actp_creatives").select("*").eq("round_id", round_id).execute()
            return [Creative(**row) for row in (result.data or [])]
        return []

    async def _get_winners_for_round(self, round_id: str) -> List[WinnerSelection]:
        """Load winner selections for a round."""
        if self.db:
            result = await self.db.table("actp_winner_selections").select("*").eq("round_id", round_id).order("rank").execute()
            return [WinnerSelection(**row) for row in (result.data or [])]
        return []

    async def _get_organic_posts_for_round(
        self, round_id: str, creatives: List[Creative]
    ) -> List[OrganicPost]:
        """Load organic posts for creatives in a round."""
        if self.db and creatives:
            creative_ids = [c.id for c in creatives]
            result = await self.db.table("actp_organic_posts").select("*").in_("creative_id", creative_ids).execute()
            return [OrganicPost(**row) for row in (result.data or [])]
        return []

    async def _get_ad_deployments_for_round(self, round_id: str) -> List[AdDeployment]:
        """Load ad deployments for a round."""
        if self.db:
            result = await self.db.table("actp_ad_deployments").select("*").eq("round_id", round_id).execute()
            return [AdDeployment(**row) for row in (result.data or [])]
        return []

    # ─── Campaign Cloning ─────────────────────────────────

    async def clone_campaign(
        self, campaign_id: str, new_name: Optional[str] = None
    ) -> TestCampaign:
        """Clone an existing campaign with its config, angles, and audience."""
        source = await self._get_campaign(campaign_id)
        if not source:
            raise ValueError(f"Campaign not found: {campaign_id}")

        clone = TestCampaign(
            name=new_name or f"{source.name} (Clone)",
            offer_id=source.offer_id,
            offer_name=source.offer_name,
            offer_url=source.offer_url,
            angles=source.angles,
            target_audience=source.target_audience,
            mode=source.mode,
            config=source.config,
            tags=source.tags if hasattr(source, "tags") else [],
        )
        await self._save_campaign(clone)

        round_1 = TestRound(
            campaign_id=clone.id,
            round_number=1,
            round_type=RoundType.ORGANIC,
            config=source.config,
        )
        await self._save_round(round_1)
        clone.total_rounds = 1
        await self._save_campaign(clone)

        await self._audit_log("campaign", clone.id, "cloned", {"source_id": campaign_id})
        logger.info(f"[ACTP] Cloned campaign {campaign_id} → {clone.id}")
        return clone

    # ─── Campaign Archival ────────────────────────────────

    async def archive_campaign(self, campaign_id: str) -> TestCampaign:
        """Soft-delete a completed campaign."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        if self.db:
            await self.db.table("actp_campaigns").update({
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            }).eq("id", campaign_id).execute()

        await self._audit_log("campaign", campaign_id, "archived")
        logger.info(f"[ACTP] Archived campaign {campaign_id}")
        return campaign

    async def restore_campaign(self, campaign_id: str) -> TestCampaign:
        """Restore an archived campaign."""
        if self.db:
            await self.db.table("actp_campaigns").update({
                "deleted_at": None,
            }).eq("id", campaign_id).execute()

        await self._audit_log("campaign", campaign_id, "restored")
        campaign = await self._get_campaign(campaign_id)
        return campaign

    # ─── Campaign Tags ────────────────────────────────────

    async def add_tags(self, campaign_id: str, tags: List[str]) -> TestCampaign:
        """Add tags to a campaign."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        existing = campaign.tags if hasattr(campaign, "tags") and campaign.tags else []
        updated = list(set(existing + tags))

        if self.db:
            await self.db.table("actp_campaigns").update(
                {"tags": updated}
            ).eq("id", campaign_id).execute()

        return await self._get_campaign(campaign_id)

    async def remove_tags(self, campaign_id: str, tags: List[str]) -> TestCampaign:
        """Remove tags from a campaign."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        existing = campaign.tags if hasattr(campaign, "tags") and campaign.tags else []
        updated = [t for t in existing if t not in tags]

        if self.db:
            await self.db.table("actp_campaigns").update(
                {"tags": updated}
            ).eq("id", campaign_id).execute()

        return await self._get_campaign(campaign_id)

    # ─── Campaign Templates ───────────────────────────────

    async def save_as_template(
        self, campaign_id: str, template_name: str, description: str = ""
    ) -> Dict[str, Any]:
        """Save a campaign's config as a reusable template."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        template = {
            "id": str(uuid4()),
            "name": template_name,
            "description": description,
            "config": campaign.config,
            "angles": campaign.angles,
            "target_audience": campaign.target_audience,
            "mode": campaign.mode,
            "tags": campaign.tags if hasattr(campaign, "tags") else [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if self.db:
            await self.db.table("actp_campaign_templates").insert(template).execute()

        logger.info(f"[ACTP] Saved template '{template_name}' from campaign {campaign_id}")
        return template

    async def create_from_template(
        self, template_id: str, name: str, offer_id: Optional[str] = None
    ) -> TestCampaign:
        """Create a campaign from a saved template."""
        if not self.db:
            raise RuntimeError("Database required for template operations")

        result = await self.db.table("actp_campaign_templates").select("*").eq(
            "id", template_id
        ).single().execute()
        if not result.data:
            raise ValueError(f"Template not found: {template_id}")

        tmpl = result.data
        request = CreateCampaignRequest(
            name=name,
            offer_id=offer_id,
            angles=tmpl.get("angles", []),
            target_audience=tmpl.get("target_audience"),
            mode=tmpl.get("mode", "offer"),
            config=tmpl.get("config"),
        )
        return await self.create_campaign(request)

    async def list_templates(self) -> List[Dict[str, Any]]:
        """List all campaign templates."""
        if self.db:
            result = await self.db.table("actp_campaign_templates").select("*").order(
                "created_at", desc=True
            ).execute()
            return result.data or []
        return []

    # ─── Dry-Run Mode ─────────────────────────────────────

    async def start_dry_run(self, campaign_id: str) -> TestCampaign:
        """Start a campaign in dry-run mode (generate + score, no publish/spend)."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign not found: {campaign_id}")

        config = campaign.config or {}
        config["dry_run"] = True
        campaign.config = config

        self._validate_transition(campaign.status, CampaignStatus.GENERATING)
        campaign.status = CampaignStatus.GENERATING
        campaign.updated_at = datetime.now(timezone.utc)
        await self._save_campaign(campaign)

        await self._audit_log("campaign", campaign_id, "dry_run_started")
        logger.info(f"[ACTP] Dry-run started for campaign {campaign_id}")
        return campaign

    def is_dry_run(self, campaign: TestCampaign) -> bool:
        """Check if a campaign is in dry-run mode."""
        return bool((campaign.config or {}).get("dry_run"))

    # ─── Campaign Progress ────────────────────────────────

    async def get_progress(self, campaign_id: str) -> Dict[str, Any]:
        """Calculate campaign progress percentage and duration."""
        campaign = await self._get_campaign(campaign_id)
        if not campaign:
            return {"progress_pct": 0, "duration_hours": 0}

        config = ACTPConfig.from_dict(campaign.config) if campaign.config else self.config
        rounds = await self._get_rounds(campaign_id)
        completed = sum(1 for r in rounds if r.status == RoundStatus.COMPLETED)
        max_rounds = config.iteration.max_rounds

        progress_pct = round((completed / max(max_rounds, 1)) * 100, 1)

        duration_hours = 0.0
        if campaign.created_at:
            end = campaign.completed_at or datetime.now(timezone.utc)
            delta = end - campaign.created_at
            duration_hours = round(delta.total_seconds() / 3600, 2)

        return {
            "campaign_id": campaign_id,
            "progress_pct": progress_pct,
            "rounds_completed": completed,
            "rounds_total": len(rounds),
            "max_rounds": max_rounds,
            "duration_hours": duration_hours,
            "status": campaign.status.value if hasattr(campaign.status, "value") else str(campaign.status),
        }

    # ─── Round Retry ──────────────────────────────────────

    async def retry_round(self, round_id: str) -> TestRound:
        """Retry a failed round from PENDING state."""
        test_round = await self._get_round(round_id)
        if not test_round:
            raise ValueError(f"Round not found: {round_id}")

        if test_round.status != RoundStatus.FAILED:
            raise ValueError(f"Can only retry failed rounds, current: {test_round.status}")

        self._validate_round_transition(RoundStatus.FAILED, RoundStatus.PENDING)
        test_round.status = RoundStatus.PENDING
        test_round.started_at = None
        test_round.completed_at = None
        await self._save_round(test_round)

        await self._audit_log("round", round_id, "retried")
        logger.info(f"[ACTP] Retried round {round_id}")
        return test_round

    # ─── Concurrent Campaign Limit ────────────────────────

    async def check_concurrent_limit(self, max_active: int = 5) -> bool:
        """Check if we're within the concurrent campaign limit."""
        if not self.db:
            return True

        result = await self.db.table("actp_campaigns").select("id").not_.in_(
            "status", ["draft", "completed", "failed", "paused"]
        ).is_("deleted_at", "null").execute()

        active_count = len(result.data or [])
        return active_count < max_active

    # ─── Bulk Operations ──────────────────────────────────

    async def bulk_pause(self, campaign_ids: List[str]) -> List[Dict[str, Any]]:
        """Pause multiple campaigns."""
        results = []
        for cid in campaign_ids:
            try:
                campaign = await self.pause_campaign(cid)
                results.append({"id": cid, "status": "paused", "success": True})
            except Exception as e:
                results.append({"id": cid, "error": str(e), "success": False})
        return results

    async def bulk_resume(self, campaign_ids: List[str]) -> List[Dict[str, Any]]:
        """Resume multiple campaigns."""
        results = []
        for cid in campaign_ids:
            try:
                campaign = await self.resume_campaign(cid)
                results.append({"id": cid, "status": str(campaign.status), "success": True})
            except Exception as e:
                results.append({"id": cid, "error": str(e), "success": False})
        return results

    async def bulk_archive(self, campaign_ids: List[str]) -> List[Dict[str, Any]]:
        """Archive multiple campaigns."""
        results = []
        for cid in campaign_ids:
            try:
                await self.archive_campaign(cid)
                results.append({"id": cid, "status": "archived", "success": True})
            except Exception as e:
                results.append({"id": cid, "error": str(e), "success": False})
        return results

    # ─── Audit Logging ────────────────────────────────────

    async def _audit_log(
        self,
        entity_type: str,
        entity_id: str,
        action: str,
        data: Optional[Dict[str, Any]] = None,
        actor: str = "system",
    ):
        """Write an audit log entry."""
        if self.db:
            await self.db.table("actp_audit_log").insert({
                "entity_type": entity_type,
                "entity_id": entity_id,
                "action": action,
                "new_value": data,
                "actor": actor,
            }).execute()

    async def get_audit_history(
        self, entity_type: str, entity_id: str
    ) -> List[Dict[str, Any]]:
        """Get audit history for an entity."""
        if self.db:
            result = await self.db.table("actp_audit_log").select("*").eq(
                "entity_type", entity_type
            ).eq("entity_id", entity_id).order("created_at", desc=True).execute()
            return result.data or []
        return []
