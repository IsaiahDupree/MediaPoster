"""
Tweet Scheduler Service (ARCH-004)
==================================
Schedules tweets at 2-hour intervals for content promotion and traffic driving.

Features:
- Schedule tweets every 2 hours for X tweets per day
- Track tweet IDs and status
- Auto-include offer URLs with tracking parameters
- Integrate with Twitter Campaign Service
- Support pause/resume of campaigns

Usage:
    scheduler = TweetScheduler()
    result = await scheduler.schedule_tweet_campaign(
        theme="AI automation revolution",
        tweets_per_day=12,
        offer_url="https://example.com/offer",
        duration_days=7
    )
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

from services.event_bus import EventBus, Topics

logger = logging.getLogger(__name__)


class TweetStatus(Enum):
    """Tweet scheduling status."""
    SCHEDULED = "scheduled"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TweetScheduler:
    """
    Tweet Scheduler Service (ARCH-004)

    Schedules tweets at regular intervals for content promotion.
    Integrates with Twitter Campaign Service for actual posting.
    """

    _instance: Optional['TweetScheduler'] = None

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus.get_instance()
        self._scheduled_tweets: Dict[str, List[Dict[str, Any]]] = {}
        self._active_campaigns: Dict[str, Dict[str, Any]] = {}
        self._twitter_service = None

        # Try to load Twitter service
        try:
            from services.twitter_campaign_service import TwitterCampaignService
            self._twitter_service = TwitterCampaignService()
            logger.info("✅ Twitter Campaign Service loaded")
        except Exception as e:
            logger.warning(f"⚠️ Twitter Campaign Service initialization failed: {e}")

        # Subscribe to events
        self._setup_subscriptions()
        logger.info("🗣️ Tweet Scheduler initialized")

    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> 'TweetScheduler':
        """Get or create singleton instance."""
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance

    def _setup_subscriptions(self) -> None:
        """Subscribe to relevant events."""
        self.event_bus.subscribe(
            "twitter.tweet.sent",
            self._handle_tweet_sent
        )
        self.event_bus.subscribe(
            "twitter.tweet.failed",
            self._handle_tweet_failed
        )
        logger.debug("📫 Tweet Scheduler subscribed to Twitter events")

    async def schedule_tweet_campaign(
        self,
        pipeline_id: str,
        theme: str,
        tweets_per_day: int = 12,
        offer_url: Optional[str] = None,
        duration_days: int = 1,
        base_message: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        start_delay_minutes: int = 0
    ) -> Dict[str, Any]:
        """Reject legacy in-memory scheduling; Airtime owns scheduling."""
        raise RuntimeError("airtime_required: legacy in-memory Twitter scheduling is disabled; use Airtime.")

    async def _schedule_tweet_event(self, tweet: Dict[str, Any]) -> None:
        """
        Schedule a tweet by creating a task that will post at the scheduled time.

        Uses async task scheduling to delay tweet posting until scheduled_at time.
        """
        raise RuntimeError("airtime_required: legacy in-memory Twitter scheduling is disabled; use Airtime.")

    async def _post_tweet_delayed(self, tweet: Dict[str, Any], delay_seconds: float) -> None:
        """Post a tweet after a delay."""
        raise RuntimeError("airtime_required: legacy delayed Twitter publishing is disabled; use Airtime.")

    async def _post_tweet(self, tweet: Dict[str, Any]) -> None:
        """
        Post a single tweet via Twitter service.

        Constructs tweet text from theme/message/hashtags and posts it.
        """
        raise RuntimeError("airtime_required: legacy direct Twitter publishing is disabled; use Airtime.")

    def _build_tweet_text(self, tweet: Dict[str, Any]) -> str:
        """
        Build tweet text from template + theme + offer URL.

        Constructs engaging tweet that includes:
        - Theme/hook
        - Call to action
        - Offer URL (with tracking if available)
        - Hashtags
        """
        raise RuntimeError("script_hub_required: legacy Twitter copy assembly is disabled; use ScriptHub.")

    async def _handle_tweet_sent(self, event) -> None:
        """Handle tweet sent event."""
        payload = event.payload
        campaign_id = payload.get("campaign_id")

        if campaign_id and campaign_id in self._active_campaigns:
            campaign = self._active_campaigns[campaign_id]
            logger.debug(f"[{campaign_id}] Tweet sent event received")

    async def _handle_tweet_failed(self, event) -> None:
        """Handle tweet failed event."""
        payload = event.payload
        campaign_id = payload.get("campaign_id")
        error = payload.get("error", "Unknown error")

        if campaign_id and campaign_id in self._active_campaigns:
            logger.warning(f"[{campaign_id}] Tweet failed: {error}")

    def get_campaign_status(self, campaign_id: str) -> Dict[str, Any]:
        """
        Get status of a tweet campaign.

        Returns:
            Campaign dict with status, scheduled tweets, and metrics
        """
        if campaign_id not in self._active_campaigns:
            return {"error": "Campaign not found"}

        campaign = self._active_campaigns[campaign_id]
        tweets = self._scheduled_tweets.get(campaign_id, [])

        # Count by status
        sent_count = sum(1 for t in tweets if t.get("status") == TweetStatus.SENT.value)
        failed_count = sum(1 for t in tweets if t.get("status") == TweetStatus.FAILED.value)
        scheduled_count = sum(1 for t in tweets if t.get("status") == TweetStatus.SCHEDULED.value)

        return {
            "campaign_id": campaign_id,
            "pipeline_id": campaign.get("pipeline_id"),
            "status": campaign.get("status"),
            "total_tweets": campaign.get("total_tweets"),
            "sent_count": sent_count,
            "failed_count": failed_count,
            "scheduled_count": scheduled_count,
            "created_at": campaign.get("created_at"),
            "tweets": tweets
        }

    async def cancel_campaign(self, campaign_id: str) -> bool:
        """
        Cancel a tweet campaign.

        Prevents remaining scheduled tweets from being posted.
        """
        if campaign_id not in self._active_campaigns:
            return False

        campaign = self._active_campaigns[campaign_id]
        campaign["status"] = "cancelled"

        logger.info(f"[{campaign_id}] Campaign cancelled")

        await self.event_bus.publish(
            "twitter.campaign.cancelled",
            {"campaign_id": campaign_id, "pipeline_id": campaign.get("pipeline_id")},
            source="TweetScheduler"
        )

        return True
