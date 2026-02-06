"""
Video Provider Adapters
=======================
Unified interface for video generation providers (Sora, Runway, Kling, etc.)

Usage:
    from services.video_providers import get_video_provider, ProviderName

    provider = get_video_provider(ProviderName.SORA)
    generation = await provider.create_clip(input)

Note:
    MockVideoProvider is available for testing only.
    Import from services.video_providers.mock_provider directly in tests.
"""

import os
from typing import Optional

from .base import (
    VideoProviderAdapter,
    ProviderName,
    ClipStatus,
    AssetKind,
    CreateClipInput,
    RemixClipInput,
    ProviderGeneration,
    ProviderError,
)


class NotConfiguredError(RuntimeError):
    """Raised when a video provider is requested but not configured."""
    pass


def get_video_provider(
    provider_name: Optional[ProviderName] = None
) -> VideoProviderAdapter:
    """
    Get configured video provider adapter.

    Args:
        provider_name: Override provider (sora, runway, kling)

    Returns:
        Configured VideoProviderAdapter instance

    Raises:
        NotConfiguredError: If the requested provider is not configured
        NotImplementedError: If the provider is not yet implemented
    """
    from .sora_provider import SoraProvider

    # Default from env or parameter
    if provider_name is None:
        env_provider = os.getenv("VIDEO_PROVIDER", "sora")
        provider_name = ProviderName(env_provider)

    if provider_name == ProviderName.SORA:
        return SoraProvider()
    elif provider_name == ProviderName.MOCK:
        raise NotConfiguredError(
            "Mock video provider is not allowed in production. "
            "Set VIDEO_PROVIDER=sora for Sora video generation."
        )
    elif provider_name == ProviderName.RUNWAY:
        raise NotImplementedError("Runway provider not yet implemented")
    elif provider_name == ProviderName.KLING:
        raise NotImplementedError("Kling provider not yet implemented")
    else:
        raise NotConfiguredError(
            f"Unknown video provider '{provider_name}'. Supported providers: sora"
        )


__all__ = [
    # Factory
    "get_video_provider",
    "NotConfiguredError",

    # Base classes
    "VideoProviderAdapter",
    "ProviderName",
    "ClipStatus",
    "AssetKind",
    "CreateClipInput",
    "RemixClipInput",
    "ProviderGeneration",
    "ProviderError",
]
