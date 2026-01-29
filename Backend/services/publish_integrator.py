"""
Publish Integrator Service (ARCH-003)
=====================================
Bridges content analysis → multi-platform publishing.

Workflow:
1. Subscribe to PUBLISH_REQUESTED from orchestrator
2. Extract AI-generated analysis (titles, descriptions, hashtags)
3. Auto-fill platform-specific metadata
4. Determine target accounts per platform
5. Trigger Blotato publishing for each account

This implements the critical "Content Analyzer → Publisher Integration"
that auto-injects AI metadata into publish payloads.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from services.event_bus import EventBus, Event, Topics

logger = logging.getLogger(__name__)


class PublishIntegrator:
    """
    ARCH-003: Content Analyzer → Publisher Integration

    Auto-injects AI-generated titles, descriptions, and hashtags
    into multi-platform publish workflows.
    """

    _instance: Optional['PublishIntegrator'] = None

    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or EventBus.get_instance()

        # Load Blotato service for account lookups
        try:
            from services.blotato_service import BlotatoService
            self.blotato_service = BlotatoService.get_instance()
        except Exception as e:
            logger.warning(f"⚠️ Blotato Service not available: {e}")
            self.blotato_service = None

        self._setup_subscriptions()
        logger.info("🔗 PublishIntegrator initialized (ARCH-003)")

    @classmethod
    def get_instance(cls, event_bus: Optional[EventBus] = None) -> 'PublishIntegrator':
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance

    def _setup_subscriptions(self) -> None:
        """Subscribe to orchestrator publish requests."""
        self.event_bus.subscribe(Topics.PUBLISH_REQUESTED, self._handle_publish_request)
        logger.info("📫 PublishIntegrator subscribed to PUBLISH_REQUESTED")

    async def _handle_publish_request(self, event: Event) -> None:
        """
        Handle PUBLISH_REQUESTED from orchestrator.

        Expected payload:
        {
            "pipeline_id": str,
            "platform": str,  # tiktok, instagram, youtube, twitter, etc.
            "video_path": str,
            "analysis": {
                "title_tiktok": str,
                "title_instagram": str,
                "title_youtube": str,
                "description": str,
                "hashtags": List[str],
                "hook": str,
                "cta": str
            },
            "offer_url": Optional[str]
        }
        """
        try:
            payload = event.payload
            pipeline_id = payload.get("pipeline_id")
            platform = payload.get("platform")
            video_path = payload.get("video_path")
            analysis = payload.get("analysis", {})
            offer_url = payload.get("offer_url")

            logger.info(f"🔗 [ARCH-003] Processing publish for {platform} (pipeline={pipeline_id})")

            # Get platform-specific metadata from analysis
            caption = self._generate_caption(platform, analysis, offer_url)
            title = self._get_platform_title(platform, analysis)

            # Get target accounts for this platform
            accounts = self._get_platform_accounts(platform)

            if not accounts:
                logger.warning(f"⚠️ No accounts found for platform: {platform}")
                await self._emit_publish_failed(pipeline_id, platform, "No accounts configured")
                return

            logger.info(f"📤 [ARCH-003] Publishing to {len(accounts)} {platform} accounts")

            # Publish to each account
            # For now, we'll publish to the first account per platform
            # TODO: Add logic for round-robin or all-accounts publishing
            account = accounts[0]

            # Upload video to media service (if needed)
            # For MVP, we assume video_path is accessible by Blotato
            media_id = await self._upload_or_reference_video(video_path, platform)

            # Trigger Blotato publish
            await self.event_bus.publish(
                "blotato.publish.requested",
                {
                    "pipeline_id": pipeline_id,
                    "media_id": media_id,
                    "account_id": account.id,
                    "platform": platform,
                    "caption": caption,
                    "title": title,
                    "video_path": video_path,
                    "analysis": analysis
                },
                correlation_id=event.correlation_id,
                source="publish_integrator"
            )

            logger.info(f"✅ [ARCH-003] Triggered publish for {platform} account {account.username}")

        except Exception as e:
            logger.error(f"❌ [ARCH-003] Error handling publish request: {e}")
            await self._emit_publish_failed(
                payload.get("pipeline_id"),
                payload.get("platform"),
                str(e)
            )

    def _generate_caption(
        self,
        platform: str,
        analysis: Dict[str, Any],
        offer_url: Optional[str] = None
    ) -> str:
        """
        Generate platform-optimized caption from AI analysis.

        Uses AI-generated hook, description, hashtags, and CTA.
        """
        hook = analysis.get("hook", "")
        description = analysis.get("description", "")
        cta = analysis.get("cta", "Follow for more!")
        hashtags = analysis.get("hashtags", [])

        # Platform-specific formatting
        if platform in ["tiktok", "instagram", "threads"]:
            # Short-form: Hook + Hashtags
            hashtag_str = " ".join([f"#{tag}" for tag in hashtags[:10]])
            caption = f"{hook}\n\n{hashtag_str}"

            if offer_url:
                caption += f"\n\n🔗 {offer_url}"

        elif platform == "youtube":
            # Long-form: Description + Hashtags + CTA
            hashtag_str = " ".join([f"#{tag}" for tag in hashtags[:3]])
            caption = f"{description}\n\n{cta}\n\n{hashtag_str}"

            if offer_url:
                caption += f"\n\n🔗 {offer_url}"

        elif platform == "twitter":
            # Thread-style: Hook + Link
            caption = hook[:260]  # Twitter char limit
            if offer_url:
                caption += f"\n\n{offer_url}"

        elif platform in ["linkedin", "facebook"]:
            # Professional: Description + CTA
            caption = f"{description}\n\n{cta}"
            if offer_url:
                caption += f"\n\nLearn more: {offer_url}"

        else:
            # Fallback: Simple format
            caption = f"{hook}\n\n{description}"
            if offer_url:
                caption += f"\n\n{offer_url}"

        return caption

    def _get_platform_title(self, platform: str, analysis: Dict[str, Any]) -> str:
        """Get platform-specific title from analysis."""
        title_map = {
            "tiktok": analysis.get("title_tiktok"),
            "instagram": analysis.get("title_instagram"),
            "youtube": analysis.get("title_youtube"),
        }

        return title_map.get(platform) or analysis.get("hook", "")[:100]

    def _get_platform_accounts(self, platform: str) -> List[Any]:
        """Get all accounts for a platform."""
        if not self.blotato_service:
            return []

        return self.blotato_service.get_accounts_by_platform(platform)

    async def _upload_or_reference_video(
        self,
        video_path: str,
        platform: str
    ) -> str:
        """
        Upload video to media service or return reference.

        For MVP, we return the video_path as media_id.
        In production, this would:
        1. Upload to cloud storage (S3/R2)
        2. Return CDN URL or media ID
        3. Let Blotato download from URL
        """
        # TODO: Implement actual video upload
        # For now, return video_path as media_id
        return video_path

    async def _emit_publish_failed(
        self,
        pipeline_id: str,
        platform: str,
        error: str
    ) -> None:
        """Emit publish failed event."""
        await self.event_bus.publish(
            "blotato.publish.failed",
            {
                "pipeline_id": pipeline_id,
                "platform": platform,
                "error": error
            },
            source="publish_integrator"
        )


# Singleton accessor
def get_publish_integrator(event_bus: Optional[EventBus] = None) -> PublishIntegrator:
    """Get or create PublishIntegrator instance."""
    return PublishIntegrator.get_instance(event_bus)
