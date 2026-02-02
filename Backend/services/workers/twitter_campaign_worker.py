"""
Twitter Campaign Worker (ARCH-004, GAP-007)
=============================================
Event-driven worker for Twitter campaign scheduling with multi-account
switching and session health monitoring.

Subscribes to:
    - twitter.campaign.schedule_requested
    - twitter.campaign.post_requested
    - twitter.session.health_check

Emits:
    - twitter.campaign.scheduled
    - twitter.campaign.failed
    - twitter.campaign.posted
    - twitter.session.health_status
    - twitter.account.switched
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from enum import Enum

from services.event_bus import EventBus, Event, Topics
from services.workers.base import BaseWorker
from services.twitter_campaign_service import TwitterCampaignService

logger = logging.getLogger(__name__)


class SessionHealth(str, Enum):
    """Twitter session health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    RATE_LIMITED = "rate_limited"
    EXPIRED = "expired"


@dataclass
class TwitterAccount:
    """Twitter account configuration for multi-account switching (GAP-007)."""
    account_id: str
    username: str
    is_active: bool = True
    session_health: str = SessionHealth.HEALTHY
    tweets_posted_today: int = 0
    daily_limit: int = 50
    last_tweet_at: Optional[str] = None
    rate_limit_until: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @property
    def can_tweet(self) -> bool:
        """Check if account can post more tweets."""
        if not self.is_active:
            return False
        if self.session_health in (SessionHealth.UNHEALTHY, SessionHealth.EXPIRED):
            return False
        if self.session_health == SessionHealth.RATE_LIMITED:
            if self.rate_limit_until:
                now = datetime.now(timezone.utc).isoformat()
                if now < self.rate_limit_until:
                    return False
        return self.tweets_posted_today < self.daily_limit


