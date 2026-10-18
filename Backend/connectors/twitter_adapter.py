"""
Twitter/X Platform Adapter
==========================
Connector for Twitter/X API v2 for publishing tweets, fetching metrics,
and managing direct messages.

Implements ADAPT-001, ADAPT-002, ADAPT-003, NOMOCK-006.
"""

import os
import hashlib
import hmac
import base64
import time
import urllib.parse
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from loguru import logger

import httpx

from .base import SourceAdapter, ContentVariant, PlatformMetricSnapshot


class TwitterAdapter(SourceAdapter):
    """
    Twitter/X adapter using Twitter API v2 for publishing, metrics, and DMs.

    Requires Twitter API v2 credentials:
    - TWITTER_API_KEY (consumer key)
    - TWITTER_API_SECRET (consumer secret)
    - TWITTER_ACCESS_TOKEN (user access token)
    - TWITTER_ACCESS_SECRET (user access token secret)
    - TWITTER_BEARER_TOKEN (app-level bearer token)
    """

    TWITTER_API_BASE = "https://api.twitter.com/2"
    TWITTER_UPLOAD_BASE = "https://upload.twitter.com/1.1"
    MAX_TWEET_LENGTH = 280

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
        mode_allows = self._app_mode in ["twitter_only", "full_stack"]
        has_creds = bool(
            self._api_key
            and self._api_secret
            and self._access_token
            and self._access_secret
        )
        return mode_allows and has_creds

    def list_supported_platforms(self) -> List[str]:
        return ["twitter", "x"]

    # =========================================================================
    # OAuth 1.0a Signing
    # =========================================================================

    def _generate_oauth_signature(
        self, method: str, url: str, params: Dict[str, str]
    ) -> str:
        """Generate OAuth 1.0a signature for Twitter API requests."""
        sorted_params = "&".join(
            f"{urllib.parse.quote(k, safe='')}={urllib.parse.quote(str(v), safe='')}"
            for k, v in sorted(params.items())
        )
        base_string = (
            f"{method.upper()}&"
            f"{urllib.parse.quote(url, safe='')}&"
            f"{urllib.parse.quote(sorted_params, safe='')}"
        )
        signing_key = (
            f"{urllib.parse.quote(self._api_secret or '', safe='')}&"
            f"{urllib.parse.quote(self._access_secret or '', safe='')}"
        )
        signature = hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(signature).decode("utf-8")

    def _get_oauth_headers(self, method: str, url: str, extra_params: Optional[Dict] = None) -> Dict[str, str]:
        """Build OAuth 1.0a Authorization header for Twitter API v2."""
        import uuid

        oauth_params = {
            "oauth_consumer_key": self._api_key or "",
            "oauth_nonce": uuid.uuid4().hex,
            "oauth_signature_method": "HMAC-SHA1",
            "oauth_timestamp": str(int(time.time())),
            "oauth_token": self._access_token or "",
            "oauth_version": "1.0",
        }
        all_params = {**oauth_params, **(extra_params or {})}
        signature = self._generate_oauth_signature(method, url, all_params)
        oauth_params["oauth_signature"] = signature

        auth_header = "OAuth " + ", ".join(
            f'{urllib.parse.quote(k, safe="")}="{urllib.parse.quote(v, safe="")}"'
            for k, v in sorted(oauth_params.items())
        )
        return {"Authorization": auth_header}

    def _get_bearer_headers(self) -> Dict[str, str]:
        """Build Bearer token Authorization header."""
        if not self._bearer_token:
            raise RuntimeError("TWITTER_BEARER_TOKEN not configured")
        return {"Authorization": f"Bearer {self._bearer_token}"}

    # =========================================================================
    # PUBLISHING (ADAPT-001)
    # =========================================================================

    async def publish_post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Publish a tweet to Twitter/X.

        Args:
            payload: Dict with 'content' (text), optional 'media_urls' list,
                     and 'platform' key.

        Returns:
            Dict with 'success', 'id', optional 'media', and 'error' on failure.
        """
        content = payload.get("content", "")
        media_urls = payload.get("media_urls", [])

        # Validate content length
        if len(content) > self.MAX_TWEET_LENGTH:
            return {
                "success": False,
                "error": f"Tweet exceeds {self.MAX_TWEET_LENGTH} characters ({len(content)} chars)",
            }

        try:
            # Upload media if provided
            media_ids = []
            media_result = []
            for media_path in media_urls:
                upload_result = await self._upload_media(media_path)
                media_id = upload_result.get("media_id")
                if media_id:
                    media_ids.append(media_id)
                    media_result.append(upload_result)

            # Post tweet
            tweet_data = await self._post_tweet(content, media_ids=media_ids or None)

            result: Dict[str, Any] = {
                "success": True,
                "id": tweet_data.get("id"),
                "text": tweet_data.get("text", content),
            }
            if media_result:
                result["media"] = media_result

            return result

        except Exception as e:
            error_msg = str(e).lower()
            logger.error(f"Failed to publish tweet: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def _post_tweet(
        self,
        text: str,
        media_ids: Optional[List[str]] = None,
        reply_to: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Post a tweet via Twitter API v2.

        POST https://api.twitter.com/2/tweets

        Args:
            text: Tweet text (max 280 chars)
            media_ids: Optional list of uploaded media IDs
            reply_to: Optional tweet ID to reply to

        Returns:
            Dict with tweet 'id', 'text', 'created_at'
        """
        url = f"{self.TWITTER_API_BASE}/tweets"
        headers = self._get_oauth_headers("POST", url)
        headers["Content-Type"] = "application/json"

        body: Dict[str, Any] = {"text": text}
        if media_ids:
            body["media"] = {"media_ids": media_ids}
        if reply_to:
            body["reply"] = {"in_reply_to_tweet_id": reply_to}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {})

    async def _upload_media(self, media_path: str) -> Dict[str, Any]:
        """
        Upload media to Twitter via v1.1 media upload endpoint.

        POST https://upload.twitter.com/1.1/media/upload.json

        Args:
            media_path: Local file path or URL of media to upload

        Returns:
            Dict with 'media_id' and 'media_id_string'
        """
        url = f"{self.TWITTER_UPLOAD_BASE}/media/upload.json"
        headers = self._get_oauth_headers("POST", url)

        async with httpx.AsyncClient(timeout=60) as client:
            if media_path.startswith(("http://", "https://")):
                # Download remote media first
                dl_response = await client.get(media_path)
                dl_response.raise_for_status()
                media_data = dl_response.content
                files = {"media_data": base64.b64encode(media_data).decode("utf-8")}
                response = await client.post(url, headers=headers, data=files)
            else:
                # Upload local file
                with open(media_path, "rb") as f:
                    files = {"media": ("media", f, "application/octet-stream")}
                    response = await client.post(url, headers=headers, files=files)

            response.raise_for_status()
            data = response.json()
            return {
                "media_id": str(data.get("media_id", "")),
                "media_id_string": data.get("media_id_string", ""),
            }

    async def publish_variant(
        self, variant: ContentVariant
    ) -> Dict[str, str]:
        """
        Publish content via SourceAdapter interface.

        Args:
            variant: ContentVariant with title/description and optional media_url

        Returns:
            Dict with 'platform_post_id' and 'url'
        """
        text = variant.title or variant.description or ""
        if len(text) > self.MAX_TWEET_LENGTH:
            text = text[: self.MAX_TWEET_LENGTH - 3] + "..."

        media_urls = [variant.media_url] if variant.media_url else []
        result = await self.publish_post(
            {"content": text, "platform": "twitter", "media_urls": media_urls}
        )

        if not result.get("success"):
            raise RuntimeError(result.get("error", "Twitter publish failed"))

        tweet_id = result.get("id", "")
        return {
            "platform_post_id": tweet_id,
            "url": f"https://twitter.com/i/status/{tweet_id}",
        }

    # =========================================================================
    # METRICS (ADAPT-002)
    # =========================================================================

    async def fetch_post_metrics(self, tweet_id: str) -> Dict[str, Any]:
        """
        Fetch engagement metrics for a published tweet.

        Args:
            tweet_id: Twitter tweet ID

        Returns:
            Dict with views, likes, retweets, replies, bookmarks, engagement_rate
        """
        if not self._bearer_token and not self._access_token:
            logger.warning("Twitter API credentials not configured for metrics")
            return {"tweet_id": tweet_id, "error": "No credentials configured"}

        try:
            metrics = await self._get_tweet_metrics(tweet_id)
            return metrics
        except Exception as e:
            logger.error(f"Failed to fetch metrics for tweet {tweet_id}: {e}")
            return {"tweet_id": tweet_id, "error": str(e)}

    async def _get_tweet_metrics(self, tweet_id: str) -> Dict[str, Any]:
        """
        Fetch tweet metrics from Twitter API v2.

        GET https://api.twitter.com/2/tweets/:id
            ?tweet.fields=public_metrics,non_public_metrics,organic_metrics

        Args:
            tweet_id: Tweet ID

        Returns:
            Dict with all metric fields
        """
        url = f"{self.TWITTER_API_BASE}/tweets/{tweet_id}"
        headers = self._get_bearer_headers()
        params = {
            "tweet.fields": "public_metrics,non_public_metrics,organic_metrics",
            "expansions": "author_id",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        tweet_data = data.get("data", {})
        public = tweet_data.get("public_metrics", {})
        organic = tweet_data.get("organic_metrics", {})

        views = organic.get("impression_count", public.get("impression_count", 0))
        likes = public.get("like_count", 0)
        retweets = public.get("retweet_count", 0)
        replies = public.get("reply_count", 0)
        bookmarks = public.get("bookmark_count", 0)

        total_engagement = likes + retweets + replies + bookmarks
        engagement_rate = round((total_engagement / views * 100), 2) if views > 0 else 0.0

        return {
            "tweet_id": tweet_id,
            "views": views,
            "likes": likes,
            "retweets": retweets,
            "replies": replies,
            "bookmarks": bookmarks,
            "engagement_rate": engagement_rate,
            "url_link_clicks": organic.get("url_link_clicks", 0),
            "user_profile_clicks": organic.get("user_profile_clicks", 0),
        }

    async def fetch_metrics_for_variant(
        self, variant: ContentVariant
    ) -> List[PlatformMetricSnapshot]:
        """
        Fetch metrics for a content variant via SourceAdapter interface.

        Args:
            variant: ContentVariant with platform_post_id in metadata

        Returns:
            List of PlatformMetricSnapshot
        """
        tweet_id = getattr(variant, "platform_post_id", None)
        if not tweet_id:
            logger.warning(f"No tweet ID for variant {variant.content_id}")
            return []

        try:
            metrics = await self._get_tweet_metrics(tweet_id)
            snapshot = PlatformMetricSnapshot(
                platform="twitter",
                platform_post_id=tweet_id,
                url=f"https://twitter.com/i/status/{tweet_id}",
                snapshot_at=datetime.now(timezone.utc),
                views=metrics.get("views"),
                likes=metrics.get("likes"),
                shares=metrics.get("retweets"),
                comments=metrics.get("replies"),
                raw_payload={
                    "bookmarks": metrics.get("bookmarks"),
                    "engagement_rate": metrics.get("engagement_rate"),
                    "url_link_clicks": metrics.get("url_link_clicks"),
                    "user_profile_clicks": metrics.get("user_profile_clicks"),
                },
            )
            return [snapshot]
        except Exception as e:
            logger.error(f"Failed to fetch metrics for tweet {tweet_id}: {e}")
            return []

    # =========================================================================
    # DIRECT MESSAGES (ADAPT-003)
    # =========================================================================

    async def send_dm(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a direct message on Twitter/X.

        Args:
            payload: Dict with 'recipient' (username or user_id), 'message' text,
                     and optional 'conversation_id'.

        Returns:
            Dict with 'dm_id', 'recipient', 'text', 'sent_at', optional 'conversation_id'
        """
        recipient = payload.get("recipient", "")
        message = payload.get("message", "")
        conversation_id = payload.get("conversation_id")

        result = await self._send_dm(recipient, message, conversation_id)
        return result

    async def _send_dm(
        self,
        recipient: str,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send DM via Twitter API v2.

        POST https://api.twitter.com/2/dm_conversations/with/:participant_id/messages

        Args:
            recipient: Twitter username or user ID
            message: Message text (max 10,000 chars)
            conversation_id: Optional existing conversation ID

        Returns:
            Dict with DM event info
        """
        # Resolve username to user ID if needed
        user_id = recipient
        if not recipient.isdigit():
            user_id = await self._get_user_id_by_username(recipient) or recipient

        if conversation_id:
            url = f"{self.TWITTER_API_BASE}/dm_conversations/{conversation_id}/messages"
        else:
            url = f"{self.TWITTER_API_BASE}/dm_conversations/with/{user_id}/messages"

        headers = self._get_oauth_headers("POST", url)
        headers["Content-Type"] = "application/json"

        body = {"text": message}

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            data = response.json()

        dm_data = data.get("data", {})
        result: Dict[str, Any] = {
            "dm_id": dm_data.get("dm_event_id", dm_data.get("id", "")),
            "recipient": recipient,
            "text": message,
            "sent_at": datetime.now(timezone.utc).isoformat(),
        }
        if conversation_id:
            result["conversation_id"] = conversation_id

        return result

    async def poll_incoming_dms(self) -> List[Dict[str, Any]]:
        """
        Poll for incoming direct messages.

        Returns:
            List of DM event dicts with dm_id, sender, text, received_at
        """
        dms = await self._poll_dms()
        return dms

    async def _poll_dms(self) -> List[Dict[str, Any]]:
        """
        Fetch recent DM events via Twitter API v2.

        GET https://api.twitter.com/2/dm_events
            ?event_types=MessageCreate
            &dm_event.fields=id,text,sender_id,created_at,dm_conversation_id

        Returns:
            List of DM event dicts
        """
        url = f"{self.TWITTER_API_BASE}/dm_events"
        headers = self._get_oauth_headers("GET", url)
        params = {
            "event_types": "MessageCreate",
            "dm_event.fields": "id,text,sender_id,created_at,dm_conversation_id",
            "max_results": "50",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        events = data.get("data", [])
        result = []
        for event in events:
            result.append(
                {
                    "dm_id": event.get("id", ""),
                    "sender": event.get("sender_id", ""),
                    "text": event.get("text", ""),
                    "received_at": event.get("created_at", datetime.now(timezone.utc).isoformat()),
                    "conversation_id": event.get("dm_conversation_id", ""),
                }
            )

        return result

    async def fetch_mentions(
        self, since_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch mentions and replies to account.

        GET https://api.twitter.com/2/users/:id/mentions

        Args:
            since_id: Only fetch tweets after this tweet ID

        Returns:
            List of tweet objects
        """
        if not self._bearer_token and not self._access_token:
            logger.warning("Twitter API credentials not configured")
            return []

        # Get authenticated user ID
        me = await self._get_authenticated_user()
        if not me:
            return []

        user_id = me.get("id", "")
        url = f"{self.TWITTER_API_BASE}/users/{user_id}/mentions"
        headers = self._get_bearer_headers()
        params: Dict[str, str] = {
            "tweet.fields": "author_id,created_at,text,public_metrics",
            "max_results": "100",
        }
        if since_id:
            params["since_id"] = since_id

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to fetch mentions: {e}")
            return []

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    async def _get_user_id_by_username(self, username: str) -> Optional[str]:
        """Look up a Twitter user ID from username."""
        username = username.lstrip("@")
        url = f"{self.TWITTER_API_BASE}/users/by/username/{username}"
        headers = self._get_bearer_headers()

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("data", {}).get("id")

    async def _get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        """Get the authenticated user's info."""
        url = f"{self.TWITTER_API_BASE}/users/me"
        headers = self._get_bearer_headers()

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                return data.get("data")
        except Exception as e:
            logger.error(f"Failed to get authenticated user: {e}")
            return None

    def validate_tweet_text(self, text: str) -> bool:
        """Validate tweet text length."""
        return len(text) <= self.MAX_TWEET_LENGTH
