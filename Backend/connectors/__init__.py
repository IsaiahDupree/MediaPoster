"""
Connectors module for MediaPoster
Handles registration and initialization of platform adapters
"""
from loguru import logger
from .registry import registry
from .base import SourceAdapter

def initialize_adapters():
    """Initialize and register all available adapters"""
    logger.info("Initializing connector adapters...")
    
    # Import and register adapters
    adapters_registered = 0
    adapters_enabled = 0
    
    try:
        # Import Meta/Facebook adapter
        from .meta import MetaCoachAdapter
        meta_adapter = MetaCoachAdapter()
        registry.register(meta_adapter)
        adapters_registered += 1
        if meta_adapter.is_enabled():
            adapters_enabled += 1
    except Exception as e:
        logger.warning(f"Meta adapter not available: {e}")
    
    try:
        # Import Blotato adapter
        from .blotato import BlotatoAdapter
        blotato_adapter = BlotatoAdapter()
        registry.register(blotato_adapter)
        adapters_registered += 1
        if blotato_adapter.is_enabled():
            adapters_enabled += 1
    except Exception as e:
        logger.warning(f"Blotato adapter not available: {e}")
    
    # Log summary
    supported_platforms = registry.get_all_supported_platforms()
    logger.info(f"Adapters initialized: {adapters_enabled} enabled out of {adapters_registered} registered")
    logger.info(f"Supported platforms: {', '.join(sorted(supported_platforms))}")
    
    return registry

__all__ = ['initialize_adapters', 'registry', 'SourceAdapter']
