import os
from typing import List, Dict, Any
from datetime import datetime
import httpx
from ..base import SourceAdapter, PlatformMetricSnapshot, ContentVariant

class MetaConnector(SourceAdapter):
    def __init__(self):
        self.app_id = os.getenv("META_APP_ID")
        self.app_secret = os.getenv("META_APP_SECRET")
        self.access_token = os.getenv("META_ACCESS_TOKEN") # Long-lived token
        self.api_version = "v18.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    @property
    def id(self) -> str:
        return "meta"

    def is_enabled(self) -> bool:
        return bool(self.app_id and self.app_secret and self.access_token)

    def list_supported_platforms(self) -> List[str]:
        return ["facebook", "instagram", "threads"]

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """
        Fetch real metrics from Meta Graph API.

        For Instagram:
        - Fetch insights from /{media-id}/insights
        - Metrics: impressions, reach, engagement, saves, likes, comments, shares

        For Facebook:
        - Fetch post insights from /{post-id}/insights
        - Metrics: impressions, reach, engagement
        """
        if not self.is_enabled():
            return []

        if variant.platform not in self.list_supported_platforms():
            return []

        try:
            if variant.platform == "instagram":
                return await self._fetch_instagram_metrics(variant)
            elif variant.platform == "facebook":
                return await self._fetch_facebook_metrics(variant)
            else:
                # Threads or unsupported
                return []
        except Exception as e:
            # Log error and return empty list to avoid breaking the pipeline
            print(f"Error fetching metrics for {variant.platform} post {variant.content_id}: {e}")
            return []

    async def _fetch_instagram_metrics(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """Fetch Instagram media insights"""
        media_id = variant.content_id

        async with httpx.AsyncClient() as client:
            # Fetch insights for Instagram media
            # Available metrics: impressions, reach, engagement, saved, likes, comments, shares
            metrics_to_fetch = ["impressions", "reach", "engagement", "saved"]

            params = {
                "metric": ",".join(metrics_to_fetch),
                "access_token": self.access_token
            }

            insights_response = await client.get(
                f"{self.base_url}/{media_id}/insights",
                params=params
            )
            insights_response.raise_for_status()
            insights_data = insights_response.json()

            # Also fetch basic media data (likes, comments)
            media_response = await client.get(
                f"{self.base_url}/{media_id}",
                params={
                    "fields": "like_count,comments_count,media_url,permalink",
                    "access_token": self.access_token
                }
            )
            media_response.raise_for_status()
            media_data = media_response.json()

            # Parse insights
            insights_dict = {}
            for item in insights_data.get("data", []):
                metric_name = item.get("name")
                metric_value = item.get("values", [{}])[0].get("value", 0)
                insights_dict[metric_name] = metric_value

            return [PlatformMetricSnapshot(
                platform="instagram",
                platform_post_id=media_id,
                url=media_data.get("permalink"),
                snapshot_at=datetime.now(),
                impressions=insights_dict.get("impressions"),
                views=insights_dict.get("reach"),  # Reach as views
                likes=media_data.get("like_count"),
                comments=media_data.get("comments_count"),
                saves=insights_dict.get("saved"),
                raw_payload={
                    "insights": insights_data,
                    "media": media_data
                }
            )]

    async def _fetch_facebook_metrics(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """Fetch Facebook post insights"""
        post_id = variant.content_id

        async with httpx.AsyncClient() as client:
            # Fetch post data with engagement metrics
            params = {
                "fields": "shares,likes.summary(true),comments.summary(true),permalink_url",
                "access_token": self.access_token
            }

            post_response = await client.get(
                f"{self.base_url}/{post_id}",
                params=params
            )
            post_response.raise_for_status()
            post_data = post_response.json()

            # Fetch insights (impressions, reach, engagement)
            insights_params = {
                "metric": "post_impressions,post_engaged_users",
                "access_token": self.access_token
            }

            insights_response = await client.get(
                f"{self.base_url}/{post_id}/insights",
                params=insights_params
            )
            insights_response.raise_for_status()
            insights_data = insights_response.json()

            # Parse insights
            insights_dict = {}
            for item in insights_data.get("data", []):
                metric_name = item.get("name")
                metric_value = item.get("values", [{}])[0].get("value", 0)
                insights_dict[metric_name] = metric_value

            return [PlatformMetricSnapshot(
                platform="facebook",
                platform_post_id=post_id,
                url=post_data.get("permalink_url"),
                snapshot_at=datetime.now(),
                impressions=insights_dict.get("post_impressions"),
                likes=post_data.get("likes", {}).get("summary", {}).get("total_count"),
                comments=post_data.get("comments", {}).get("summary", {}).get("total_count"),
                shares=post_data.get("shares", {}).get("count"),
                raw_payload={
                    "post": post_data,
                    "insights": insights_data
                }
            )]

    async def publish_variant(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Publish content to Instagram/Facebook via Meta Graph API.

        For Instagram:
        - Create media container with image/video + caption
        - Publish media container

        For Facebook:
        - Create page photo/video post

        Args:
            variant: Content variant with media_url and description

        Returns:
            Dict with 'platform_post_id' and 'url'

        Raises:
            RuntimeError: If connector is not enabled or API call fails
        """
        if not self.is_enabled():
            raise RuntimeError("Meta connector is not enabled. Set META_ACCESS_TOKEN, META_APP_ID, META_APP_SECRET.")

        if variant.platform == "instagram":
            return await self._publish_to_instagram(variant)
        elif variant.platform == "facebook":
            return await self._publish_to_facebook(variant)
        elif variant.platform == "threads":
            return await self._publish_to_threads(variant)
        else:
            raise ValueError(f"Unsupported platform: {variant.platform}")

    async def _publish_to_instagram(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Publish to Instagram using Container API.

        Process:
        1. Create media container (POST /{ig-user-id}/media)
        2. Publish container (POST /{ig-user-id}/media_publish)
        """
        if not variant.media_url:
            raise ValueError("Instagram posts require media_url")

        ig_user_id = os.getenv("INSTAGRAM_USER_ID")
        if not ig_user_id:
            raise RuntimeError("INSTAGRAM_USER_ID not set")

        async with httpx.AsyncClient() as client:
            # Step 1: Create media container
            container_params = {
                "image_url": variant.media_url,
                "caption": variant.description or "",
                "access_token": self.access_token
            }

            container_response = await client.post(
                f"{self.base_url}/{ig_user_id}/media",
                params=container_params
            )
            container_response.raise_for_status()
            container_data = container_response.json()
            creation_id = container_data.get("id")

            if not creation_id:
                raise RuntimeError("Failed to create Instagram media container")

            # Step 2: Publish media container
            publish_params = {
                "creation_id": creation_id,
                "access_token": self.access_token
            }

            publish_response = await client.post(
                f"{self.base_url}/{ig_user_id}/media_publish",
                params=publish_params
            )
            publish_response.raise_for_status()
            publish_data = publish_response.json()
            media_id = publish_data.get("id")

            return {
                "platform_post_id": media_id,
                "url": f"https://www.instagram.com/p/{media_id}/",
                "status": "published"
            }

    async def _publish_to_facebook(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Publish to Facebook page.

        Uses /{page-id}/photos or /{page-id}/videos endpoint.
        """
        page_id = os.getenv("FACEBOOK_PAGE_ID")
        if not page_id:
            raise RuntimeError("FACEBOOK_PAGE_ID not set")

        async with httpx.AsyncClient() as client:
            if variant.media_url:
                # Photo/video post
                params = {
                    "url": variant.media_url,
                    "caption": variant.description or "",
                    "access_token": self.access_token
                }
                endpoint = f"{self.base_url}/{page_id}/photos"
            else:
                # Text-only post
                params = {
                    "message": variant.description or "",
                    "access_token": self.access_token
                }
                endpoint = f"{self.base_url}/{page_id}/feed"

            response = await client.post(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            post_id = data.get("id", "")

            return {
                "platform_post_id": post_id,
                "url": f"https://www.facebook.com/{post_id}",
                "status": "published"
            }

    async def _publish_to_threads(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Publish to Threads.

        Note: Threads API is still in development.
        This is a placeholder for future implementation.
        """
        raise NotImplementedError("Threads publishing not yet available via Meta Graph API")
