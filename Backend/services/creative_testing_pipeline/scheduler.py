"""
ACTP Pipeline Scheduler
========================
Background scheduler that auto-progresses rounds through the pipeline.
Checks wait times, triggers metric collection, winner selection, and next round creation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from .config import ACTPConfig
from .models import CampaignStatus, RoundStatus, RoundType, TestRound

logger = logging.getLogger(__name__)

# Default check interval (seconds)
DEFAULT_CHECK_INTERVAL = 300  # 5 minutes


class PipelineScheduler:
    """
    Background task that monitors active campaigns and auto-advances rounds.

    Workflow per active campaign:
    1. Find current round
    2. If WAITING and wait_until elapsed → trigger collect-metrics
    3. If COLLECTING complete → trigger select-winners
    4. If organic round COMPLETED → create ad round
    5. If ad round COMPLETED → create iteration round
    """

    def __init__(self, db_client=None, config: Optional[ACTPConfig] = None):
        self.db = db_client
        self.config = config or ACTPConfig()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        logger.info("[ACTP:Scheduler] Initialized")

    async def start(self, interval: int = DEFAULT_CHECK_INTERVAL):
        """Start the background scheduler loop."""
        if self._running:
            logger.warning("[ACTP:Scheduler] Already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop(interval))
        logger.info(f"[ACTP:Scheduler] Started (interval={interval}s)")

    async def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[ACTP:Scheduler] Stopped")

    async def _run_loop(self, interval: int):
        """Main scheduler loop."""
        while self._running:
            try:
                await self._check_all_campaigns()
            except Exception as e:
                logger.error(f"[ACTP:Scheduler] Check cycle error: {e}")

            await asyncio.sleep(interval)

    async def _check_all_campaigns(self):
        """Check all active campaigns for rounds that need advancement."""
        if not self.db:
            return

        # Fetch active campaigns
        result = await self.db.table("actp_campaigns").select("id, status").not_.in_(
            "status", ["draft", "completed", "failed", "paused"]
        ).execute()

        campaigns = result.data or []
        if not campaigns:
            return

        logger.debug(f"[ACTP:Scheduler] Checking {len(campaigns)} active campaigns")

        from .orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(db_client=self.db, config=self.config)

        for campaign_data in campaigns:
            campaign_id = campaign_data["id"]
            try:
                await self._check_campaign(campaign_id, orchestrator)
            except Exception as e:
                logger.error(f"[ACTP:Scheduler] Campaign {campaign_id} check error: {e}")

    async def _check_campaign(self, campaign_id: str, orchestrator):
        """Check a single campaign's rounds for needed actions."""
        rounds = await orchestrator._get_rounds(campaign_id)
        if not rounds:
            return

        current = orchestrator._get_current_round(rounds)
        if not current:
            return

        now = datetime.now(timezone.utc)

        # Handle WAITING rounds
        if current.status == RoundStatus.WAITING:
            if current.wait_until and now >= current.wait_until:
                logger.info(
                    f"[ACTP:Scheduler] Round {current.id} wait elapsed, advancing"
                )
                await orchestrator.advance_round(current.id)

                # After advancing from WAITING → COLLECTING, auto-collect
                updated = await orchestrator._get_round(current.id)
                if updated and updated.status == RoundStatus.COLLECTING:
                    await self._auto_collect_metrics(updated, orchestrator)

        # Handle COLLECTING → auto-advance to SELECTING
        elif current.status == RoundStatus.COLLECTING:
            await self._auto_collect_metrics(current, orchestrator)

        # Handle SELECTING → auto-select winners
        elif current.status == RoundStatus.SELECTING:
            await self._auto_select_winners(current, orchestrator)

        # Handle COMPLETED → create next round
        elif current.status == RoundStatus.COMPLETED:
            last_round = max(rounds, key=lambda r: r.round_number)
            if last_round.id == current.id:
                campaign = await orchestrator._get_campaign(campaign_id)
                config = ACTPConfig.from_dict(campaign.config) if campaign.config else self.config

                if last_round.round_number < config.iteration.max_rounds:
                    logger.info(
                        f"[ACTP:Scheduler] Creating next round for campaign {campaign_id}"
                    )
                    await orchestrator.create_next_round(campaign_id)

    async def _auto_collect_metrics(self, test_round: TestRound, orchestrator):
        """Auto-collect metrics for a round in COLLECTING status."""
        from .analytics_collector import AnalyticsCollector

        creatives = await orchestrator._get_creatives_for_round(test_round.id)
        posts = await orchestrator._get_organic_posts_for_round(test_round.id, creatives)

        if not posts:
            # No posts to collect, advance
            await orchestrator.advance_round(test_round.id)
            return

        analytics = AnalyticsCollector(db_client=self.db, config=self.config)
        logs = await analytics.collect_metrics(posts, test_round.id)

        logger.info(f"[ACTP:Scheduler] Collected {len(logs)} metrics for round {test_round.id}")

        # Advance to SELECTING
        await orchestrator.advance_round(test_round.id)

    async def _auto_select_winners(self, test_round: TestRound, orchestrator):
        """Auto-select winners for a round in SELECTING status."""
        from .winner_selector import WinnerSelector

        creatives = await orchestrator._get_creatives_for_round(test_round.id)
        selector = WinnerSelector(db_client=self.db, config=self.config)

        if test_round.round_type == RoundType.ORGANIC:
            posts = await orchestrator._get_organic_posts_for_round(
                test_round.id, creatives
            )
            winners = await selector.select_organic_winners(
                creatives, posts, test_round.id
            )
        else:
            ads = await orchestrator._get_ad_deployments_for_round(test_round.id)
            winners = await selector.select_ad_winners(
                creatives, ads, test_round.id
            )

        logger.info(
            f"[ACTP:Scheduler] Selected {len(winners)} winners for round {test_round.id}"
        )

        # Advance round
        await orchestrator.advance_round(test_round.id)

    # ─── Manual Triggers ──────────────────────────────────

    async def run_once(self):
        """Run a single check cycle (useful for testing/manual triggers)."""
        await self._check_all_campaigns()
