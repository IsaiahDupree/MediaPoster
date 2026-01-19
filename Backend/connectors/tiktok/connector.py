import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from ..base import SourceAdapter, PlatformMetricSnapshot, ContentVariant

class TikTokConnector(SourceAdapter):
    """
    TikTok Connector Implementation

    Uses TikTok API for Business (https://developers.tiktok.com/)

    Features:
    - Publish videos to TikTok
    - Fetch video analytics (views, likes, comments, shares)
    - Support for TikTok Creator API
    """

    def __init__(self):
        self.app_key = os.getenv("TIKTOK_APP_KEY")
        self.app_secret = os.getenv("TIKTOK_APP_SECRET")
        self.access_token = os.getenv("TIKTOK_ACCESS_TOKEN")
        self.api_version = "v2"
        self.base_url = f"https://open.tiktokapis.com/{self.api_version}"

    @property
    def id(self) -> str:
        return "tiktok"

    @property
    def display_name(self) -> str:
        return "TikTok"

    def is_enabled(self) -> bool:
        return bool(self.app_key and self.app_secret and self.access_token)

    def list_supported_platforms(self) -> List[str]:
        return ["tiktok"]

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """
        Fetch TikTok video metrics using Content Posting API.

        Metrics available:
        - video_views
        - likes
        - comments
        - shares
        - reach
        """
        if not self.is_enabled():
            return []

        if variant.platform != "tiktok":
            return []

        try:
            return await self._fetch_video_metrics(variant)
        except Exception as e:
            logger.error(f"Error fetching TikTok metrics for {variant.content_id}: {e}")
            return []

    async def _fetch_video_metrics(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """Fetch video analytics from TikTok API"""
        video_id = variant.content_id

        async with httpx.AsyncClient() as client:
            # Fetch video info using TikTok Content Posting API
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            # Query video data
            response = await client.post(
                f"{self.base_url}/video/query/",
                headers=headers,
                json={
                    "filters": {
                        "video_ids": [video_id]
                    }
                }
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("data", {}).get("videos"):
                logger.warning(f"No video data found for {video_id}")
                return []

            video_data = data["data"]["videos"][0]

            return [PlatformMetricSnapshot(
                platform="tiktok",
                platform_post_id=video_id,
                url=video_data.get("share_url"),
                snapshot_at=datetime.now(),
                views=video_data.get("view_count"),
                likes=video_data.get("like_count"),
                comments=video_data.get("comment_count"),
                shares=video_data.get("share_count"),
                raw_payload=video_data
            )]

    async def publish_variant(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Publish video to TikTok using Content Posting API.

        Process:
        1. Initialize upload (get upload URL)
        2. Upload video file
        3. Publish video with metadata

        Args:
            variant: Content variant with media_url and description

        Returns:
            Dict with 'platform_post_id' and 'url'
        """
        if not self.is_enabled():
            raise RuntimeError("TikTok connector is not enabled. Set TIKTOK_ACCESS_TOKEN, TIKTOK_APP_KEY, TIKTOK_APP_SECRET.")

        if not variant.media_url:
            raise ValueError("TikTok posts require media_url")

        try:
            return await self._publish_video(variant)
        except Exception as e:
            logger.error(f"Error publishing to TikTok: {e}")
            raise RuntimeError(f"Failed to publish to TikTok: {e}")

    async def _publish_video(self, variant: ContentVariant) -> Dict[str, str]:
        """Upload and publish video to TikTok"""

        async with httpx.AsyncClient(timeout=300.0) as client:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            # Step 1: Initialize video upload
            init_response = await client.post(
                f"{self.base_url}/post/publish/inbox/video/init/",
                headers=headers,
                json={
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "video_size": 0,  # Size will be determined during upload
                        "chunk_size": 10485760,  # 10MB chunks
                        "total_chunk_count": 1
                    }
                }
            )
            init_response.raise_for_status()
            init_data = init_response.json()

            upload_url = init_data["data"]["upload_url"]
            publish_id = init_data["data"]["publish_id"]

            # Step 2: Upload video file
            # Download video from media_url and upload to TikTok
            video_response = await client.get(variant.media_url)
            video_response.raise_for_status()
            video_bytes = video_response.content

            upload_headers = {
                "Content-Type": "video/mp4",
                "Content-Length": str(len(video_bytes))
            }

            upload_response = await client.put(
                upload_url,
                headers=upload_headers,
                content=video_bytes
            )
            upload_response.raise_for_status()

            # Step 3: Publish video
            publish_response = await client.post(
                f"{self.base_url}/post/publish/video/init/",
                headers=headers,
                json={
                    "post_info": {
                        "title": variant.description or "",
                        "privacy_level": "PUBLIC_TO_EVERYONE",
                        "disable_duet": False,
                        "disable_comment": False,
                        "disable_stitch": False,
                        "video_cover_timestamp_ms": 1000
                    },
                    "source_info": {
                        "source": "FILE_UPLOAD",
                        "publish_id": publish_id
                    }
                }
            )
            publish_response.raise_for_status()
            publish_data = publish_response.json()

            return {
                "platform_post_id": publish_data["data"]["publish_id"],
                "url": f"https://www.tiktok.com/@user/video/{publish_data['data']['publish_id']}",
                "status": "published"
            }
