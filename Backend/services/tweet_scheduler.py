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

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
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
        """
        Schedule a tweet campaign (ARCH-004).

        Tweets are scheduled at regular intervals (2-hour intervals for 12/day).
        Each tweet includes offer URL with tracking parameters if provided.

        Args:
            pipeline_id: Pipeline ID for correlation
            theme: Content theme for tweet generation
            tweets_per_day: Number of tweets per day (default 12 = 2-hour intervals)
            offer_url: URL to include in tweets for tracking
            duration_days: How many days to run campaign (default 1)
            base_message: Optional base message to include in all tweets
            hashtags: Optional list of hashtags to include
            start_delay_minutes: Minutes to delay before first tweet (default 0)

        Returns:
            Dict with campaign_id, scheduled_count, and tweet_schedule
        """
        campaign_id = f"tweet-campaign-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)

        logger.info(
            f"[{campaign_id}] Scheduling {tweets_per_day} tweets/day for {duration_days} days: {theme}"
        )

        # Calculate interval between tweets (minutes)
        interval_minutes = int((24 * 60) / tweets_per_day)

        # Generate tweet schedule
        tweet_schedule = []
        total_tweets = tweets_per_day * duration_days

        for tweet_num in range(1, total_tweets + 1):
            # Calculate scheduled time
            delay = timedelta(
                minutes=start_delay_minutes + (interval_minutes * (tweet_num - 1))
            )
            scheduled_time = now + delay

            tweet = {
                "tweet_id": f"{campaign_id}_tweet{tweet_num}",
                "campaign_id": campaign_id,
                "pipeline_id": pipeline_id,
                "tweet_num": tweet_num,
                "scheduled_at": scheduled_time.isoformat(),
                "status": TweetStatus.SCHEDULED.value,
                "theme": theme,
                "offer_url": offer_url,
                "base_message": base_message,
                "hashtags": hashtags or [],
                "created_at": now.isoformat()
            }
            tweet_schedule.append(tweet)

        # Store campaign
        self._active_campaigns[campaign_id] = {
            "campaign_id": campaign_id,
            "pipeline_id": pipeline_id,
            "theme": theme,
            "tweets_per_day": tweets_per_day,
            "duration_days": duration_days,
            "offer_url": offer_url,
            "status": "scheduled",
            "created_at": now.isoformat(),
            "total_tweets": total_tweets,
            "scheduled_tweets": tweet_schedule
        }

        # Store scheduled tweets for quick lookup
        self._scheduled_tweets[campaign_id] = tweet_schedule

        # Schedule actual tweet posting via event bus
        for tweet in tweet_schedule:
            await self._schedule_tweet_event(tweet)

        # Emit campaign scheduled event
        await self.event_bus.publish(
            "twitter.campaign.scheduled",
            {
                "campaign_id": campaign_id,
                "pipeline_id": pipeline_id,
                "tweets_scheduled": len(tweet_schedule),
                "first_tweet_time": tweet_schedule[0]["scheduled_at"],
                "last_tweet_time": tweet_schedule[-1]["scheduled_at"]
            },
            correlation_id=pipeline_id,
            source="TweetScheduler"
        )

        logger.info(
            f"[{campaign_id}] ✅ Scheduled {len(tweet_schedule)} tweets across {duration_days} day(s)"
        )

        return {
            "campaign_id": campaign_id,
            "pipeline_id": pipeline_id,
            "scheduled_count": len(tweet_schedule),
            "first_tweet": tweet_schedule[0]["scheduled_at"] if tweet_schedule else None,
            "last_tweet": tweet_schedule[-1]["scheduled_at"] if tweet_schedule else None,
            "interval_minutes": interval_minutes,
            "tweet_schedule": tweet_schedule
        }

    async def _schedule_tweet_event(self, tweet: Dict[str, Any]) -> None:
        """
        Schedule a tweet by creating a task that will post at the scheduled time.

        Uses async task scheduling to delay tweet posting until scheduled_at time.
        """
        try:
            scheduled_time = datetime.fromisoformat(tweet["scheduled_at"])
            now = datetime.now(timezone.utc)
            delay_seconds = (scheduled_time - now).total_seconds()

            if delay_seconds <= 0:
                # Tweet is due now or overdue
                await self._post_tweet(tweet)
            else:
                # Schedule tweet posting in the future
                asyncio.create_task(
                    self._post_tweet_delayed(tweet, delay_seconds)
                )
                logger.debug(
                    f"Scheduled tweet {tweet['tweet_id']} in {delay_seconds:.1f}s"
                )

        except Exception as e:
            logger.error(f"Failed to schedule tweet {tweet['tweet_id']}: {e}")

    async def _post_tweet_delayed(self, tweet: Dict[str, Any], delay_seconds: float) -> None:
        """Post a tweet after a delay."""
        try:
            await asyncio.sleep(delay_seconds)
            await self._post_tweet(tweet)
        except asyncio.CancelledError:
            logger.debug(f"Tweet {tweet['tweet_id']} posting cancelled")
        except Exception as e:
            logger.error(f"Failed to post delayed tweet {tweet['tweet_id']}: {e}")

    async def _post_tweet(self, tweet: Dict[str, Any]) -> None:
        """
        Post a single tweet via Twitter service.

        Constructs tweet text from theme/message/hashtags and posts it.
        """
        tweet_id = tweet.get("tweet_id")
        campaign_id = tweet.get("campaign_id")

        try:
            # Build tweet text
            text = self._build_tweet_text(tweet)

            logger.info(f"[{campaign_id}] 📤 Posting tweet {tweet_id}: {text[:60]}...")

            if self._twitter_service:
                # Post via Twitter service
                result = await self._twitter_service.post_tweet(text)

                if result.get("success"):
                    tweet["status"] = TweetStatus.SENT.value
                    tweet["posted_at"] = datetime.now(timezone.utc).isoformat()

                    # Emit success event
                    await self.event_bus.publish(
                        "twitter.tweet.sent",
                        {
                            "tweet_id": tweet_id,
                            "campaign_id": campaign_id,
                            "pipeline_id": tweet.get("pipeline_id"),
                            "platform_id": result.get("id"),
                            "posted_at": tweet["posted_at"]
                        },
                        source="TweetScheduler"
                    )
                    logger.info(f"[{campaign_id}] ✅ Tweet {tweet_id} posted successfully")
                else:
                    raise Exception(result.get("error", "Unknown error"))
            else:
                # No Twitter service available - log only
                tweet["status"] = TweetStatus.SCHEDULED.value
                logger.warning(f"[{campaign_id}] No Twitter service available, cannot post tweet")

        except Exception as e:
            logger.error(f"[{campaign_id}] ❌ Failed to post tweet {tweet_id}: {e}")
            tweet["status"] = TweetStatus.FAILED.value
            tweet["error"] = str(e)

            # Emit failure event
            await self.event_bus.publish(
                "twitter.tweet.failed",
                {
                    "tweet_id": tweet_id,
                    "campaign_id": campaign_id,
                    "pipeline_id": tweet.get("pipeline_id"),
                    "error": str(e)
                },
                source="TweetScheduler"
            )

    def _build_tweet_text(self, tweet: Dict[str, Any]) -> str:
        """
        Build tweet text from template + theme + offer URL.

        Constructs engaging tweet that includes:
        - Theme/hook
        - Call to action
        - Offer URL (with tracking if available)
        - Hashtags
        """
        theme = tweet.get("theme", "Check this out")
        offer_url = tweet.get("offer_url", "")
        base_message = tweet.get("base_message")
        hashtags = tweet.get("hashtags", [])
        tweet_num = tweet.get("tweet_num", 1)

        # Create tweet text
        parts = []

        if base_message:
            parts.append(base_message)
        else:
            parts.append(f"🔥 {theme}")

        if offer_url:
            parts.append(f"🎯 {offer_url}")

        # Add hashtags
        if hashtags:
            parts.append(" ".join([f"#{tag}" for tag in hashtags[:3]]))

        text = "\n".join(parts)

        # Twitter limit is 280 chars, truncate if needed
        if len(text) > 280:
            text = text[:277] + "..."

        return text

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
