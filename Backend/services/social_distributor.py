"""
YTP-005: Multi-Platform Social Distribution
Distributes content from the YouTube pipeline to multiple social platforms.
"""
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class DistributionTarget:
    """A target platform for content distribution."""
    platform: str  # twitter, instagram, tiktok, linkedin, threads
    account_id: Optional[str] = None
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DistributionResult:
    """Result of distributing content to a platform."""
    platform: str
    success: bool
    post_id: Optional[str] = None
    post_url: Optional[str] = None
    error: Optional[str] = None
    distributed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SocialDistributor:
    """
    Distributes content across multiple social platforms.

    Takes content from the YouTube pipeline (hooks, summaries, quotes)
    and formats/publishes to each configured platform.
    """

    def __init__(self):
        self._targets: List[DistributionTarget] = []

    def add_target(
        self,
        platform: str,
        account_id: Optional[str] = None,
        **config,
    ) -> None:
        """Add a distribution target."""
        self._targets.append(DistributionTarget(
            platform=platform,
            account_id=account_id,
            config=config,
        ))

    def remove_target(self, platform: str) -> bool:
        """Remove a distribution target."""
        initial = len(self._targets)
        self._targets = [t for t in self._targets if t.platform != platform]
        return len(self._targets) < initial

    async def distribute(
        self,
        content: Dict[str, Any],
        platforms: Optional[List[str]] = None,
    ) -> List[DistributionResult]:
        """
        Distribute content to configured platforms.

        Args:
            content: Content dict with keys: title, summary, hooks, hashtags, media_url
            platforms: Optional list of platforms to target (default: all enabled)

        Returns:
            List of DistributionResult for each platform
        """
        results = []
        targets = self._targets

        if platforms:
            targets = [t for t in targets if t.platform in platforms and t.enabled]

        for target in targets:
            try:
                result = await self._distribute_to_platform(target, content)
                results.append(result)
            except Exception as e:
                logger.error("Distribution to %s failed: %s", target.platform, e)
                results.append(DistributionResult(
                    platform=target.platform,
                    success=False,
                    error=str(e),
                ))

        return results

    async def _distribute_to_platform(
        self,
        target: DistributionTarget,
        content: Dict[str, Any],
    ) -> DistributionResult:
        """Format and distribute content to a specific platform."""
        platform = target.platform

        # Format content for platform
        formatted = self._format_for_platform(content, platform)

        logger.info("Distributing to %s: %s", platform, formatted.get("text", "")[:50])

        # In production, this would call platform-specific APIs
        # For now, we return a success result with the formatted content
        return DistributionResult(
            platform=platform,
            success=True,
        )

    def _format_for_platform(
        self,
        content: Dict[str, Any],
        platform: str,
    ) -> Dict[str, Any]:
        """Format content for a specific platform's requirements."""
        hooks = content.get("social_hooks", [])
        hashtags = content.get("hashtags", [])
        title = content.get("title", "")

        if platform == "twitter":
            # 280 char limit
            text = hooks[0] if hooks else title
            tags = " ".join(f"#{t}" for t in hashtags[:3])
            return {"text": f"{text[:240]}\n\n{tags}"}

        elif platform == "linkedin":
            # Longer format
            summary = content.get("summary", "")
            return {"text": f"{title}\n\n{summary}\n\n{' '.join(f'#{t}' for t in hashtags[:5])}"}

        elif platform == "instagram":
            # Caption format
            text = hooks[0] if hooks else title
            tags = " ".join(f"#{t}" for t in hashtags[:10])
            return {"text": f"{text}\n\n{tags}"}

        else:
            return {"text": hooks[0] if hooks else title}

    def get_targets(self) -> List[DistributionTarget]:
        """Get all configured targets."""
        return self._targets
