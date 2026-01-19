"""
Twitter/X Connector Implementation

Handles publishing and metrics fetching for Twitter/X platform.
Uses Blotato API for publishing and Twitter API v2 for comprehensive metrics.
"""

import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
from ..base import SourceAdapter, ContentVariant, PlatformMetricSnapshot
from services.blotato_api import BlotatoAPI, PostContent, TwitterTarget, Platform

logger = logging.getLogger(__name__)


class TwitterConnector(SourceAdapter):
    """
    Twitter/X platform connector.

    Features:
    - Publish single tweets
    - Publish threads (multiple tweets)
    - Fetch comprehensive metrics (views, likes, retweets, replies, bookmarks, etc.)
    - Character limit validation (280 chars)
    - Media attachment support
    """

    def __init__(self):
        # Twitter API credentials (for metrics)
        self.api_key = os.getenv("TWITTER_API_KEY")
        self.api_secret = os.getenv("TWITTER_API_SECRET")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN")
        self.access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        self.bearer_token = os.getenv("TWITTER_BEARER_TOKEN")

        # Blotato integration (for publishing)
        self.blotato_api_key = os.getenv("BLOTATO_API_KEY")
        self.twitter_account_id = os.getenv("TWITTER_ACCOUNT_ID", "4151")  # Default to known account

        # Initialize Blotato API client
        self.blotato = BlotatoAPI()

        # Twitter API v2 base URL
        self.twitter_api_base = "https://api.twitter.com/2"

    @property
    def id(self) -> str:
        """Unique connector identifier"""
        return "twitter"

    @property
    def display_name(self) -> str:
        """Human-readable connector name"""
        return "Twitter/X"

    def is_enabled(self) -> bool:
        """
        Check if connector is enabled.
        Requires either:
        - Blotato API key (for publishing)
        - Twitter API credentials (for metrics)
        """
        has_blotato = bool(self.blotato_api_key)
        has_twitter_api = bool(
            self.bearer_token or
            (self.api_key and self.api_secret and self.access_token and self.access_token_secret)
        )

        return has_blotato or has_twitter_api

    def list_supported_platforms(self) -> List[str]:
        """Returns list of supported platforms"""
        return ["twitter"]

    # =========================================================================
    # PUBLISHING
    # =========================================================================

    async def publish_variant(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Publish content to Twitter.

        Args:
            variant: Content variant with title, description, media_url

        Returns:
            Dict with 'platform_post_id' and 'url'

        Raises:
            RuntimeError: If Blotato API is not configured
            ValueError: If content exceeds character limits
        """
        if not self.blotato_api_key:
            raise RuntimeError("Blotato API key not configured. Cannot publish to Twitter.")

        # Prepare tweet text
        tweet_text = self._prepare_tweet_text(variant)

        # Validate character limit
        if len(tweet_text) > 280:
            raise ValueError(f"Tweet text exceeds 280 characters: {len(tweet_text)} chars")

        # Prepare media URLs
        media_urls = []
        if variant.media_url:
            media_urls.append(variant.media_url)

        # Create post content
        content = PostContent(
            text=tweet_text,
            platform=Platform.TWITTER,
            media_urls=media_urls
        )

        # Create Twitter target
        target = TwitterTarget()

        try:
            # Publish via Blotato
            logger.info(f"Publishing tweet via Blotato (account: {self.twitter_account_id})")
            response = await self.blotato.publish_post(
                account_id=self.twitter_account_id,
                content=content,
                target=target
            )

            # Extract post submission ID
            post_submission_id = response.get("postSubmissionId", "")

            # Construct Twitter URL (we'll get the actual URL from checkback)
            # For now, return the submission ID
            return {
                "platform_post_id": post_submission_id,
                "url": f"https://twitter.com/i/status/{post_submission_id}",  # Placeholder
                "status": "submitted"
            }

        except Exception as e:
            logger.error(f"Failed to publish tweet: {str(e)}")
            raise RuntimeError(f"Twitter publish failed: {str(e)}")

    async def publish_thread(
        self,
        variant: ContentVariant,
        additional_tweets: List[str]
    ) -> Dict[str, str]:
        """
        Publish a Twitter thread.

        Args:
            variant: Content variant for the first tweet
            additional_tweets: List of additional tweet texts

        Returns:
            Dict with thread information

        Raises:
            RuntimeError: If Blotato API is not configured
            ValueError: If any tweet exceeds character limits
        """
        if not self.blotato_api_key:
            raise RuntimeError("Blotato API key not configured. Cannot publish thread.")

        # Prepare first tweet
        first_tweet_text = self._prepare_tweet_text(variant)

        # Validate all tweets
        all_tweets = [first_tweet_text] + additional_tweets
        for i, tweet in enumerate(all_tweets):
            if len(tweet) > 280:
                raise ValueError(f"Tweet {i+1} exceeds 280 characters: {len(tweet)} chars")

        # Prepare media URLs
        media_urls = []
        if variant.media_url:
            media_urls.append(variant.media_url)

        # Create additional posts for thread
        additional_posts = [
            {"text": tweet} for tweet in additional_tweets
        ]

        # Create post content with thread
        content = PostContent(
            text=first_tweet_text,
            platform=Platform.TWITTER,
            media_urls=media_urls,
            additional_posts=additional_posts
        )

        # Create Twitter target
        target = TwitterTarget()

        try:
            # Publish thread via Blotato
            logger.info(f"Publishing thread ({len(all_tweets)} tweets) via Blotato")
            response = await self.blotato.publish_post(
                account_id=self.twitter_account_id,
                content=content,
                target=target
            )

            # Extract post submission ID
            post_submission_id = response.get("postSubmissionId", "")

            return {
                "platform_post_id": post_submission_id,
                "url": f"https://twitter.com/i/status/{post_submission_id}",  # Placeholder
                "status": "submitted",
                "thread_length": len(all_tweets)
            }

        except Exception as e:
            logger.error(f"Failed to publish thread: {str(e)}")
            raise RuntimeError(f"Twitter thread publish failed: {str(e)}")

    def _prepare_tweet_text(self, variant: ContentVariant) -> str:
        """
        Prepare tweet text from variant.

        Priority:
        1. variant.title (if present and <= 280 chars)
        2. variant.description (if present)
        3. Combination of title + description (truncated)

        Args:
            variant: Content variant

        Returns:
            Tweet text (max 280 chars)
        """
        if variant.title and len(variant.title) <= 280:
            return variant.title

        if variant.description:
            # Truncate description if needed
            if len(variant.description) <= 280:
                return variant.description
            else:
                return variant.description[:277] + "..."

        if variant.title:
            # Title is too long, truncate it
            return variant.title[:277] + "..."

        # Fallback
        return f"New post about {variant.content_id}"

    # =========================================================================
    # METRICS FETCHING
    # =========================================================================

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """
        Fetch Twitter metrics for a published tweet.

        Uses Twitter API v2 to fetch:
        - Impressions (views)
        - Likes
        - Retweets
        - Replies
        - Quotes
        - Bookmarks
        - Profile clicks
        - URL clicks

        Args:
            variant: Content variant with platform_post_id in metadata

        Returns:
            List of PlatformMetricSnapshot objects
        """
        if not self.bearer_token and not (self.access_token and self.access_token_secret):
            logger.warning("Twitter API credentials not configured. Cannot fetch metrics.")
            return []

        # Extract tweet ID from variant
        # TODO: This assumes variant has metadata with tweet_id
        # In practice, we'd query the database for the PlatformPost record
        tweet_id = getattr(variant, "platform_post_id", None)
        if not tweet_id:
            logger.warning(f"No tweet ID found for variant {variant.content_id}")
            return []

        try:
            metrics_data = await self._fetch_tweet_metrics(tweet_id)

            # Convert to PlatformMetricSnapshot
            snapshot = PlatformMetricSnapshot(
                platform="twitter",
                platform_post_id=tweet_id,
                url=f"https://twitter.com/i/status/{tweet_id}",
                snapshot_at=datetime.utcnow(),
                views=metrics_data.get("impression_count"),
                likes=metrics_data.get("like_count"),
                shares=metrics_data.get("retweet_count"),
                comments=metrics_data.get("reply_count"),
                # Additional Twitter-specific metrics
                raw_payload={
                    "quote_count": metrics_data.get("quote_count"),
                    "bookmark_count": metrics_data.get("bookmark_count"),
                    "url_link_clicks": metrics_data.get("url_link_clicks"),
                    "user_profile_clicks": metrics_data.get("user_profile_clicks")
                }
            )

            return [snapshot]

        except Exception as e:
            logger.error(f"Failed to fetch metrics for tweet {tweet_id}: {str(e)}")
            return []

    async def _fetch_tweet_metrics(self, tweet_id: str) -> Dict[str, Any]:
        """
        Fetch metrics for a specific tweet using Twitter API v2.

        Args:
            tweet_id: Twitter tweet ID

        Returns:
            Dict with metric counts
        """
        # Prepare headers
        headers = {}
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        else:
            # Use OAuth 1.0a if bearer token not available
            # TODO: Implement OAuth 1.0a signing
            raise NotImplementedError("OAuth 1.0a not yet implemented. Please provide TWITTER_BEARER_TOKEN.")

        # Twitter API v2 endpoint for tweet metrics
        url = f"{self.twitter_api_base}/tweets/{tweet_id}"
        params = {
            "tweet.fields": "public_metrics,non_public_metrics,organic_metrics",
            "expansions": "author_id"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()
            tweet_data = data.get("data", {})

            # Combine public and organic metrics
            public_metrics = tweet_data.get("public_metrics", {})
            organic_metrics = tweet_data.get("organic_metrics", {})

            return {
                "impression_count": organic_metrics.get("impression_count", 0),
                "like_count": public_metrics.get("like_count", 0),
                "retweet_count": public_metrics.get("retweet_count", 0),
                "reply_count": public_metrics.get("reply_count", 0),
                "quote_count": public_metrics.get("quote_count", 0),
                "bookmark_count": public_metrics.get("bookmark_count", 0),
                "url_link_clicks": organic_metrics.get("url_link_clicks", 0),
                "user_profile_clicks": organic_metrics.get("user_profile_clicks", 0)
            }

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def validate_tweet_text(self, text: str) -> bool:
        """
        Validate tweet text length.

        Args:
            text: Tweet text to validate

        Returns:
            True if valid, False otherwise
        """
        return len(text) <= 280

    def split_into_thread(self, long_text: str, max_length: int = 280) -> List[str]:
        """
        Split long text into multiple tweets for a thread.

        Args:
            long_text: Long text to split
            max_length: Maximum characters per tweet (default 280)

        Returns:
            List of tweet texts
        """
        # Simple splitting by sentences
        sentences = long_text.split(". ")
        tweets = []
        current_tweet = ""

        for sentence in sentences:
            # Add period back if not last sentence
            sentence = sentence.strip()
            if not sentence.endswith("."):
                sentence += "."

            # Check if adding this sentence would exceed limit
            if len(current_tweet) + len(sentence) + 1 <= max_length:
                current_tweet += (" " if current_tweet else "") + sentence
            else:
                # Save current tweet and start new one
                if current_tweet:
                    tweets.append(current_tweet)
                current_tweet = sentence

        # Add final tweet
        if current_tweet:
            tweets.append(current_tweet)

        return tweets

    # =========================================================================
    # DIRECT MESSAGES (ADAPT-003)
    # =========================================================================

    async def send_dm(
        self,
        username: str,
        message: str,
        use_safari_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Send a direct message to a Twitter user.

        Args:
            username: Twitter username (without @)
            message: Message text to send
            use_safari_fallback: Use Safari automation if API not available

        Returns:
            Dict with 'success', 'dm_id', and 'timestamp'

        Raises:
            RuntimeError: If both API and Safari automation fail
        """
        # Try Twitter API v2 DM endpoint first (if credentials available)
        if self.bearer_token:
            try:
                return await self._send_dm_via_api(username, message)
            except Exception as e:
                logger.warning(f"Twitter API DM failed: {str(e)}")
                if not use_safari_fallback:
                    raise

        # Fallback to Safari automation
        if use_safari_fallback:
            logger.info("Using Safari automation for DM sending")
            return await self._send_dm_via_safari(username, message)

        raise RuntimeError("Unable to send DM: API credentials not available and Safari fallback disabled")

    async def _send_dm_via_api(self, username: str, message: str) -> Dict[str, Any]:
        """
        Send DM via Twitter API v2.

        Note: Twitter API v2 DM endpoints require special permissions.
        Most apps won't have access to this endpoint.

        Args:
            username: Twitter username
            message: Message text

        Returns:
            Dict with DM information
        """
        # First, get user ID from username
        user_id = await self._get_user_id_by_username(username)

        if not user_id:
            raise ValueError(f"User @{username} not found")

        # Send DM via API
        url = f"{self.twitter_api_base}/dm_conversations/with/{user_id}/messages"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        payload = {
            "text": message
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()
            dm_data = data.get("data", {})

            return {
                "success": True,
                "dm_id": dm_data.get("dm_event_id"),
                "timestamp": datetime.utcnow().isoformat(),
                "method": "api"
            }

    async def _send_dm_via_safari(self, username: str, message: str) -> Dict[str, Any]:
        """
        Send DM via Safari automation.

        Args:
            username: Twitter username
            message: Message text

        Returns:
            Dict with DM information
        """
        try:
            from automation.safari_twitter_dm import SafariTwitterDM

            dm_automation = SafariTwitterDM()
            success = dm_automation.send_dm(username, message)

            if success:
                return {
                    "success": True,
                    "dm_id": None,  # Safari automation doesn't return DM ID
                    "timestamp": datetime.utcnow().isoformat(),
                    "method": "safari"
                }
            else:
                raise RuntimeError("Safari DM automation failed")

        except ImportError:
            raise RuntimeError("Safari DM automation not available")

    async def _get_user_id_by_username(self, username: str) -> Optional[str]:
        """
        Get Twitter user ID from username.

        Args:
            username: Twitter username (without @)

        Returns:
            User ID or None if not found
        """
        if not self.bearer_token:
            return None

        # Remove @ if present
        username = username.lstrip("@")

        url = f"{self.twitter_api_base}/users/by/username/{username}"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            data = response.json()
            user_data = data.get("data", {})

            return user_data.get("id")

    async def check_dm_inbox(self, use_safari: bool = True) -> List[Dict[str, Any]]:
        """
        Check DM inbox for recent conversations.

        Args:
            use_safari: Use Safari automation (default: True)

        Returns:
            List of conversations
        """
        if use_safari:
            try:
                from automation.safari_twitter_dm import SafariTwitterDM

                dm_automation = SafariTwitterDM()
                conversations = dm_automation.check_inbox()

                return conversations

            except ImportError:
                logger.error("Safari DM automation not available")
                return []

        # API-based inbox checking would go here
        # (requires special Twitter API access)
        logger.warning("API-based inbox checking not implemented")
        return []

    async def get_unread_dm_count(self, use_safari: bool = True) -> Optional[int]:
        """
        Get number of unread DM conversations.

        Args:
            use_safari: Use Safari automation (default: True)

        Returns:
            Number of unread conversations or None if unable to determine
        """
        if use_safari:
            try:
                from automation.safari_twitter_dm import SafariTwitterDM

                dm_automation = SafariTwitterDM()
                count = dm_automation.get_unread_count()

                return count

            except ImportError:
                logger.error("Safari DM automation not available")
                return None

        # API-based unread count would go here
        logger.warning("API-based unread count not implemented")
        return None

    async def send_bulk_dms(
        self,
        recipients: List[str],
        message: str,
        delay_between: float = 15.0,
        use_safari: bool = True
    ) -> Dict[str, bool]:
        """
        Send the same message to multiple recipients.

        Args:
            recipients: List of Twitter usernames
            message: Message text to send
            delay_between: Seconds to wait between each DM
            use_safari: Use Safari automation (default: True)

        Returns:
            Dict mapping username to success status
        """
        if use_safari:
            try:
                from automation.safari_twitter_dm import SafariTwitterDM

                dm_automation = SafariTwitterDM()
                results = dm_automation.send_bulk_dms(recipients, message, delay_between)

                return results

            except ImportError:
                logger.error("Safari DM automation not available")
                return {username: False for username in recipients}

        # API-based bulk sending
        results = {}
        for username in recipients:
            try:
                result = await self.send_dm(username, message, use_safari_fallback=False)
                results[username] = result.get("success", False)

                # Rate limiting
                if delay_between > 0:
                    import asyncio
                    await asyncio.sleep(delay_between)

            except Exception as e:
                logger.error(f"Failed to send DM to @{username}: {str(e)}")
                results[username] = False

        return results
