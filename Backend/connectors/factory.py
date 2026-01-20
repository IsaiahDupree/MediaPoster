"""
Adapter Factory (MOD-007)
==========================
Factory for creating platform adapters based on configuration.

This factory provides a centralized way to:
- Create adapter instances based on platform type
- Auto-discover available adapters
- Handle adapter creation with configuration
- Support dynamic adapter loading

Usage:
    >>> from connectors.factory import AdapterFactory
    >>> factory = AdapterFactory()
    >>>
    >>> # Create adapter by platform ID
    >>> twitter_adapter = factory.create("twitter")
    >>>
    >>> # Create all enabled adapters
    >>> adapters = factory.create_all_enabled()
    >>>
    >>> # Get available adapter types
    >>> types = factory.get_available_types()
"""

from typing import Dict, Type, Optional, List
from loguru import logger
from .base import SourceAdapter


class AdapterFactory:
    """
    Factory for creating platform adapters.

    Implements MOD-007: Adapter Factory feature.
    Dynamically creates adapter instances based on configuration.
    """

    # Adapter type registry - maps adapter_id to adapter class
    _adapter_classes: Dict[str, Type[SourceAdapter]] = {}

    @classmethod
    def register_adapter_class(cls, adapter_id: str, adapter_class: Type[SourceAdapter]):
        """
        Register an adapter class for dynamic creation.

        Args:
            adapter_id: Unique identifier for the adapter (e.g., 'twitter', 'meta')
            adapter_class: The adapter class to register
        """
        if adapter_id in cls._adapter_classes:
            logger.warning(f"Overwriting existing adapter class: {adapter_id}")
        cls._adapter_classes[adapter_id] = adapter_class
        logger.debug(f"Registered adapter class: {adapter_id} -> {adapter_class.__name__}")

    @classmethod
    def create(cls, adapter_id: str, **kwargs) -> Optional[SourceAdapter]:
        """
        Create an adapter instance by ID.

        Args:
            adapter_id: The adapter ID (e.g., 'twitter', 'meta', 'blotato')
            **kwargs: Additional configuration for the adapter

        Returns:
            SourceAdapter instance, or None if adapter_id not found
        """
        adapter_class = cls._adapter_classes.get(adapter_id)

        if not adapter_class:
            logger.error(f"Adapter type '{adapter_id}' not found in factory registry")
            return None

        try:
            # Create adapter instance
            instance = adapter_class(**kwargs)
            logger.info(f"Created adapter: {adapter_id} ({instance.display_name})")
            return instance
        except Exception as e:
            logger.error(f"Failed to create adapter {adapter_id}: {e}")
            return None

    @classmethod
    def create_all_registered(cls) -> List[SourceAdapter]:
        """
        Create instances of all registered adapter types.

        Returns:
            List of adapter instances
        """
        adapters = []

        for adapter_id in cls._adapter_classes.keys():
            adapter = cls.create(adapter_id)
            if adapter:
                adapters.append(adapter)

        logger.info(f"Created {len(adapters)} adapters from factory")
        return adapters

    @classmethod
    def create_all_enabled(cls) -> List[SourceAdapter]:
        """
        Create instances of all enabled adapters.

        Returns:
            List of enabled adapter instances
        """
        all_adapters = cls.create_all_registered()
        enabled = [a for a in all_adapters if a.is_enabled()]

        logger.info(f"Created {len(enabled)} enabled adapters out of {len(all_adapters)} total")
        return enabled

    @classmethod
    def get_available_types(cls) -> List[str]:
        """
        Get list of available adapter types.

        Returns:
            List of adapter IDs
        """
        return list(cls._adapter_classes.keys())

    @classmethod
    def is_registered(cls, adapter_id: str) -> bool:
        """
        Check if an adapter type is registered.

        Args:
            adapter_id: The adapter ID to check

        Returns:
            True if registered, False otherwise
        """
        return adapter_id in cls._adapter_classes


def auto_register_adapters():
    """
    Auto-register all available adapter classes.

    This function attempts to import and register all known adapter types.
    Used during initialization to populate the factory.
    """
    logger.info("Auto-registering adapter classes...")

    registered = 0

    # Meta/Facebook adapter
    try:
        from .meta import MetaCoachAdapter
        AdapterFactory.register_adapter_class("meta", MetaCoachAdapter)
        registered += 1
    except ImportError as e:
        logger.debug(f"Meta adapter not available: {e}")

    # Blotato adapter
    try:
        from .blotato_adapter import BlotatoAdapter
        AdapterFactory.register_adapter_class("blotato", BlotatoAdapter)
        registered += 1
    except ImportError as e:
        logger.debug(f"Blotato adapter not available: {e}")

    # Twitter adapter
    try:
        from .twitter import TwitterConnector
        AdapterFactory.register_adapter_class("twitter", TwitterConnector)
        registered += 1
    except ImportError as e:
        logger.debug(f"Twitter adapter not available: {e}")

    # Twitter adapter (alternate)
    try:
        from .twitter_adapter import TwitterAdapter
        AdapterFactory.register_adapter_class("twitter_adapter", TwitterAdapter)
        registered += 1
    except ImportError as e:
        logger.debug(f"Twitter adapter (alternate) not available: {e}")

    # Instagram adapters
    try:
        from .instagram import InstagramConnector
        AdapterFactory.register_adapter_class("instagram", InstagramConnector)
        registered += 1
    except ImportError as e:
        logger.debug(f"Instagram connector not available: {e}")

    # TikTok adapter
    try:
        from .tiktok import TikTokConnector
        AdapterFactory.register_adapter_class("tiktok", TikTokConnector)
        registered += 1
    except ImportError as e:
        logger.debug(f"TikTok connector not available: {e}")

    # YouTube adapter
    try:
        from .youtube import YouTubeConnector
        AdapterFactory.register_adapter_class("youtube", YouTubeConnector)
        registered += 1
    except ImportError as e:
        logger.debug(f"YouTube connector not available: {e}")

    # LinkedIn adapter
    try:
        from .linkedin import LinkedInConnector
        AdapterFactory.register_adapter_class("linkedin", LinkedInConnector)
        registered += 1
    except ImportError as e:
        logger.debug(f"LinkedIn connector not available: {e}")

    # Threads adapter
    try:
        from .threads import ThreadsConnector
        AdapterFactory.register_adapter_class("threads", ThreadsConnector)
        registered += 1
    except ImportError as e:
        logger.debug(f"Threads connector not available: {e}")

    logger.info(f"Auto-registered {registered} adapter classes")
    return registered


__all__ = ['AdapterFactory', 'auto_register_adapters']
