"""
Channel Router Service (HITL-007 / BM-011)
==========================================
Routes content to multiple platforms simultaneously, selecting Safari automation
or Blotato API based on availability and user preference.

Key Features:
- Multi-platform targeting (all 9 Blotato platforms)
- Safari/Blotato selection logic per platform
- Fallback handling (Safari -> Blotato and vice versa)
- Per-platform formatting (caption limits, hashtag styles)
- Optional HITL approval gate
- Published URL tracking per platform
- EventBus integration for real-time progress

Topics Emitted:
    - route.started           - Routing job started
    - route.platform.started  - Single platform publish started
    - route.platform.completed - Single platform publish completed
    - route.platform.failed   - Single platform publish failed
    - route.completed         - All platforms finished
    - route.approval.pending  - Awaiting HITL approval

Usage:
    router = ChannelRouter.get_instance()

    result = await router.route_content(
        video_path="/path/to/video.mp4",
        platforms=["twitter", "tiktok", "instagram"],
        analysis={"hook": "Amazing content", "hashtags": ["viral"]},
        offer_url="https://example.com/offer",
        approval_required=False,
    )
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
from dataclasses import dataclass, field
from enum import Enum

# Import event bus
try:
    from services.event_bus import EventBus, Event
    from services.event_bus.topics import Topics
except ImportError:
    EventBus = None
    Event = None
    Topics = None

logger = logging.getLogger(__name__)


# =============================================================================
# Constants
# =============================================================================

# All supported platforms (from BlotatoService)
ALL_PLATFORMS = [
    "tiktok", "instagram", "youtube", "twitter",
    "threads", "pinterest", "linkedin", "facebook", "bluesky",
]

# Platforms supported by Safari automation
SAFARI_SUPPORTED_PLATFORMS = {"twitter"}

# Platforms supported by Blotato API
BLOTATO_SUPPORTED_PLATFORMS = set(ALL_PLATFORMS)

# Per-platform formatting limits
PLATFORM_LIMITS = {
    "twitter": {
        "caption_max_length": 280,
        "hashtag_max_count": 3,
        "hashtag_style": "inline",         # hashtags inline with text
        "supports_video": True,
        "description": "Twitter/X - Short-form text with optional media",
    },
    "tiktok": {
        "caption_max_length": 2200,
        "hashtag_max_count": 10,
        "hashtag_style": "appended",       # hashtags appended at end
        "supports_video": True,
        "description": "TikTok - Short-form video with caption",
    },
    "instagram": {
        "caption_max_length": 2200,
        "hashtag_max_count": 30,
        "hashtag_style": "comment_or_caption",  # hashtags in first comment or caption
        "supports_video": True,
        "description": "Instagram Reels - Video with rich caption",
    },
    "youtube": {
        "caption_max_length": 5000,
        "hashtag_max_count": 15,
        "hashtag_style": "description",    # hashtags in description
        "supports_video": True,
        "description": "YouTube Shorts - Short-form vertical video",
    },
    "threads": {
        "caption_max_length": 500,
        "hashtag_max_count": 10,
        "hashtag_style": "inline",
        "supports_video": True,
        "description": "Threads - Text-first with optional media",
    },
    "pinterest": {
        "caption_max_length": 500,
        "hashtag_max_count": 20,
        "hashtag_style": "appended",
        "supports_video": True,
        "description": "Pinterest - Visual discovery pin",
    },
    "linkedin": {
        "caption_max_length": 3000,
        "hashtag_max_count": 5,
        "hashtag_style": "appended",
        "supports_video": True,
        "description": "LinkedIn - Professional content",
    },
    "facebook": {
        "caption_max_length": 63206,
        "hashtag_max_count": 10,
        "hashtag_style": "appended",
        "supports_video": True,
        "description": "Facebook - Social media post",
    },
    "bluesky": {
        "caption_max_length": 300,
        "hashtag_max_count": 5,
        "hashtag_style": "inline",
        "supports_video": True,
        "description": "Bluesky - Decentralized social",
    },
}


class PublishMethod(str, Enum):
    """Method used to publish content to a platform."""
    SAFARI = "safari"
    BLOTATO = "blotato"


class RoutePreference(str, Enum):
    """User preference for routing method."""
    SAFARI_PREFERRED = "safari_preferred"     # Try Safari first, fallback to Blotato
    BLOTATO_PREFERRED = "blotato_preferred"   # Try Blotato first, fallback to Safari
    SAFARI_ONLY = "safari_only"               # Safari only, no fallback
    BLOTATO_ONLY = "blotato_only"             # Blotato only, no fallback
    AUTO = "auto"                             # System decides best method


@dataclass
class PlatformResult:
    """Result of publishing to a single platform."""
    platform: str
    success: bool
    method: PublishMethod = PublishMethod.BLOTATO
    published_url: Optional[str] = None
    post_id: Optional[str] = None
    error: Optional[str] = None
    fallback_used: bool = False
    caption_used: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "success": self.success,
            "method": self.method.value,
            "published_url": self.published_url,
            "post_id": self.post_id,
            "error": self.error,
            "fallback_used": self.fallback_used,
            "caption_used": self.caption_used,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class RouteResult:
    """Result of routing content to multiple platforms."""
    route_id: str
    status: str = "pending"
    platforms_requested: List[str] = field(default_factory=list)
    platform_results: Dict[str, PlatformResult] = field(default_factory=dict)
    published_urls: Dict[str, str] = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    approval_required: bool = False
    approval_status: Optional[str] = None

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.platform_results.values() if r.success)

    @property
    def failure_count(self) -> int:
        return sum(1 for r in self.platform_results.values() if not r.success)

    @property
    def all_completed(self) -> bool:
        return len(self.platform_results) == len(self.platforms_requested)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "route_id": self.route_id,
            "status": self.status,
            "platforms_requested": self.platforms_requested,
            "platform_results": {
                k: v.to_dict() for k, v in self.platform_results.items()
            },
            "published_urls": self.published_urls,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "approval_required": self.approval_required,
            "approval_status": self.approval_status,
        }


class ChannelRouter:
    """
    Channel Router Service (HITL-007 / BM-011)

    Routes content to multiple platforms simultaneously.
    Selects Safari automation or Blotato API based on availability
    and user preference, with automatic fallback.

    Singleton Pattern:
        router = ChannelRouter.get_instance()
    """

    _instance: Optional["ChannelRouter"] = None

    def __init__(self, event_bus: Optional[Any] = None):
        self._event_bus = event_bus or (EventBus.get_instance() if EventBus else None)
        self._route_preference = RoutePreference.AUTO
        self._active_routes: Dict[str, RouteResult] = {}
        self._completed_routes: Dict[str, RouteResult] = {}

        # Lazy-loaded service references
        self._blotato_service = None
        self._safari_session_manager = None
        self._safari_twitter_poster = None
        self._approval_queue = None

        if self._event_bus:
            self._setup_subscriptions()

        logger.info("ChannelRouter initialized")

    @classmethod
    def get_instance(cls, event_bus: Optional[Any] = None) -> "ChannelRouter":
        """Get or create the singleton ChannelRouter instance."""
        if cls._instance is None:
            cls._instance = cls(event_bus)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        cls._instance = None

    # =========================================================================
    # Service References (lazy-loaded)
    # =========================================================================

    def _get_blotato_service(self):
        """Lazy-load BlotatoService."""
        if self._blotato_service is None:
            try:
                from services.blotato_service import BlotatoService
                self._blotato_service = BlotatoService.get_instance()
            except Exception as e:
                logger.warning(f"BlotatoService not available: {e}")
        return self._blotato_service

    def _get_safari_session_manager(self):
        """Lazy-load SafariSessionManager."""
        if self._safari_session_manager is None:
            try:
                from automation.safari_session_manager import SafariSessionManager
                self._safari_session_manager = SafariSessionManager()
            except Exception as e:
                logger.warning(f"SafariSessionManager not available: {e}")
        return self._safari_session_manager

    def _get_safari_twitter_poster(self):
        """Lazy-load SafariTwitterPoster."""
        if self._safari_twitter_poster is None:
            try:
                from automation.safari_twitter_poster import SafariTwitterPoster
                self._safari_twitter_poster = SafariTwitterPoster()
            except Exception as e:
                logger.warning(f"SafariTwitterPoster not available: {e}")
        return self._safari_twitter_poster

    # =========================================================================
    # EventBus Integration
    # =========================================================================

    def _setup_subscriptions(self) -> None:
        """Set up event bus subscriptions."""
        if not self._event_bus:
            return
        logger.info("[ChannelRouter] Subscribed to event bus topics")

    async def _emit_event(self, topic: str, payload: Dict[str, Any],
                          correlation_id: Optional[str] = None) -> None:
        """Emit an event to the event bus."""
        if self._event_bus:
            await self._event_bus.publish(
                topic, payload,
                correlation_id=correlation_id,
                source="ChannelRouter",
            )

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_route_preference(self, preference: RoutePreference) -> None:
        """Set the global routing preference."""
        self._route_preference = preference
        logger.info(f"[ChannelRouter] Route preference set to: {preference.value}")

    def get_route_preference(self) -> RoutePreference:
        """Get the current routing preference."""
        return self._route_preference

    # =========================================================================
    # Core Routing
    # =========================================================================

    async def route_content(
        self,
        video_path: str,
        platforms: List[str],
        analysis: Optional[Dict[str, Any]] = None,
        offer_url: Optional[str] = None,
        approval_required: bool = False,
        caption_override: Optional[str] = None,
        preference: Optional[RoutePreference] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RouteResult:
        """
        Route content to multiple platforms.

        Args:
            video_path: Path to the video file to publish.
            platforms: List of platform names (e.g., ["twitter", "tiktok"]).
            analysis: AI analysis metadata (hook, hashtags, description, etc.).
            offer_url: Optional offer URL to include in captions.
            approval_required: If True, submit to approval queue first.
            caption_override: If set, use this caption for all platforms.
            preference: Override the global routing preference for this request.
            metadata: Additional metadata for the routing job.

        Returns:
            RouteResult with per-platform results and published URLs.
        """
        route_id = f"route-{uuid4().hex[:12]}"
        correlation_id = str(uuid4())
        effective_preference = preference or self._route_preference

        # Validate platforms
        valid_platforms = [p for p in platforms if p in ALL_PLATFORMS]
        if not valid_platforms:
            logger.error(f"[{route_id}] No valid platforms in: {platforms}")
            return RouteResult(
                route_id=route_id,
                status="failed",
                platforms_requested=platforms,
            )

        result = RouteResult(
            route_id=route_id,
            status="started",
            platforms_requested=valid_platforms,
            started_at=datetime.now(timezone.utc).isoformat(),
            approval_required=approval_required,
        )
        self._active_routes[route_id] = result

        # Emit route.started
        await self._emit_event("route.started", {
            "route_id": route_id,
            "platforms": valid_platforms,
            "video_path": video_path,
            "approval_required": approval_required,
        }, correlation_id=correlation_id)

        logger.info(
            f"[{route_id}] Routing to {len(valid_platforms)} platforms: "
            f"{', '.join(valid_platforms)}"
        )

        # HITL Approval Gate
        if approval_required:
            result.approval_status = "pending"
            result.status = "awaiting_approval"

            await self._emit_event("route.approval.pending", {
                "route_id": route_id,
                "platforms": valid_platforms,
                "video_path": video_path,
                "analysis": analysis or {},
            }, correlation_id=correlation_id)

            await self._submit_to_approval_queue(
                route_id=route_id,
                video_path=video_path,
                platforms=valid_platforms,
                analysis=analysis,
                offer_url=offer_url,
                metadata=metadata,
            )

            logger.info(f"[{route_id}] Submitted to approval queue")
            return result

        # Route to each platform
        for platform in valid_platforms:
            platform_result = await self._route_to_platform(
                route_id=route_id,
                platform=platform,
                video_path=video_path,
                analysis=analysis or {},
                offer_url=offer_url,
                caption_override=caption_override,
                preference=effective_preference,
                correlation_id=correlation_id,
            )
            result.platform_results[platform] = platform_result

            if platform_result.success and platform_result.published_url:
                result.published_urls[platform] = platform_result.published_url

        # Finalize
        result.status = "completed"
        result.completed_at = datetime.now(timezone.utc).isoformat()

        # Emit route.completed
        await self._emit_event("route.completed", {
            "route_id": route_id,
            "success_count": result.success_count,
            "failure_count": result.failure_count,
            "published_urls": result.published_urls,
        }, correlation_id=correlation_id)

        # Move to completed
        self._completed_routes[route_id] = result
        self._active_routes.pop(route_id, None)

        logger.info(
            f"[{route_id}] Routing complete: "
            f"{result.success_count}/{len(valid_platforms)} succeeded"
        )

        return result

    # =========================================================================
    # Per-Platform Routing
    # =========================================================================

    async def _route_to_platform(
        self,
        route_id: str,
        platform: str,
        video_path: str,
        analysis: Dict[str, Any],
        offer_url: Optional[str],
        caption_override: Optional[str],
        preference: RoutePreference,
        correlation_id: str,
    ) -> PlatformResult:
        """Route content to a single platform with method selection and fallback."""
        started_at = datetime.now(timezone.utc).isoformat()

        # Emit route.platform.started
        await self._emit_event("route.platform.started", {
            "route_id": route_id,
            "platform": platform,
        }, correlation_id=correlation_id)

        # Format content for this platform
        formatted_caption = self._format_for_platform(
            platform=platform,
            analysis=analysis,
            offer_url=offer_url,
            caption_override=caption_override,
        )

        # Determine publish method (primary + fallback)
        primary_method, fallback_method = self._select_method(platform, preference)

        logger.info(
            f"[{route_id}] {platform}: primary={primary_method.value}, "
            f"fallback={fallback_method.value if fallback_method else 'none'}"
        )

        # Try primary method
        platform_result = await self._publish_via_method(
            method=primary_method,
            platform=platform,
            video_path=video_path,
            caption=formatted_caption,
            analysis=analysis,
            offer_url=offer_url,
        )
        platform_result.started_at = started_at
        platform_result.caption_used = formatted_caption

        # If primary failed and we have a fallback, try it
        if not platform_result.success and fallback_method is not None:
            logger.warning(
                f"[{route_id}] {platform}: primary method {primary_method.value} "
                f"failed ({platform_result.error}), trying fallback "
                f"{fallback_method.value}"
            )
            fallback_result = await self._publish_via_method(
                method=fallback_method,
                platform=platform,
                video_path=video_path,
                caption=formatted_caption,
                analysis=analysis,
                offer_url=offer_url,
            )
            if fallback_result.success:
                platform_result = fallback_result
                platform_result.fallback_used = True
                platform_result.started_at = started_at
                platform_result.caption_used = formatted_caption

        platform_result.completed_at = datetime.now(timezone.utc).isoformat()

        # Emit route.platform.completed
        event_topic = (
            "route.platform.completed" if platform_result.success
            else "route.platform.failed"
        )
        await self._emit_event(event_topic, {
            "route_id": route_id,
            "platform": platform,
            "success": platform_result.success,
            "method": platform_result.method.value,
            "published_url": platform_result.published_url,
            "fallback_used": platform_result.fallback_used,
            "error": platform_result.error,
        }, correlation_id=correlation_id)

        return platform_result

    # =========================================================================
    # Method Selection Logic
    # =========================================================================

    def _select_method(
        self, platform: str, preference: RoutePreference
    ) -> tuple:
        """
        Select the primary and fallback publish methods for a platform.

        Returns:
            (primary_method, fallback_method) - fallback may be None.
        """
        safari_available = platform in SAFARI_SUPPORTED_PLATFORMS
        blotato_available = platform in BLOTATO_SUPPORTED_PLATFORMS

        # Check Safari session health if Safari is an option
        if safari_available:
            safari_healthy = self._check_safari_health(platform)
        else:
            safari_healthy = False

        # Determine methods based on preference
        if preference == RoutePreference.SAFARI_ONLY:
            if safari_available:
                return (PublishMethod.SAFARI, None)
            else:
                # Safari doesn't support this platform, use Blotato as only option
                return (PublishMethod.BLOTATO, None)

        elif preference == RoutePreference.BLOTATO_ONLY:
            return (PublishMethod.BLOTATO, None)

        elif preference == RoutePreference.SAFARI_PREFERRED:
            if safari_available and safari_healthy:
                return (PublishMethod.SAFARI, PublishMethod.BLOTATO)
            else:
                return (PublishMethod.BLOTATO, None)

        elif preference == RoutePreference.BLOTATO_PREFERRED:
            if blotato_available:
                primary = PublishMethod.BLOTATO
                fallback = PublishMethod.SAFARI if safari_available and safari_healthy else None
                return (primary, fallback)
            elif safari_available:
                return (PublishMethod.SAFARI, None)
            else:
                return (PublishMethod.BLOTATO, None)

        else:  # AUTO
            # Auto: Use Blotato for all platforms (most reliable),
            # but prefer Safari for Twitter if session is healthy
            if platform == "twitter" and safari_healthy:
                return (PublishMethod.SAFARI, PublishMethod.BLOTATO)
            else:
                fallback = (
                    PublishMethod.SAFARI
                    if safari_available and safari_healthy
                    else None
                )
                return (PublishMethod.BLOTATO, fallback)

    def _check_safari_health(self, platform: str) -> bool:
        """
        Check if Safari session is healthy for the given platform.

        Returns True if Safari automation is available and logged in.
        """
        session_manager = self._get_safari_session_manager()
        if session_manager is None:
            return False

        try:
            from automation.safari_session_manager import Platform as SafariPlatform
            platform_map = {
                "twitter": SafariPlatform.TWITTER,
                "tiktok": SafariPlatform.TIKTOK,
                "instagram": SafariPlatform.INSTAGRAM,
                "youtube": SafariPlatform.YOUTUBE,
                "threads": SafariPlatform.THREADS,
            }
            safari_platform = platform_map.get(platform)
            if safari_platform is None:
                return False

            state = session_manager.sessions.get(safari_platform)
            if state and state.is_logged_in:
                return True
        except Exception as e:
            logger.debug(f"Safari health check failed for {platform}: {e}")

        return False

    # =========================================================================
    # Publishing via Method
    # =========================================================================

    async def _publish_via_method(
        self,
        method: PublishMethod,
        platform: str,
        video_path: str,
        caption: str,
        analysis: Dict[str, Any],
        offer_url: Optional[str],
    ) -> PlatformResult:
        """Publish content using the specified method."""
        if method == PublishMethod.SAFARI:
            return await self._publish_via_safari(platform, video_path, caption)
        else:
            return await self._publish_via_blotato(platform, video_path, caption, offer_url)

    async def _publish_via_safari(
        self,
        platform: str,
        video_path: str,
        caption: str,
    ) -> PlatformResult:
        """Publish content via Safari browser automation."""
        try:
            if platform == "twitter":
                poster = self._get_safari_twitter_poster()
                if poster is None:
                    return PlatformResult(
                        platform=platform,
                        success=False,
                        method=PublishMethod.SAFARI,
                        error="SafariTwitterPoster not available",
                    )

                result = poster.post_tweet(
                    text=caption,
                    media_paths=[video_path] if video_path else None,
                )

                if result.get("success"):
                    return PlatformResult(
                        platform=platform,
                        success=True,
                        method=PublishMethod.SAFARI,
                        published_url=result.get("url"),
                        post_id=result.get("tweet_id"),
                    )
                else:
                    return PlatformResult(
                        platform=platform,
                        success=False,
                        method=PublishMethod.SAFARI,
                        error=result.get("error", "Safari post failed"),
                    )
            else:
                return PlatformResult(
                    platform=platform,
                    success=False,
                    method=PublishMethod.SAFARI,
                    error=f"Safari automation not supported for {platform}",
                )

        except Exception as e:
            logger.error(f"Safari publish failed for {platform}: {e}")
            return PlatformResult(
                platform=platform,
                success=False,
                method=PublishMethod.SAFARI,
                error=str(e),
            )

    async def _publish_via_blotato(
        self,
        platform: str,
        video_path: str,
        caption: str,
        offer_url: Optional[str],
    ) -> PlatformResult:
        """Publish content via Blotato API."""
        try:
            blotato = self._get_blotato_service()
            if blotato is None:
                return PlatformResult(
                    platform=platform,
                    success=False,
                    method=PublishMethod.BLOTATO,
                    error="BlotatoService not available",
                )

            # Find an account for this platform
            accounts = blotato.get_accounts_by_platform(platform)
            if not accounts:
                return PlatformResult(
                    platform=platform,
                    success=False,
                    method=PublishMethod.BLOTATO,
                    error=f"No Blotato account for {platform}",
                )

            # Use first active account
            account = next((a for a in accounts if a.is_active), accounts[0])

            result = await blotato.publish_content(
                media_id=video_path,
                account_id=account.id,
                caption=caption,
            )

            if result.get("success"):
                published_url = None
                post_id = None
                api_result = result.get("result", {})
                if isinstance(api_result, dict):
                    published_url = api_result.get("url") or api_result.get("post_url")
                    post_id = api_result.get("id") or api_result.get("post_id")

                return PlatformResult(
                    platform=platform,
                    success=True,
                    method=PublishMethod.BLOTATO,
                    published_url=published_url,
                    post_id=str(post_id) if post_id else None,
                )
            else:
                return PlatformResult(
                    platform=platform,
                    success=False,
                    method=PublishMethod.BLOTATO,
                    error=result.get("error", "Blotato publish failed"),
                )

        except Exception as e:
            logger.error(f"Blotato publish failed for {platform}: {e}")
            return PlatformResult(
                platform=platform,
                success=False,
                method=PublishMethod.BLOTATO,
                error=str(e),
            )

    # =========================================================================
    # Per-Platform Formatting
    # =========================================================================

    def format_for_platform(
        self,
        platform: str,
        analysis: Dict[str, Any],
        offer_url: Optional[str] = None,
        caption_override: Optional[str] = None,
    ) -> str:
        """
        Public interface for formatting content for a specific platform.

        Delegates to the internal _format_for_platform method.
        """
        return self._format_for_platform(platform, analysis, offer_url, caption_override)

    def _format_for_platform(
        self,
        platform: str,
        analysis: Dict[str, Any],
        offer_url: Optional[str] = None,
        caption_override: Optional[str] = None,
    ) -> str:
        """
        Format content caption for a specific platform.

        Applies platform-specific limits for caption length, hashtag count,
        and hashtag formatting style.

        Args:
            platform: Target platform name.
            analysis: AI analysis dict with hook, description, hashtags, etc.
            offer_url: Optional URL to append.
            caption_override: If set, use this as the base caption.

        Returns:
            Formatted caption string.
        """
        limits = PLATFORM_LIMITS.get(platform, PLATFORM_LIMITS.get("facebook", {}))
        max_length = limits.get("caption_max_length", 2200)
        max_hashtags = limits.get("hashtag_max_count", 10)
        hashtag_style = limits.get("hashtag_style", "appended")

        # Build base caption
        if caption_override:
            base_caption = caption_override
        else:
            hook = analysis.get("hook") or analysis.get("detected_hook") or ""
            description = analysis.get("description") or analysis.get("viral_analysis") or ""

            if platform == "twitter":
                # Twitter: Hook only, very concise
                base_caption = hook or description[:200]
            elif platform == "tiktok":
                # TikTok: Short hook
                base_caption = hook or description[:300]
            elif platform == "youtube":
                # YouTube: Full description with SEO keywords
                base_caption = f"{hook}\n\n{description}" if hook and description else (hook or description)
            elif platform == "linkedin":
                # LinkedIn: Professional tone
                base_caption = f"{hook}\n\n{description}" if hook and description else (hook or description)
            elif platform in ("threads", "bluesky"):
                # Short-form
                base_caption = hook or description[:400]
            else:
                # Default: Hook + description
                base_caption = f"{hook}\n\n{description}" if hook and description else (hook or description)

        # Build hashtags
        raw_hashtags = analysis.get("hashtags", [])[:max_hashtags]
        formatted_hashtags = []
        for tag in raw_hashtags:
            tag = tag.strip().lstrip("#")
            if tag:
                formatted_hashtags.append(f"#{tag}")

        hashtag_string = " ".join(formatted_hashtags)

        # Assemble caption based on hashtag style
        if hashtag_style == "inline" and formatted_hashtags:
            # Inline: hashtags woven into or right after text
            caption = f"{base_caption} {hashtag_string}".strip()
        elif hashtag_style == "appended" and formatted_hashtags:
            # Appended: hashtags on new line after caption
            caption = f"{base_caption}\n\n{hashtag_string}".strip()
        elif hashtag_style == "description" and formatted_hashtags:
            # Description: hashtags in description area
            caption = f"{base_caption}\n\n{hashtag_string}".strip()
        elif hashtag_style == "comment_or_caption" and formatted_hashtags:
            # Instagram: hashtags at end of caption
            caption = f"{base_caption}\n\n{hashtag_string}".strip()
        else:
            caption = base_caption.strip()

        # Append offer URL if provided
        if offer_url:
            url_addition = f"\n\n{offer_url}"
            if len(caption) + len(url_addition) <= max_length:
                caption = f"{caption}{url_addition}"

        # Enforce max length
        if len(caption) > max_length:
            caption = caption[:max_length - 3] + "..."

        return caption

    # =========================================================================
    # Approval Queue Integration
    # =========================================================================

    async def _submit_to_approval_queue(
        self,
        route_id: str,
        video_path: str,
        platforms: List[str],
        analysis: Optional[Dict[str, Any]],
        offer_url: Optional[str],
        metadata: Optional[Dict[str, Any]],
    ) -> None:
        """Submit a routing job to the HITL approval queue."""
        try:
            from services.approval_queue import ApprovalQueue, ApprovalItem, ApprovalPriority

            queue = ApprovalQueue()
            await queue.add_item(
                content_id=route_id,
                content_type="channel_route",
                content_data={
                    "video_path": video_path,
                    "platforms": platforms,
                    "analysis": analysis or {},
                    "offer_url": offer_url,
                    "metadata": metadata or {},
                },
                priority=ApprovalPriority.HIGH,
            )
        except ImportError:
            logger.warning("[ChannelRouter] ApprovalQueue not available, skipping HITL gate")
        except Exception as e:
            logger.error(f"[ChannelRouter] Failed to submit to approval queue: {e}")

    async def handle_approval_response(
        self,
        route_id: str,
        approved: bool,
        feedback: str = "",
    ) -> Optional[RouteResult]:
        """
        Handle an approval/rejection response from the HITL queue.

        If approved, proceeds to route content.
        If rejected, marks the route as rejected.

        Args:
            route_id: The route ID that was submitted for approval.
            approved: Whether the content was approved.
            feedback: Optional reviewer feedback.

        Returns:
            Updated RouteResult, or None if route not found.
        """
        result = self._active_routes.get(route_id)
        if not result:
            logger.warning(f"[ChannelRouter] Route {route_id} not found for approval response")
            return None

        if approved:
            result.approval_status = "approved"
            logger.info(f"[{route_id}] Approved - proceeding with routing")
            # In a full implementation, we would re-trigger routing here
            # using stored video_path, platforms, analysis, etc.
        else:
            result.approval_status = "rejected"
            result.status = "rejected"
            logger.info(f"[{route_id}] Rejected: {feedback}")
            self._completed_routes[route_id] = result
            self._active_routes.pop(route_id, None)

        return result

    # =========================================================================
    # Status and Tracking
    # =========================================================================

    def get_route_status(self, route_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of a route."""
        result = self._active_routes.get(route_id) or self._completed_routes.get(route_id)
        if result:
            return result.to_dict()
        return None

    def get_published_urls(self, route_id: str) -> Dict[str, str]:
        """Get all published URLs for a route."""
        result = self._active_routes.get(route_id) or self._completed_routes.get(route_id)
        if result:
            return dict(result.published_urls)
        return {}

    def list_active_routes(self) -> List[Dict[str, Any]]:
        """List all active (in-progress) routes."""
        return [r.to_dict() for r in self._active_routes.values()]

    def list_completed_routes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List recently completed routes."""
        routes = list(self._completed_routes.values())
        routes.sort(key=lambda r: r.completed_at or "", reverse=True)
        return [r.to_dict() for r in routes[:limit]]

    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics."""
        all_results = list(self._completed_routes.values())
        total_success = sum(r.success_count for r in all_results)
        total_failure = sum(r.failure_count for r in all_results)

        return {
            "active_routes": len(self._active_routes),
            "completed_routes": len(self._completed_routes),
            "total_platforms_published": total_success,
            "total_platforms_failed": total_failure,
            "route_preference": self._route_preference.value,
        }


# =============================================================================
# Module-level Convenience Functions
# =============================================================================

def get_channel_router(event_bus: Optional[Any] = None) -> ChannelRouter:
    """Get the singleton ChannelRouter instance."""
    return ChannelRouter.get_instance(event_bus)
