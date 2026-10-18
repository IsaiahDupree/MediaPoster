"""
ACTP → MediaPoster Lite Publisher
===================================
Routes ACTP organic post requests through the MediaPoster Lite queue.

Flow:
  1. ACTP generates a creative video (Sora/Remotion/etc.)
  2. This publisher enqueues it in MPLite with ACTP metadata
  3. Local machine polls MPLite /api/queue/next
  4. Local machine claims the item, runs Safari automation / Blotato upload
  5. Local machine calls complete/fail with the resulting post URL
  6. MPLite webhook (or ACTP polling) picks up the result
  7. ACTP records the OrganicPost and begins collecting metrics

This decouples ACTP from the local machine — the web dashboard controls
what gets published, and the local machine executes it natively.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .mplite_client import MPLiteClient, MPLiteError, MPLITE_PLATFORMS
from .models import Creative, OrganicPost, Platform

logger = logging.getLogger(__name__)

# Map ACTP Platform enum values → MPLite platform strings
PLATFORM_MAP: Dict[str, str] = {
    "tiktok": "tiktok",
    "youtube_shorts": "youtube",
    "instagram_reels": "instagram",
    "twitter": "twitter",
    "threads": "threads",
    # Ad platforms are not routed through MPLite organic queue
}

# Map MPLite platform strings back to ACTP Platform enum values
REVERSE_PLATFORM_MAP: Dict[str, str] = {v: k for k, v in PLATFORM_MAP.items()}


def _mplite_platform(actp_platform: str) -> Optional[str]:
    """Convert an ACTP platform string to an MPLite platform string."""
    return PLATFORM_MAP.get(actp_platform.lower())


class MPLitePublisher:
    """
    Publishes ACTP creatives through the MediaPoster Lite queue.

    Replaces direct platform API calls for organic posting — instead of
    calling TikTok/YouTube APIs directly, we enqueue the video in MPLite
    and let the local machine handle the actual upload via Safari automation.
    """

    def __init__(
        self,
        db_client=None,
        mplite_url: Optional[str] = None,
        mplite_key: Optional[str] = None,
    ):
        self.db = db_client
        self._mplite_url = mplite_url or os.getenv("MPLITE_URL")
        self._mplite_key = mplite_key or os.getenv("MPLITE_KEY")

    def is_configured(self) -> bool:
        """Return True if MPLite credentials are set."""
        return bool(self._mplite_key)

    def supports_platform(self, platform: str) -> bool:
        """Return True if the platform can be routed through MPLite."""
        return _mplite_platform(platform) is not None

    # ─── Enqueue for organic publishing ───────────────────

    async def enqueue_organic_post(
        self,
        creative: Creative,
        platform: str,
        account_id: str,
        caption: str,
        hashtags: Optional[List[str]] = None,
        priority: int = 5,
        scheduled_for: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Enqueue a creative for organic publishing via MPLite.

        Returns a dict with:
          - mplite_item_id: the MPLite queue item ID
          - platform: the MPLite platform string
          - status: 'queued'
          - enqueued_at: ISO timestamp
        """
        mplite_platform = _mplite_platform(platform)
        if not mplite_platform:
            raise MPLiteError(
                f"Platform '{platform}' cannot be routed through MPLite. "
                f"Supported ACTP platforms: {sorted(PLATFORM_MAP.keys())}"
            )

        video_url = self._resolve_video_url(creative)
        if not video_url:
            raise MPLiteError(
                f"Creative {creative.id} has no video_url — cannot enqueue in MPLite"
            )

        title = f"ACTP | {creative.angle or ''} | {creative.hook[:40] if creative.hook else ''}".strip(" |")

        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            item = await client.enqueue_actp_creative(
                creative_id=creative.id,
                video_url=video_url,
                platform=mplite_platform,
                account_id=account_id,
                caption=caption,
                hashtags=hashtags or [],
                priority=priority,
                campaign_id=creative.campaign_id,
                round_id=creative.round_id,
            )
            if scheduled_for:
                await client.reschedule(item["id"], scheduled_for)

        result = {
            "mplite_item_id": item["id"],
            "platform": mplite_platform,
            "actp_platform": platform,
            "status": "queued",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "creative_id": creative.id,
            "video_url": video_url,
            "priority": priority,
        }

        logger.info(
            f"[ACTP:MPLite] Enqueued creative {creative.id} → "
            f"{mplite_platform} (item={item['id']}, priority={priority})"
        )
        return result

    async def enqueue_batch(
        self,
        creatives: List[Creative],
        platform: str,
        account_id: str,
        caption_template: str = "",
        hashtags: Optional[List[str]] = None,
        base_priority: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Enqueue multiple creatives for organic publishing.
        Priority increments by 1 per creative so they publish in order.
        """
        results = []
        for i, creative in enumerate(creatives):
            caption = caption_template or (creative.hook or "")
            try:
                result = await self.enqueue_organic_post(
                    creative=creative,
                    platform=platform,
                    account_id=account_id,
                    caption=caption,
                    hashtags=hashtags,
                    priority=min(base_priority + i, 10),
                )
                results.append({"success": True, "creative_id": creative.id, **result})
            except MPLiteError as e:
                logger.error(f"[ACTP:MPLite] Failed to enqueue {creative.id}: {e}")
                results.append({"success": False, "creative_id": creative.id, "error": str(e)})
        return results

    # ─── Poll for completion ───────────────────────────────

    async def poll_item_status(self, mplite_item_id: str) -> Dict[str, Any]:
        """
        Check the current status of an enqueued item.

        Returns the MPLite item dict with status, platform_url, etc.
        Call this to detect when a local machine has completed publishing.
        """
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            item = await client.get_item(mplite_item_id)
            return item.get("item", item)

    async def poll_pending_for_campaign(
        self, campaign_id: str, platform: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all MPLite queue items that belong to this ACTP campaign.
        Filters by actp_campaign_id in item metadata.
        """
        mplite_platform = _mplite_platform(platform) if platform else None

        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            result = await client.list_queue(
                platform=mplite_platform,
                limit=100,
            )
            items = result.get("items", [])

        return [
            item for item in items
            if (item.get("metadata") or {}).get("actp_campaign_id") == campaign_id
        ]

    # ─── Build OrganicPost from completed MPLite item ─────

    def build_organic_post_from_item(
        self, mplite_item: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Convert a completed MPLite queue item into an ACTP OrganicPost dict.

        Returns None if the item is not yet published or missing ACTP metadata.
        """
        if mplite_item.get("status") != "published":
            return None

        metadata = mplite_item.get("metadata") or {}
        creative_id = metadata.get("actp_creative_id")
        if not creative_id:
            return None

        mplite_platform = mplite_item.get("platform", "")
        actp_platform = REVERSE_PLATFORM_MAP.get(mplite_platform, mplite_platform)

        return {
            "creative_id": creative_id,
            "platform": actp_platform,
            "post_id": mplite_item.get("platform_post_id") or mplite_item["id"],
            "post_url": mplite_item.get("platform_url") or "",
            "status": "published",
            "posted_at": mplite_item.get("published_at") or datetime.now(timezone.utc).isoformat(),
            "metrics": {},
            "mplite_item_id": mplite_item["id"],
        }

    # ─── Status checks ────────────────────────────────────

    async def get_queue_status(self) -> Dict[str, Any]:
        """Get MPLite queue status — global state, today's counts, queue summary."""
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            return await client.get_status()

    async def can_publish_to(self, platform: str) -> Dict[str, Any]:
        """Check if MPLite can currently publish to a platform."""
        mplite_platform = _mplite_platform(platform)
        if not mplite_platform:
            return {
                "can_publish": False,
                "reason": f"Platform '{platform}' not supported by MPLite",
            }
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            return await client.can_publish(mplite_platform)

    async def get_daily_summary(self) -> Dict[str, Any]:
        """Get today's publish counts by platform."""
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            return await client.get_daily_summary()

    async def get_publish_history(
        self, platform: Optional[str] = None, days: int = 7
    ) -> Dict[str, Any]:
        """Get recent publish history, optionally filtered by platform."""
        mplite_platform = _mplite_platform(platform) if platform else None
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            return await client.get_history(platform=mplite_platform, days=days)

    # ─── Control ──────────────────────────────────────────

    async def pause_publishing(self) -> Dict[str, Any]:
        """Pause all MPLite publishing (e.g. during off-hours or emergencies)."""
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            result = await client.pause()
            logger.warning("[ACTP:MPLite] Publishing PAUSED globally")
            return result

    async def resume_publishing(self) -> Dict[str, Any]:
        """Resume MPLite publishing."""
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            result = await client.resume()
            logger.info("[ACTP:MPLite] Publishing RESUMED globally")
            return result

    async def cancel_item(self, mplite_item_id: str) -> Dict[str, Any]:
        """Cancel a queued item (e.g. if the creative was eliminated before publishing)."""
        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            result = await client.cancel(mplite_item_id)
            logger.info(f"[ACTP:MPLite] Cancelled item {mplite_item_id}")
            return result

    async def cancel_campaign_items(self, campaign_id: str) -> Dict[str, Any]:
        """Cancel all pending MPLite items for a campaign (e.g. campaign paused/deleted)."""
        items = await self.poll_pending_for_campaign(campaign_id)
        cancelled = []
        errors = []

        async with MPLiteClient(
            base_url=self._mplite_url, api_key=self._mplite_key
        ) as client:
            for item in items:
                if item.get("status") in ("queued", "scheduled", "paused"):
                    try:
                        await client.cancel(item["id"])
                        cancelled.append(item["id"])
                    except MPLiteError as e:
                        errors.append({"item_id": item["id"], "error": str(e)})

        logger.info(
            f"[ACTP:MPLite] Cancelled {len(cancelled)} items for campaign {campaign_id}"
        )
        return {
            "campaign_id": campaign_id,
            "cancelled": cancelled,
            "errors": errors,
            "total_cancelled": len(cancelled),
        }

    # ─── Internal helpers ─────────────────────────────────

    def _resolve_video_url(self, creative: Creative) -> Optional[str]:
        """Extract the video URL from a creative's generation metadata."""
        meta = creative.generation_metadata or {}
        # Check common locations where the video URL might be stored
        for key in ("video_url", "output_url", "file_url", "url"):
            url = meta.get(key)
            if url:
                return url
        # Fall back to result dict
        result = meta.get("result") or {}
        if isinstance(result, dict):
            for key in ("video_url", "output_url", "url"):
                url = result.get(key)
                if url:
                    return url
        return None
