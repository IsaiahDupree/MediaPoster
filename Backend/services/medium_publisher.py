"""
YTP-004: Medium Blog Publisher
Publishes blog posts to Medium via their API.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class MediumPost:
    """A Medium blog post."""
    post_id: Optional[str] = None
    title: str = ""
    content: str = ""
    content_format: str = "markdown"
    tags: List[str] = field(default_factory=list)
    canonical_url: Optional[str] = None
    publish_status: str = "draft"  # draft, public, unlisted
    url: Optional[str] = None
    published_at: Optional[str] = None


class MediumPublisher:
    """
    Publishes blog posts to Medium.

    Features:
    - Draft and public publishing
    - Tag management
    - Canonical URL support
    - Publication publishing
    """

    def __init__(
        self,
        api_token: Optional[str] = None,
    ):
        self.api_token = api_token or os.getenv("MEDIUM_API_TOKEN", "")
        self.base_url = "https://api.medium.com/v1"
        self._user_id: Optional[str] = None

    async def get_user(self) -> Dict[str, Any]:
        """Get authenticated user info."""
        try:
            import aiohttp
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/me", headers=headers
                ) as resp:
                    data = await resp.json()
                    user = data.get("data", {})
                    self._user_id = user.get("id")
                    return user
        except Exception as e:
            logger.error("Failed to get Medium user: %s", e)
            return {}

    async def publish(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        publish_status: str = "draft",
        content_format: str = "markdown",
        canonical_url: Optional[str] = None,
    ) -> MediumPost:
        """
        Publish a post to Medium.

        Args:
            title: Post title
            content: Post content (markdown or HTML)
            tags: Up to 5 tags
            publish_status: draft, public, or unlisted
            content_format: markdown or html
            canonical_url: Original source URL

        Returns:
            MediumPost with published info
        """
        if not self._user_id:
            await self.get_user()

        if not self._user_id:
            raise ValueError("Could not determine Medium user ID")

        post_data = {
            "title": title,
            "contentFormat": content_format,
            "content": content,
            "tags": (tags or [])[:5],
            "publishStatus": publish_status,
        }
        if canonical_url:
            post_data["canonicalUrl"] = canonical_url

        try:
            import aiohttp
            headers = {
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/users/{self._user_id}/posts",
                    headers=headers,
                    json=post_data,
                ) as resp:
                    result = await resp.json()
                    post = result.get("data", {})

                    return MediumPost(
                        post_id=post.get("id"),
                        title=title,
                        content=content,
                        content_format=content_format,
                        tags=tags or [],
                        canonical_url=canonical_url,
                        publish_status=publish_status,
                        url=post.get("url"),
                        published_at=datetime.now(timezone.utc).isoformat(),
                    )

        except ImportError:
            logger.warning("aiohttp not available for Medium publishing")
            return MediumPost(title=title, content=content, tags=tags or [])
        except Exception as e:
            logger.error("Failed to publish to Medium: %s", e)
            raise
