import os
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from ..base import SourceAdapter, PlatformMetricSnapshot, ContentVariant

class YouTubeConnector(SourceAdapter):
    """
    YouTube Connector Implementation

    Uses YouTube Data API v3 for metrics and uploading.

    Features:
    - Upload videos to YouTube
    - Fetch video statistics (views, likes, comments, watch time)
    - Support for Shorts and regular videos
    """

    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        self.refresh_token = os.getenv("YOUTUBE_REFRESH_TOKEN")
        self.access_token = None
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.upload_url = "https://www.googleapis.com/upload/youtube/v3/videos"

    @property
    def id(self) -> str:
        return "youtube"

    @property
    def display_name(self) -> str:
        return "YouTube"

    def is_enabled(self) -> bool:
        # Can work with just API key for read-only, or OAuth for uploads
        return bool(self.api_key or (self.client_id and self.client_secret and self.refresh_token))

    def list_supported_platforms(self) -> List[str]:
        return ["youtube"]

    async def _get_access_token(self) -> str:
        """Get or refresh OAuth access token"""
        if self.access_token:
            return self.access_token

        if not (self.client_id and self.client_secret and self.refresh_token):
            raise RuntimeError("YouTube OAuth credentials not configured")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            data = response.json()
            self.access_token = data["access_token"]
            return self.access_token

    async def fetch_metrics_for_variant(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """
        Fetch YouTube video statistics.

        Metrics available:
        - viewCount
        - likeCount
        - commentCount
        - favoriteCount (saved to playlists)
        """
        if not self.is_enabled():
            return []

        if variant.platform != "youtube":
            return []

        try:
            return await self._fetch_video_metrics(variant)
        except Exception as e:
            logger.error(f"Error fetching YouTube metrics for {variant.content_id}: {e}")
            return []

    async def _fetch_video_metrics(self, variant: ContentVariant) -> List[PlatformMetricSnapshot]:
        """Fetch video statistics from YouTube Data API"""
        video_id = variant.content_id

        async with httpx.AsyncClient() as client:
            params = {
                "part": "statistics,contentDetails,snippet",
                "id": video_id,
                "key": self.api_key
            }

            response = await client.get(
                f"{self.base_url}/videos",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            if not data.get("items"):
                logger.warning(f"No video data found for {video_id}")
                return []

            video_data = data["items"][0]
            stats = video_data.get("statistics", {})
            snippet = video_data.get("snippet", {})
            content_details = video_data.get("contentDetails", {})

            return [PlatformMetricSnapshot(
                platform="youtube",
                platform_post_id=video_id,
                url=f"https://www.youtube.com/watch?v={video_id}",
                snapshot_at=datetime.now(),
                views=int(stats.get("viewCount", 0)),
                likes=int(stats.get("likeCount", 0)),
                comments=int(stats.get("commentCount", 0)),
                saves=int(stats.get("favoriteCount", 0)),
                raw_payload={
                    "statistics": stats,
                    "snippet": snippet,
                    "contentDetails": content_details
                }
            )]

    async def publish_variant(self, variant: ContentVariant) -> Dict[str, str]:
        """
        Upload video to YouTube using YouTube Data API v3.

        Process:
        1. Get OAuth access token
        2. Initialize resumable upload
        3. Upload video file
        4. Set video metadata

        Args:
            variant: Content variant with media_url, title, and description

        Returns:
            Dict with 'platform_post_id' and 'url'
        """
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise RuntimeError("YouTube connector is not configured for uploads. Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.")

        if not variant.media_url:
            raise ValueError("YouTube uploads require media_url")

        try:
            return await self._upload_video(variant)
        except Exception as e:
            logger.error(f"Error uploading to YouTube: {e}")
            raise RuntimeError(f"Failed to upload to YouTube: {e}")

    async def _upload_video(self, variant: ContentVariant) -> Dict[str, str]:
        """Upload video to YouTube"""
        access_token = await self._get_access_token()

        async with httpx.AsyncClient(timeout=600.0) as client:
            # Download video file
            video_response = await client.get(variant.media_url)
            video_response.raise_for_status()
            video_bytes = video_response.content

            # Prepare metadata
            metadata = {
                "snippet": {
                    "title": variant.title or "Untitled Video",
                    "description": variant.description or "",
                    "categoryId": "22"  # People & Blogs
                },
                "status": {
                    "privacyStatus": "public",
                    "selfDeclaredMadeForKids": False
                }
            }

            # Upload video
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Type": "video/*",
                "X-Upload-Content-Length": str(len(video_bytes))
            }

            # Step 1: Initialize resumable upload
            init_response = await client.post(
                f"{self.upload_url}?uploadType=resumable&part=snippet,status",
                headers=headers,
                json=metadata
            )
            init_response.raise_for_status()
            upload_url = init_response.headers["Location"]

            # Step 2: Upload video bytes
            upload_headers = {
                "Content-Type": "video/*",
                "Content-Length": str(len(video_bytes))
            }

            upload_response = await client.put(
                upload_url,
                headers=upload_headers,
                content=video_bytes
            )
            upload_response.raise_for_status()
            upload_data = upload_response.json()

            video_id = upload_data["id"]

            return {
                "platform_post_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "status": "published"
            }

    # =========================================================================
    # COMMENT MANAGEMENT (ADAPT-010)
    # =========================================================================

    async def fetch_comments(
        self,
        video_id: str,
        max_results: int = 100,
        order: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """
        Fetch comments for a YouTube video.

        Args:
            video_id: YouTube video ID
            max_results: Maximum number of comments to fetch (default: 100, max: 100)
            order: Sort order - 'time' (newest first) or 'relevance' (default)

        Returns:
            List of comment dictionaries with author, text, timestamp, etc.

        Raises:
            RuntimeError: If API is not configured
        """
        if not self.api_key:
            raise RuntimeError("YouTube API key not configured")

        logger.info(f"Fetching comments for video {video_id}...")

        async with httpx.AsyncClient() as client:
            params = {
                "part": "snippet,replies",
                "videoId": video_id,
                "maxResults": min(max_results, 100),  # API limit
                "order": order,
                "key": self.api_key,
                "textFormat": "plainText"
            }

            response = await client.get(
                f"{self.base_url}/commentThreads",
                params=params
            )
            response.raise_for_status()
            data = response.json()

            comments = []
            for item in data.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]

                comment_data = {
                    "comment_id": item["id"],
                    "video_id": video_id,
                    "author": snippet["authorDisplayName"],
                    "author_channel_id": snippet.get("authorChannelId", {}).get("value"),
                    "text": snippet["textDisplay"],
                    "like_count": snippet["likeCount"],
                    "published_at": snippet["publishedAt"],
                    "updated_at": snippet.get("updatedAt"),
                    "reply_count": item["snippet"]["totalReplyCount"],
                    "has_replies": item["snippet"]["totalReplyCount"] > 0
                }

                # Include top-level replies if available
                if "replies" in item:
                    comment_data["replies"] = [
                        {
                            "reply_id": reply["id"],
                            "author": reply["snippet"]["authorDisplayName"],
                            "text": reply["snippet"]["textDisplay"],
                            "like_count": reply["snippet"]["likeCount"],
                            "published_at": reply["snippet"]["publishedAt"]
                        }
                        for reply in item["replies"]["comments"]
                    ]

                comments.append(comment_data)

            logger.info(f"Fetched {len(comments)} comments for video {video_id}")
            return comments

    async def post_comment(
        self,
        video_id: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Post a top-level comment on a YouTube video.

        Args:
            video_id: YouTube video ID
            text: Comment text

        Returns:
            Dict with comment information including comment_id

        Raises:
            RuntimeError: If OAuth credentials not configured
        """
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise RuntimeError(
                "YouTube OAuth credentials required to post comments. "
                "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN."
            )

        logger.info(f"Posting comment on video {video_id}...")

        access_token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            body = {
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {
                        "snippet": {
                            "textOriginal": text
                        }
                    }
                }
            }

            response = await client.post(
                f"{self.base_url}/commentThreads?part=snippet",
                headers=headers,
                json=body
            )
            response.raise_for_status()
            data = response.json()

            comment_id = data["id"]
            snippet = data["snippet"]["topLevelComment"]["snippet"]

            result = {
                "comment_id": comment_id,
                "video_id": video_id,
                "text": snippet["textDisplay"],
                "author": snippet["authorDisplayName"],
                "published_at": snippet["publishedAt"],
                "status": "published"
            }

            logger.success(f"✓ Comment posted on video {video_id}: {comment_id}")
            return result

    async def reply_to_comment(
        self,
        comment_id: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Reply to an existing comment.

        Args:
            comment_id: Parent comment ID to reply to
            text: Reply text

        Returns:
            Dict with reply information

        Raises:
            RuntimeError: If OAuth credentials not configured
        """
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise RuntimeError(
                "YouTube OAuth credentials required to reply to comments. "
                "Set YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN."
            )

        logger.info(f"Replying to comment {comment_id}...")

        access_token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            body = {
                "snippet": {
                    "parentId": comment_id,
                    "textOriginal": text
                }
            }

            response = await client.post(
                f"{self.base_url}/comments?part=snippet",
                headers=headers,
                json=body
            )
            response.raise_for_status()
            data = response.json()

            reply_id = data["id"]
            snippet = data["snippet"]

            result = {
                "reply_id": reply_id,
                "parent_comment_id": comment_id,
                "text": snippet["textDisplay"],
                "author": snippet["authorDisplayName"],
                "published_at": snippet["publishedAt"],
                "status": "published"
            }

            logger.success(f"✓ Reply posted to comment {comment_id}: {reply_id}")
            return result

    async def delete_comment(self, comment_id: str) -> bool:
        """
        Delete a comment (must be your own comment).

        Args:
            comment_id: Comment or reply ID to delete

        Returns:
            True if successful

        Raises:
            RuntimeError: If OAuth credentials not configured
        """
        if not (self.client_id and self.client_secret and self.refresh_token):
            raise RuntimeError("YouTube OAuth credentials required to delete comments.")

        logger.info(f"Deleting comment {comment_id}...")

        access_token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {access_token}"
            }

            response = await client.delete(
                f"{self.base_url}/comments?id={comment_id}",
                headers=headers
            )
            response.raise_for_status()

            logger.success(f"✓ Comment deleted: {comment_id}")
            return True
