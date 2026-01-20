"""
Connectors module for MediaPoster
Handles registration and initialization of platform adapters
"""
from loguru import logger
from .registry import registry
from .base import SourceAdapter
from .factory import AdapterFactory, auto_register_adapters

def initialize_adapters():
    """
    Initialize and register all available adapters using AdapterFactory (MOD-007).

    This function:
    1. Auto-registers all adapter classes in the factory
    2. Creates instances of all enabled adapters
    3. Registers them in the global registry
    """
    logger.info("Initializing connector adapters with AdapterFactory...")

    # Auto-register all adapter classes
    auto_register_adapters()

    # Create all enabled adapter instances
    adapters = AdapterFactory.create_all_registered()

    # Register all adapters in the global registry
    adapters_registered = 0
    adapters_enabled = 0

    for adapter in adapters:
        registry.register(adapter)
        adapters_registered += 1
        if adapter.is_enabled():
            adapters_enabled += 1

    # Log summary
    supported_platforms = registry.get_all_supported_platforms()
    logger.info(f"Adapters initialized: {adapters_enabled} enabled out of {adapters_registered} registered")
    logger.info(f"Supported platforms: {', '.join(sorted(supported_platforms))}")

    return registry

__all__ = ['initialize_adapters', 'registry', 'SourceAdapter', 'AdapterFactory', 'auto_register_adapters']
