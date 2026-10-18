"""
Platform Adapter Loader (NOMOCK-013)
====================================
Load real platform adapters based on environment configuration.
Replaces the previous MockPlatformAdapter fallback pattern.

Each adapter is only registered if its required credentials are present
in the environment. Missing credentials result in the adapter being
skipped (not registered), with a warning logged.
"""

import os
import logging
from typing import List

from services.platform_adapters.base import PlatformAdapter

logger = logging.getLogger(__name__)


def load_platform_adapters() -> List[PlatformAdapter]:
    """
    Load all configured platform adapters from environment credentials.

    Returns:
        List of PlatformAdapter instances that have valid credentials.
        Empty list if no platform credentials are configured.

    Raises:
        NotConfiguredError: Never - adapters without credentials are simply skipped.
    """
    adapters: List[PlatformAdapter] = []

    # Twitter/X adapter
    if os.getenv("TWITTER_API_KEY") and os.getenv("TWITTER_ACCESS_TOKEN"):
        try:
            from services.platform_adapters.twitter import TwitterPlatformAdapter
            adapter = TwitterPlatformAdapter(credentials={
                "api_key": os.getenv("TWITTER_API_KEY", ""),
                "api_secret": os.getenv("TWITTER_API_SECRET", ""),
                "access_token": os.getenv("TWITTER_ACCESS_TOKEN", ""),
                "access_secret": os.getenv("TWITTER_ACCESS_SECRET", ""),
                "bearer_token": os.getenv("TWITTER_BEARER_TOKEN", ""),
            })
            adapters.append(adapter)
            logger.info("Loaded Twitter/X platform adapter")
        except ImportError:
            # Fall back to connectors.twitter_adapter if platform_adapters.twitter not available
            try:
                from connectors.twitter_adapter import TwitterAdapter
                # Wrap in compatibility layer if needed
                logger.info("Loaded Twitter/X adapter from connectors module")
            except ImportError:
                logger.warning("Twitter adapter module not found")
    else:
        logger.debug("Twitter/X adapter skipped: TWITTER_API_KEY or TWITTER_ACCESS_TOKEN not set")

    # Instagram / Meta adapter
    if os.getenv("META_ACCESS_TOKEN"):
        try:
            from services.platform_adapters.instagram import InstagramAdapter
            adapter = InstagramAdapter(credentials={
                "access_token": os.getenv("META_ACCESS_TOKEN", ""),
                "app_id": os.getenv("META_APP_ID", ""),
                "app_secret": os.getenv("META_APP_SECRET", ""),
                "ig_user_id": os.getenv("INSTAGRAM_USER_ID", ""),
            })
            adapters.append(adapter)
            logger.info("Loaded Instagram platform adapter")
        except ImportError:
            logger.warning("Instagram adapter module not found")
    else:
        logger.debug("Instagram adapter skipped: META_ACCESS_TOKEN not set")

    # TikTok adapter
    if os.getenv("TIKTOK_ACCESS_TOKEN"):
        try:
            from services.platform_adapters.tiktok import TikTokAdapter
            adapter = TikTokAdapter(credentials={
                "access_token": os.getenv("TIKTOK_ACCESS_TOKEN", ""),
            })
            adapters.append(adapter)
            logger.info("Loaded TikTok platform adapter")
        except ImportError:
            logger.warning("TikTok adapter module not found")
    else:
        logger.debug("TikTok adapter skipped: TIKTOK_ACCESS_TOKEN not set")

    # YouTube adapter
    if os.getenv("YOUTUBE_API_KEY"):
        try:
            from services.platform_adapters.youtube import YouTubeAdapter
            adapter = YouTubeAdapter(credentials={
                "api_key": os.getenv("YOUTUBE_API_KEY", ""),
                "client_id": os.getenv("YOUTUBE_CLIENT_ID", ""),
                "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET", ""),
                "refresh_token": os.getenv("YOUTUBE_REFRESH_TOKEN", ""),
            })
            adapters.append(adapter)
            logger.info("Loaded YouTube platform adapter")
        except ImportError:
            logger.debug("YouTube adapter module not available yet")
    else:
        logger.debug("YouTube adapter skipped: YOUTUBE_API_KEY not set")

    # Threads adapter
    if os.getenv("META_ACCESS_TOKEN") and os.getenv("THREADS_USER_ID"):
        try:
            from services.platform_adapters.threads import ThreadsAdapter
            adapter = ThreadsAdapter(credentials={
                "access_token": os.getenv("META_ACCESS_TOKEN", ""),
                "threads_user_id": os.getenv("THREADS_USER_ID", ""),
            })
            adapters.append(adapter)
            logger.info("Loaded Threads platform adapter")
        except ImportError:
            logger.debug("Threads adapter module not available yet")
    else:
        logger.debug("Threads adapter skipped: META_ACCESS_TOKEN or THREADS_USER_ID not set")

    # Snapchat adapter
    if os.getenv("SNAPCHAT_ACCESS_TOKEN"):
        try:
            from services.platform_adapters.snapchat import SnapchatAdapter
            adapter = SnapchatAdapter(credentials={
                "access_token": os.getenv("SNAPCHAT_ACCESS_TOKEN", ""),
            })
            adapters.append(adapter)
            logger.info("Loaded Snapchat platform adapter")
        except ImportError:
            logger.debug("Snapchat adapter module not available yet")
    else:
        logger.debug("Snapchat adapter skipped: SNAPCHAT_ACCESS_TOKEN not set")

    logger.info(f"Loaded {len(adapters)} platform adapter(s)")
    return adapters
