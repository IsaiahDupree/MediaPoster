"""
MediaPoster Lite Client
========================
Python HTTP client for the MediaPoster Lite web API.
Enables ACTP to enqueue organic posts and ad creatives through the
cloud-deployed MPLite queue, which local machines poll to execute
Safari automations, Blotato uploads, and other native publishing tasks.

Live dashboard: https://mediaposter-lite-isaiahduprees-projects.vercel.app
API base:       https://mediaposter-lite-isaiahduprees-projects.vercel.app/api
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

MPLITE_BASE_URL = os.getenv(
    "MPLITE_URL",
    "https://mediaposter-lite-isaiahduprees-projects.vercel.app",
)
MPLITE_API_KEY = os.getenv("MPLITE_KEY", "")

# Platforms supported by MPLite
MPLITE_PLATFORMS = {"tiktok", "instagram", "youtube", "twitter", "threads"}


class MPLiteError(Exception):
    """Raised when the MPLite API returns an error."""

    def __init__(self, message: str, status_code: int = 0, code: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class MPLiteClient:
    """
    Async HTTP client for the MediaPoster Lite API.

    Usage:
        async with MPLiteClient() as client:
            status = await client.get_status()
            item_id = await client.enqueue(...)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 15.0,
    ):
        self._base = (base_url or MPLITE_BASE_URL).rstrip("/")
        self._key = api_key or MPLITE_API_KEY
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    # ─── Context manager ──────────────────────────────────

    async def __aenter__(self) -> "MPLiteClient":
        self._client = httpx.AsyncClient(
            base_url=self._base,
            headers={
                "Authorization": f"Bearer {self._key}",
                "Content-Type": "application/json",
            },
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, *_):
        if self._client:
            await self._client.aclose()
            self._client = None

    # ─── Internal request helper ──────────────────────────

    async def _request(
        self,
        method: str,
        path: str,
        body: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not self._client:
            raise MPLiteError("Client not started — use async with MPLiteClient()")

        resp = await self._client.request(
            method,
            f"/api{path}",
            json=body,
            params=params,
        )

        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}

        if not resp.is_success:
            msg = data.get("message") or data.get("error") or f"HTTP {resp.status_code}"
            code = data.get("error", "")
            raise MPLiteError(msg, resp.status_code, code)

        return data.get("data", data)

    # ─── Health / Status ──────────────────────────────────

    async def health(self) -> Dict[str, Any]:
        """Check MPLite API health (no auth required)."""
        if not self._client:
            raise MPLiteError("Client not started")
        resp = await self._client.get("/api/health")
        return resp.json()

    async def get_status(self) -> Dict[str, Any]:
        """Get full publishing status: global state, today's counts, queue summary."""
        return await self._request("GET", "/status")

    async def get_config(self) -> Dict[str, Any]:
        """Get current publishing config."""
        return await self._request("GET", "/config")

    async def can_publish(self, platform: str) -> Dict[str, Any]:
        """Check if a platform can publish right now (rate limits, posting window)."""
        return await self._request("GET", f"/can-publish/{platform}")

    # ─── Global controls ──────────────────────────────────

    async def pause(self) -> Dict[str, Any]:
        """Pause all publishing globally."""
        return await self._request("POST", "/config/pause")

    async def resume(self) -> Dict[str, Any]:
        """Resume publishing globally."""
        return await self._request("POST", "/config/resume")

    # ─── Queue management ─────────────────────────────────

    async def list_queue(
        self,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List queue items with optional filters."""
        params: Dict[str, str] = {"limit": str(limit)}
        if platform:
            params["platform"] = platform
        if status:
            params["status"] = status
        return await self._request("GET", "/queue", params=params)

    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics (counts by status/platform)."""
        return await self._request("GET", "/queue/stats")

    async def enqueue(
        self,
        video_url: str,
        platform: str,
        account_id: str,
        caption: str = "",
        title: str = "",
        account_username: str = "",
        hashtags: Optional[List[str]] = None,
        priority: int = 5,
        scheduled_for: Optional[str] = None,
        thumbnail_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: str = "api",
    ) -> Dict[str, Any]:
        """
        Add a video to the MPLite publishing queue.

        Returns the created queue item dict including its `id`.
        The local machine polls /api/queue/next to pick this up and
        execute the actual Safari automation / Blotato upload.
        """
        if platform not in MPLITE_PLATFORMS:
            raise MPLiteError(
                f"Platform '{platform}' not supported by MPLite. "
                f"Supported: {sorted(MPLITE_PLATFORMS)}"
            )

        body: Dict[str, Any] = {
            "video_url": video_url,
            "platform": platform,
            "account_id": account_id,
            "account_username": account_username,
            "caption": caption,
            "title": title,
            "hashtags": hashtags or [],
            "priority": priority,
            "metadata": metadata or {},
            "source": source,
        }
        if scheduled_for:
            body["scheduled_for"] = scheduled_for
        if thumbnail_url:
            body["thumbnail_url"] = thumbnail_url

        result = await self._request("POST", "/queue", body=body)
        item = result.get("item", result)
        logger.info(
            f"[ACTP:MPLite] Enqueued {platform} item {item.get('id')} "
            f"(priority={priority}, source={source})"
        )
        return item

    async def get_next(self, platform: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get the next item ready to publish (used by local machine polling)."""
        params: Dict[str, str] = {}
        if platform:
            params["platform"] = platform
        try:
            result = await self._request("GET", "/queue/next", params=params)
            return result.get("item", result)
        except MPLiteError as e:
            if e.status_code == 404:
                return None
            raise

    async def get_item(self, item_id: str) -> Dict[str, Any]:
        """Get a specific queue item by ID."""
        return await self._request("GET", f"/queue/{item_id}")

    async def claim(self, item_id: str) -> Dict[str, Any]:
        """Mark an item as currently being published (status → publishing)."""
        result = await self._request("POST", f"/queue/{item_id}/claim")
        logger.info(f"[ACTP:MPLite] Claimed item {item_id}")
        return result

    async def complete(
        self,
        item_id: str,
        platform_url: Optional[str] = None,
        platform_post_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark an item as successfully published."""
        body: Dict[str, Any] = {}
        if platform_url:
            body["platform_url"] = platform_url
        if platform_post_id:
            body["platform_post_id"] = platform_post_id
        result = await self._request("POST", f"/queue/{item_id}/complete", body=body)
        logger.info(f"[ACTP:MPLite] Completed item {item_id} → {platform_url}")
        return result

    async def fail(self, item_id: str, error_message: str) -> Dict[str, Any]:
        """Mark an item as failed (auto-retries up to max_retries)."""
        result = await self._request(
            "POST", f"/queue/{item_id}/fail", body={"error_message": error_message}
        )
        logger.warning(f"[ACTP:MPLite] Failed item {item_id}: {error_message}")
        return result

    async def cancel(self, item_id: str) -> Dict[str, Any]:
        """Cancel a queued item."""
        return await self._request("POST", f"/queue/{item_id}/cancel")

    async def retry(self, item_id: str) -> Dict[str, Any]:
        """Retry a failed item."""
        return await self._request("POST", f"/queue/{item_id}/retry")

    async def reschedule(self, item_id: str, scheduled_for: str) -> Dict[str, Any]:
        """Reschedule an item to a new datetime (ISO 8601)."""
        return await self._request(
            "POST", f"/queue/{item_id}/reschedule", body={"scheduled_for": scheduled_for}
        )

    async def set_priority(self, item_id: str, priority: int) -> Dict[str, Any]:
        """Change the priority of a queued item (1=highest, 10=lowest)."""
        return await self._request(
            "POST", f"/queue/{item_id}/priority", body={"priority": priority}
        )

    async def pause_item(self, item_id: str) -> Dict[str, Any]:
        """Pause a specific queue item."""
        return await self._request("POST", f"/queue/{item_id}/pause")

    async def resume_item(self, item_id: str) -> Dict[str, Any]:
        """Resume a paused queue item."""
        return await self._request("POST", f"/queue/{item_id}/resume")

    # ─── History ──────────────────────────────────────────

    async def get_history(
        self,
        platform: Optional[str] = None,
        days: int = 7,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Get published history."""
        params: Dict[str, str] = {"days": str(days), "limit": str(limit)}
        if platform:
            params["platform"] = platform
        return await self._request("GET", "/history", params=params)

    async def get_daily_summary(self) -> Dict[str, Any]:
        """Get today's publish counts by platform."""
        return await self._request("GET", "/daily-summary")

    # ─── Platforms ────────────────────────────────────────

    async def list_platforms(self) -> Dict[str, Any]:
        """List all configured platforms and their status."""
        return await self._request("GET", "/platforms")

    async def toggle_platform(self, platform: str, enabled: bool) -> Dict[str, Any]:
        """Enable or disable a platform."""
        return await self._request("POST", f"/platforms/{platform}/toggle", body={"is_enabled": enabled})

    # ─── Activity ─────────────────────────────────────────

    async def get_activity(self, limit: int = 50) -> Dict[str, Any]:
        """Get recent activity log."""
        return await self._request("GET", "/activity", params={"limit": str(limit)})

    # ─── API Keys ─────────────────────────────────────────

    async def list_keys(self) -> Dict[str, Any]:
        """List all API keys."""
        return await self._request("GET", "/keys")

    async def create_key(
        self,
        name: str,
        permissions: Optional[List[str]] = None,
        expires_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new API key."""
        body: Dict[str, Any] = {
            "name": name,
            "permissions": permissions or ["*"],
        }
        if expires_at:
            body["expires_at"] = expires_at
        return await self._request("POST", "/keys", body=body)

    # ─── Webhooks ─────────────────────────────────────────

    async def list_webhooks(self) -> Dict[str, Any]:
        """List registered webhooks."""
        return await self._request("GET", "/webhooks")

    async def create_webhook(
        self,
        name: str,
        url: str,
        events: Optional[List[str]] = None,
        secret: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register a new inbound webhook."""
        body: Dict[str, Any] = {
            "name": name,
            "url": url,
            "events": events or ["*"],
        }
        if secret:
            body["secret"] = secret
        return await self._request("POST", "/webhooks", body=body)

    async def delete_webhook(self, webhook_id: str) -> Dict[str, Any]:
        """Delete a webhook registration."""
        return await self._request("DELETE", f"/webhooks/{webhook_id}")

    # ─── Convenience helpers ──────────────────────────────

    def is_configured(self) -> bool:
        """Return True if an API key is set."""
        return bool(self._key)

    async def enqueue_actp_creative(
        self,
        creative_id: str,
        video_url: str,
        platform: str,
        account_id: str,
        caption: str,
        hashtags: Optional[List[str]] = None,
        priority: int = 5,
        campaign_id: Optional[str] = None,
        round_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue an ACTP creative for organic publishing via MPLite.

        Attaches ACTP metadata so the local machine can report back
        which creative_id was published, enabling ACTP to record the
        OrganicPost and start collecting metrics.
        """
        return await self.enqueue(
            video_url=video_url,
            platform=platform,
            account_id=account_id,
            caption=caption,
            hashtags=hashtags,
            priority=priority,
            metadata={
                "actp_creative_id": creative_id,
                "actp_campaign_id": campaign_id or "",
                "actp_round_id": round_id or "",
                "source": "actp",
            },
            source="api",
        )