class TwitterCampaignWorker(BaseWorker):
    """
    Worker for scheduling Twitter campaigns (ARCH-004, GAP-007).

    Handles:
        - Campaign scheduling requests from orchestrator
        - Tweet generation and scheduling
        - 2-hour interval management (12 tweets/day default)
        - Multi-account switching (GAP-007)
        - Session health monitoring (GAP-007)

    Usage:
        worker = TwitterCampaignWorker()
        await worker.start()

        # Request campaign scheduling via event
        await bus.publish("twitter.campaign.schedule_requested", {
            "pipeline_id": "...",
            "theme": "AI automation trends",
            "count": 12,
            "interval_minutes": 120,
            "offer_url": "https://..."
        })
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        worker_id: Optional[str] = None
    ):
        super().__init__(event_bus, worker_id)
        self.campaign_service = TwitterCampaignService(interval_minutes=120)

        # Multi-account support (GAP-007)
        self._accounts: Dict[str, TwitterAccount] = {}
        self._active_account_id: Optional[str] = None
        self._session_health: SessionHealth = SessionHealth.HEALTHY
        self._health_check_count: int = 0
        self._account_switch_count: int = 0

    def get_subscriptions(self) -> List[str]:
        """Subscribe to Twitter campaign events."""
        return [
            "twitter.campaign.schedule_requested",
            "twitter.campaign.post_requested",
            "twitter.session.health_check",
        ]

    async def handle_event(self, event: Event) -> None:
        """Handle Twitter campaign events."""
        if event.topic == "twitter.campaign.schedule_requested":
            await self._handle_schedule_request(event)
        elif event.topic == "twitter.campaign.post_requested":
            await self._handle_post_request(event)
        elif event.topic == "twitter.session.health_check":
            await self._handle_health_check(event)

    async def _handle_schedule_request(self, event: Event) -> None:
        """
        Handle campaign scheduling request (ARCH-004).

        Payload:
            - pipeline_id: Orchestrator pipeline ID
            - theme: Campaign theme
            - count: Number of tweets (default 12)
            - interval_minutes: Time between tweets (default 120 = 2 hours)
            - offer_url: Optional offer URL to include in tweets
        """
        payload = event.payload
        pipeline_id = payload.get("pipeline_id")
        theme = payload.get("theme")
        count = payload.get("count", 12)
        interval_minutes = payload.get("interval_minutes", 120)
        offer_url = payload.get("offer_url")

        if not theme:
            logger.error(f"[{self.worker_id}] Campaign request missing theme")
            await self.emit(
                "twitter.campaign.failed",
                {
                    "pipeline_id": pipeline_id,
                    "error": "Missing theme"
                },
                correlation_id=event.correlation_id
            )
            return

        logger.info(
            f"[{self.worker_id}] Scheduling campaign: "
            f"theme='{theme}', count={count}, interval={interval_minutes}min"
        )

        try:
            # Schedule campaign
            if offer_url:
                # Use offer-specific scheduling (REQ-TWITTER-002)
                tweet_ids = self.campaign_service.schedule_offer_tweets(
                    offer_url=offer_url,
                    offer_description=theme,
                    count=count,
                    interval_minutes=interval_minutes,
                    campaign_name=theme
                )
                campaign_id = f"offer_{theme}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}"
            else:
                # Use theme-based scheduling
                campaign_id = self.campaign_service.schedule_campaign(
                    theme=theme,
                    count=count,
                    interval_minutes=interval_minutes
                )
                tweet_ids = []  # schedule_campaign doesn't return IDs yet

            # Emit success event
            await self.emit(
                "twitter.campaign.scheduled",
                {
                    "pipeline_id": pipeline_id,
                    "campaign_id": campaign_id,
                    "theme": theme,
                    "tweets_scheduled": count,
                    "interval_minutes": interval_minutes,
                    "offer_url": offer_url
                },
                correlation_id=event.correlation_id
            )

            logger.success(
                f"[{self.worker_id}] Campaign scheduled: {count} tweets, "
                f"interval={interval_minutes}min"
            )

        except Exception as e:
            logger.error(f"[{self.worker_id}] Campaign scheduling failed: {e}")
            await self.emit(
                "twitter.campaign.failed",
                {
                    "pipeline_id": pipeline_id,
                    "theme": theme,
                    "error": str(e)
                },
                correlation_id=event.correlation_id
            )

    # ------------------------------------------------------------------
    # Multi-Account Management (GAP-007)
    # ------------------------------------------------------------------

    def register_account(self, account_id: str, username: str, daily_limit: int = 50) -> TwitterAccount:
        """
        Register a Twitter account for multi-account switching (GAP-007).

        Args:
            account_id: Unique account identifier
            username: Twitter handle
            daily_limit: Max tweets per day for this account

        Returns:
            TwitterAccount instance
        """
        account = TwitterAccount(
            account_id=account_id,
            username=username,
            daily_limit=daily_limit,
        )
        self._accounts[account_id] = account
        if self._active_account_id is None:
            self._active_account_id = account_id
        logger.info(f"[{self.worker_id}] Registered account: @{username} ({account_id})")
        return account

    def get_accounts(self) -> List[TwitterAccount]:
        """Get all registered accounts."""
        return list(self._accounts.values())

    def get_active_account(self) -> Optional[TwitterAccount]:
        """Get the currently active account."""
        if self._active_account_id:
            return self._accounts.get(self._active_account_id)
        return None

    async def switch_account(self, account_id: str) -> bool:
        """
        Switch to a different Twitter account (GAP-007).

        Emits twitter.account.switched event on success.

        Args:
            account_id: Account to switch to

        Returns:
            True if switch was successful
        """
        if account_id not in self._accounts:
            logger.error(f"[{self.worker_id}] Unknown account: {account_id}")
            return False

        account = self._accounts[account_id]
        if not account.is_active:
            logger.warning(f"[{self.worker_id}] Account {account_id} is inactive")
            return False

        prev_id = self._active_account_id
        self._active_account_id = account_id
        self._account_switch_count += 1

        await self.emit(
            "twitter.account.switched",
            {
                "previous_account_id": prev_id,
                "new_account_id": account_id,
                "username": account.username,
            }
        )

        logger.info(f"[{self.worker_id}] Switched to account @{account.username}")
        return True

    async def auto_switch_account(self) -> Optional[str]:
        """
        Automatically switch to the best available account (GAP-007).

        Selects account with fewest tweets today and healthy session.

        Returns:
            account_id of the switched account, or None if no accounts available
        """
        available = [
            a for a in self._accounts.values()
            if a.can_tweet and a.session_health in (SessionHealth.HEALTHY, SessionHealth.DEGRADED)
        ]

        if not available:
            logger.warning(f"[{self.worker_id}] No available accounts for auto-switch")
            return None

        # Pick account with fewest tweets posted today
        best = min(available, key=lambda a: a.tweets_posted_today)
        await self.switch_account(best.account_id)
        return best.account_id

    # ------------------------------------------------------------------
    # Session Health Monitoring (GAP-007)
    # ------------------------------------------------------------------

    def get_session_health(self) -> SessionHealth:
        """Get overall session health status."""
        return self._session_health

    def update_session_health(self, account_id: str, health: SessionHealth, rate_limit_until: Optional[str] = None) -> None:
        """Update health status for an account."""
        if account_id in self._accounts:
            self._accounts[account_id].session_health = health
            if rate_limit_until:
                self._accounts[account_id].rate_limit_until = rate_limit_until

        # Update overall health
        healths = [a.session_health for a in self._accounts.values() if a.is_active]
        if not healths:
            self._session_health = SessionHealth.HEALTHY
        elif all(h == SessionHealth.UNHEALTHY for h in healths):
            self._session_health = SessionHealth.UNHEALTHY
        elif any(h == SessionHealth.UNHEALTHY for h in healths):
            self._session_health = SessionHealth.DEGRADED
        elif any(h == SessionHealth.RATE_LIMITED for h in healths):
            self._session_health = SessionHealth.RATE_LIMITED
        else:
            self._session_health = SessionHealth.HEALTHY

    async def _handle_health_check(self, event: Event) -> None:
        """
        Handle session health check request (GAP-007).

        Performs health check on all registered accounts and emits status.
        """
        self._health_check_count += 1
        account_statuses = {}

        for aid, account in self._accounts.items():
            account_statuses[aid] = {
                "username": account.username,
                "is_active": account.is_active,
                "session_health": account.session_health,
                "tweets_posted_today": account.tweets_posted_today,
                "can_tweet": account.can_tweet,
            }

        await self.emit(
            "twitter.session.health_status",
            {
                "overall_health": self._session_health,
                "accounts": account_statuses,
                "active_account_id": self._active_account_id,
                "health_check_number": self._health_check_count,
            }
        )

    async def _handle_post_request(self, event: Event) -> None:
        """
        Handle individual tweet post request (GAP-007).

        Supports multi-account: auto-switches if current account is at limit.
        """
        payload = event.payload
        content = payload.get("content")
        account_id = payload.get("account_id", self._active_account_id)

        if not content:
            await self.emit("twitter.campaign.failed", {
                "error": "Missing tweet content",
                "pipeline_id": payload.get("pipeline_id"),
            })
            return

        # Auto-switch if current account can't tweet
        if account_id and account_id in self._accounts:
            account = self._accounts[account_id]
            if not account.can_tweet:
                switched_id = await self.auto_switch_account()
                if switched_id:
                    account_id = switched_id
                else:
                    await self.emit("twitter.campaign.failed", {
                        "error": "No available accounts",
                        "pipeline_id": payload.get("pipeline_id"),
                    })
                    return

        # Record the tweet
        if account_id and account_id in self._accounts:
            self._accounts[account_id].tweets_posted_today += 1
            self._accounts[account_id].last_tweet_at = datetime.now(timezone.utc).isoformat()

        await self.emit(
            "twitter.campaign.posted",
            {
                "pipeline_id": payload.get("pipeline_id"),
                "account_id": account_id,
                "content": content[:100],
                "posted_at": datetime.now(timezone.utc).isoformat(),
            },
            correlation_id=event.correlation_id,
        )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get worker statistics including multi-account info."""
        stats = super().get_stats()
        stats.update({
            "campaigns_scheduled": self._events_processed,
            "campaigns_failed": self._events_failed,
            "session_health": self._session_health,
            "registered_accounts": len(self._accounts),
            "active_account_id": self._active_account_id,
            "account_switch_count": self._account_switch_count,
            "health_check_count": self._health_check_count,
        })
        return stats


# Singleton instance
_worker: Optional[TwitterCampaignWorker] = None

def get_twitter_campaign_worker(event_bus: Optional[EventBus] = None) -> TwitterCampaignWorker:
    """Get singleton TwitterCampaignWorker instance."""
    global _worker
    if _worker is None:
        _worker = TwitterCampaignWorker(event_bus)
    return _worker
