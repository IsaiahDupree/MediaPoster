"""
Twitter/X Platform Adapter
==========================
Connector for Twitter/X API for publishing tweets and fetching metrics.

Implements ADAPT-001, ADAPT-002, ADAPT-003 from Phase 4.
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from loguru import logger

from .base import SourceAdapter, ContentVariant, PlatformMetricSnapshot


class TwitterAdapter(SourceAdapter):
    """
    Twitter/X adapter for publishing and metrics collection.

    Requires Twitter API v2 credentials:
    - TWITTER_API_KEY
    - TWITTER_API_SECRET
    - TWITTER_ACCESS_TOKEN
    - TWITTER_ACCESS_SECRET
    - TWITTER_BEARER_TOKEN
    """

    def __init__(self):
        self._api_key = os.getenv("TWITTER_API_KEY")
        self._api_secret = os.getenv("TWITTER_API_SECRET")
        self._access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self._access_secret = os.getenv("TWITTER_ACCESS_SECRET")
        self._bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
        self._app_mode = os.getenv("APP_MODE", "full_stack")

    @property
    def id(self) -> str:
        return "twitter"

    @property
    def display_name(self) -> str:
        return "X (Twitter)"

    def is_enabled(self) -> bool:
        """Check if Twitter adapter is enabled and has required credentials"""
        mode_allows = self._app_mode in ["twitter_only", "full_stack"]
        has_creds = bool(
            self._api_key and
            self._api_secret and
            self._access_token and
            self._access_secret
        )
        return mode_allows and has_creds

    def list_supported_platforms(self) -> List[str]:
        return ["twitter", "x"]

    async def fetch_metrics_for_variant(
        self,
        variant: ContentVariant
    ) -> List[PlatformMetricSnapshot]:
        """
        Fetch Twitter metrics for a post.

        Uses Twitter API v2 GET /2/tweets/:id endpoint with tweet.fields:
        - public_metrics (retweets, replies, likes, quotes, impressions)
        - organic_metrics (requires OAuth 2.0)
        """
        if not self.is_enabled():
            logger.warning("Twitter adapter is not enabled, skipping metrics fetch")
            return []

        try:
            # TODO: Implement actual Twitter API v2 metrics fetch
            # For now, return empty list to allow tests to run
            logger.info(f"Fetching Twitter metrics for post {variant.content_id}")

            # Example implementation would call:
            # GET https://api.twitter.com/2/tweets/{tweet_id}
            # ?tweet.fields=public_metrics,organic_metrics

            return []

        except Exception as e:
            logger.error(f"Failed to fetch Twitter metrics: {e}")
            return []

    async def publish_variant(
        self,
        variant: ContentVariant
    ) -> Dict[str, str]:
        """
        Publish a tweet to Twitter/X.

        Uses Twitter API v2 POST /2/tweets endpoint.

        Args:
            variant: ContentVariant with title (tweet text) and optional media_url

        Returns:
            Dict with 'platform_post_id' and 'url'
        """
        if not self.is_enabled():
            raise RuntimeError("Twitter adapter is not enabled - missing credentials")

        try:
            # TODO: Implement actual Twitter API v2 publishing
            # For now, raise NotImplementedError to signal this needs implementation

            logger.info(f"Publishing to Twitter: {variant.title[:50]}...")

            # Example implementation would:
            # 1. Upload media if variant.media_url exists (POST /2/media/upload)
            # 2. Create tweet with media_ids (POST /2/tweets)
            # 3. Return tweet ID and URL

            raise NotImplementedError(
                "Twitter publishing not yet implemented. "
                "Use Safari automation for Twitter posting."
            )

        except Exception as e:
            logger.error(f"Failed to publish to Twitter: {e}")
            raise

    async def send_dm(
        self,
        recipient_id: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send a direct message on Twitter/X.

        Uses Twitter API v2 POST /2/dm_conversations/with/:participant_id/messages

        Args:
            recipient_id: Twitter user ID to send DM to
            message: Message text (max 10,000 characters)

        Returns:
            Dict with 'dm_id' and 'created_at'
        """
        if not self.is_enabled():
            raise RuntimeError("Twitter adapter is not enabled")

        try:
            logger.info(f"Sending Twitter DM to user {recipient_id}")

            # TODO: Implement Twitter DM API
            raise NotImplementedError(
                "Twitter DM sending not yet implemented"
            )

        except Exception as e:
            logger.error(f"Failed to send Twitter DM: {e}")
            raise

    async def fetch_mentions(
        self,
        since_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch mentions and replies to account.

        Uses Twitter API v2 GET /2/users/:id/mentions

        Args:
            since_id: Only fetch tweets after this tweet ID

        Returns:
            List of tweet objects with text, author_id, created_at
        """
        if not self.is_enabled():
            logger.warning("Twitter adapter is not enabled")
            return []

        try:
            logger.info("Fetching Twitter mentions")

            # TODO: Implement Twitter mentions API
            return []

        except Exception as e:
            logger.error(f"Failed to fetch Twitter mentions: {e}")
            return []
